from django.db.models import Prefetch
from django_readers import specs, pairs, qs, rest_framework


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

    plugin_spec = get_serialization_spec(plugin)
    if plugin_spec:
        prepare, _ = specs.process(preprocess_spec(plugin_spec, request_user=request_user))
    else:
        prepare = plugin.modify_queryset

    return prepare, plugin.get_value


def preprocess_item(item, request_user=None):
    if isinstance(item, dict):
        processed_item = []
        for key, value in item.items():
            if isinstance(value, list):
                processed_item.append({key: preprocess_spec(value, request_user=request_user)})
            elif isinstance(value, SerializationSpecPlugin):
                processed_item.append({key: adapt_plugin_spec({key: value}, request_user=request_user)})
            elif isinstance(value, Filtered):
                if value.serialization_spec is None:
                    spec = {key: value.field_name}
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
                    spec = specs.relationship(value.field_name or key, relationship_spec, to_attr=to_attr)
                processed_item.append(spec)
            else:
                processed_item.append({key: value})
        return processed_item
    return [item]


def preprocess_spec(spec, request_user=None):
    processed_spec = []
    for item in spec:
        processed_spec += preprocess_item(item, request_user=request_user)
    return processed_spec


class SerializationSpecMixin(rest_framework.SpecMixin):
    def get_spec(self):
        spec = get_serialization_spec(self) or super().get_spec()
        return preprocess_spec(spec, request_user=self.request.user)
