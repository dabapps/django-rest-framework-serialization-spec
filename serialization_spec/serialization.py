from django.core.exceptions import ImproperlyConfigured
from django.db.models import Prefetch
from django.utils.functional import cached_property
from django_readers import specs, pairs, qs
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


class SerializationSpecPlugin:
    """ These methods can access self.key to get the key """

    def modify_queryset(self, queryset):
        return queryset

    # abstract method
    def get_value(self, instance):
        raise NotImplementedError


class ManyToManyIDsPlugin(SerializationSpecPlugin):
    def __init__(self, related_model, key):
        self.related_model = related_model
        self.to_attr = '_%s_ids' % key
        self.key = key

    def modify_queryset(self, queryset):
        inner_queryset = self.related_model.objects.only('id')
        return queryset.prefetch_related(Prefetch(self.key, queryset=inner_queryset))

    def get_value(self, instance):
        return [str(each.id) for each in getattr(instance, self.key).all()]


class Filtered:
    def __init__(self, *args):
        if len(args) == 2:
            self.field_name = None
            self.filters, self.serialization_spec = args
        elif len(args) == 3:
            self.field_name, self.filters, self.serialization_spec = args
        else:
            raise Exception('Specify filters and serialization_spec for Filtered')


class Aliased(Filtered):
    def __init__(self, field_name, serialization_spec=None):
        self.filters = None
        self.field_name = field_name
        self.serialization_spec = serialization_spec


def get_serialization_spec(view_or_plugin, request_user=None):
    if hasattr(view_or_plugin, 'get_serialization_spec'):
        view_or_plugin.request_user = request_user
        return view_or_plugin.get_serialization_spec()
    return getattr(view_or_plugin, 'serialization_spec', None)


def adapt_plugin_spec(plugin_spec, request_user=None):
    assert len(plugin_spec) == 1
    key, plugin = next(iter(plugin_spec.items()))
    plugin.key = key
    plugin.request_user = request_user

    def prepare(queryset):
        plugin_spec = get_serialization_spec(plugin)
        if plugin_spec:
            plugin_prepare, _ = specs.process(preprocess_spec(plugin_spec, request_user=request_user))
            return plugin_prepare(queryset)
        return plugin.modify_queryset(queryset)

    def project(instance):
        return {key: plugin.get_value(instance)}

    return prepare, project


def preprocess_item(item, request_user=None):
    if isinstance(item, dict):
        processed_item = []
        for key, value in item.items():
            if isinstance(value, list):
                processed_item.append({key: preprocess_spec(value, request_user=request_user)})
            elif isinstance(value, SerializationSpecPlugin):
                processed_item.append(adapt_plugin_spec({key: value}, request_user=request_user))
            elif isinstance(value, Filtered):
                if value.serialization_spec is None:
                    spec = specs.alias(key, value.field_name)
                else:
                    relationship_spec = preprocess_spec(value.serialization_spec, request_user=request_user)
                    if value.filters:
                        relationship_spec.append(
                            pairs.prepare_only(
                                qs.pipe(
                                    qs.filter(value.filters),
                                    qs.distinct()
                                )
                            )
                        )
                    to_attr = key if value.field_name and value.field_name != key else None
                    spec = specs.auto_relationship(value.field_name or key, relationship_spec, to_attr=to_attr)
                processed_item.append(spec)
        return processed_item
    return [item]


def preprocess_spec(spec, request_user=None):
    processed_spec = []
    for item in spec:
        processed_spec += preprocess_item(item, request_user=request_user)
    return processed_spec


class ProjectionSerializer:
    def __init__(self, data=None, many=False, projector=None):
        self.many = many
        self._data = data
        self.project = projector

    @property
    def data(self):
        if self.many:
            return [self.project(item) for item in self._data]
        return self.project(self._data)


class SerializationSpecMixin:

    serialization_spec = None  # type: SerializationSpec

    def get_reader_pair(self):
        spec = get_serialization_spec(self)
        if spec is None:
            raise ImproperlyConfigured('SerializationSpecMixin requires serialization_spec or get_serialization_spec')
        spec = preprocess_spec(spec, request_user=self.request.user)
        return specs.process(spec)

    @cached_property
    def reader_pair(self):
        return self.get_reader_pair()

    def get_prepare_function(self):
        return self.reader_pair[0]

    def get_project_function(self):
        return self.reader_pair[1]

    def filter_queryset(self, queryset):
        return self.get_prepare_function()(queryset)

    def get_serializer(self, *args, **kwargs):
        return ProjectionSerializer(
            *args,
            **kwargs,
            projector=self.get_project_function()
        )


"""
serialization_spec type should be

    SerializationSpec = List[Union[str, Dict[str, Union[SerializationSpecPlugin, 'SerializationSpec']]]]

But recursive types are not yet implemented :(
So we specify to an (arbitrary) depth of 5
"""
SerializationSpec = List[Union[str, Dict[str, Union[Filtered, SerializationSpecPlugin,
    List[Union[str, Dict[str, Union[Filtered, SerializationSpecPlugin,
        List[Union[str, Dict[str, Union[Filtered, SerializationSpecPlugin,
            List[Union[str, Dict[str, Union[Filtered, SerializationSpecPlugin,
                List[Union[str, Dict[str, Union[Filtered, SerializationSpecPlugin,
                    List]]]]
            ]]]]
        ]]]]
    ]]]]
]]]]
