from django.db.models import Prefetch, Count
from rest_framework.utils import model_meta
from rest_framework.fields import Field
from rest_framework.serializers import ModelSerializer
from zen_queries.rest_framework import QueriesDisabledViewMixin

from typing import List, Dict, Union

"""
Parse a serialization spec such as:

class ProductVersionDetail(SerializationSpecMixin, generics.RetrieveAPIView):

    queryset = ProductVersion.objects.all()
    serialization_spec = [
        'id',
        {'product': [
            'id',
            'name'
        ]},
        {'report_templates': [
            'id',
            'name'
        ]}
    ]

1. fetch the data required to populate this
2. output it

mixin should implement get_queryset() and get_serializer()

"""


class SerializerLambdaField(Field):
    def __init__(self, impl, **kwargs):
        self.impl = impl
        kwargs['source'] = '*'
        kwargs['read_only'] = True
        super().__init__(**kwargs)

    def to_representation(self, value):
        return self.impl(value)


class SerializationSpecPlugin:
    pass


def get_fields(serialization_spec):
    return sum(
        [list(x.keys()) if isinstance(x, dict) else [x] for x in serialization_spec],
        []
    )


def get_only_fields(model, serialization_spec):
    field_info = model_meta.get_field_info(model)
    return [
        field for field in get_fields(serialization_spec)
        if field in field_info.fields_and_pk.keys() or field in field_info.forward_relations.keys()
    ]


def get_childspecs(serialization_spec):
    return [each for each in serialization_spec if isinstance(each, dict)]


def make_serializer_class(model, serialization_spec):
    relations = model_meta.get_field_info(model).relations
    return type(
        'MySerializer',
        (ModelSerializer,),
        {
            'Meta': type(
                'Meta',
                (object,),
                {'model': model, 'fields': get_fields(serialization_spec)}
            ),
            **{
                key: make_serializer_class(
                    relations[key].related_model,
                    values
                )(many=relations[key].to_many) if isinstance(values, list) else SerializerLambdaField(impl=values.get_value)
                for key, values
                in [item for each in get_childspecs(serialization_spec) for item in each.items()]
            }
        }
    )


def prefetch_related(queryset, model, prefixes, serialization_spec, use_select_related):
    relations = model_meta.get_field_info(model).relations
    for key, childspec in [item for each in get_childspecs(serialization_spec) for item in each.items()]:
        key_path = '__'.join(prefixes + [key])

        if isinstance(childspec, SerializationSpecPlugin):
            queryset = childspec.modify_queryset(queryset)

        else:
            relation = relations[key]
            related_model = relation.related_model

            if (relation.model_field and relation.model_field.one_to_one) or (use_select_related and not relation.to_many):
                # no way to .only() on a select_related field
                queryset = queryset.select_related(key_path)
                queryset = prefetch_related(queryset, related_model, prefixes + [key], childspec, use_select_related)
            else:
                only_fields = get_only_fields(related_model, childspec)
                if relation.reverse and not relation.has_through_model:
                    # need to include the reverse FK to allow prefetch to stitch results together
                    # Unfortunately that info is in the model._meta but is not in the RelationInfo tuple
                    reverse_fk = next(
                        rel.field.name
                        for rel in model._meta.related_objects
                        if rel.get_accessor_name() == key
                    )
                    only_fields += ['%s_id' % reverse_fk]
                inner_queryset = prefetch_related(related_model.objects.only(*only_fields), related_model, [], childspec, use_select_related)
                queryset = queryset.prefetch_related(Prefetch(key_path, queryset=inner_queryset))

    return queryset


class SerializationSpecMixin(QueriesDisabledViewMixin):

    serialization_spec = None  # type: SerializationSpec

    def get_object(self):
        self.use_select_related = True
        return super().get_object()

    def get_queryset(self):
        queryset = self.queryset
        queryset = queryset.only(*get_only_fields(queryset.model, self.serialization_spec))
        queryset = prefetch_related(queryset, queryset.model, [], self.serialization_spec, getattr(self, 'use_select_related', False))
        return queryset

    def get_serializer_class(self):
        return make_serializer_class(self.queryset.model, self.serialization_spec)


class SerializationSpecPluginModel(SerializationSpecPlugin):
    def __init__(self, relation):
        self.relation = relation

    def get_name(self):
        return '%s_%s' % (self.relation, self.name)

    def modify_queryset(self, queryset):
        return queryset.annotate(**{self.get_name(): self.model_function(self.relation)})

    def get_value(self, instance):
        return getattr(instance, self.get_name())


class CountOf(SerializationSpecPluginModel):
    name = 'count'
    model_function = Count


"""
serialization_spec type should be

    SerializationSpec = List[Union[str, Dict[str, Union[SerializationSpecPluginModel, 'SerializationSpec']]]]

But recursive types are not yet implemented :(
So we specify to an (arbitrary) depth of 5
"""
SerializationSpec = List[Union[str, Dict[str, Union[SerializationSpecPluginModel,
    List[Union[str, Dict[str, Union[SerializationSpecPluginModel,
        List[Union[str, Dict[str, Union[SerializationSpecPluginModel,
            List[Union[str, Dict[str, Union[SerializationSpecPluginModel,
                List[Union[str, Dict[str, Union[SerializationSpecPluginModel,
                    List]]]]
            ]]]]
        ]]]]
    ]]]]
]]]]
