from typing import Dict, Any
from django.db.models import Count
from .serialization import SerializationSpecPlugin
from .utils import extend_queryset


class SerializationSpecPluginModel(SerializationSpecPlugin):
    """ Derive from this if you want to apply model a function """
    kwargs = {}  # type: Dict[str, Any]

    def __init__(self, relation):
        self.relation = relation

    def get_name(self):
        return '%s_%s' % (self.relation, self.name)

    def modify_queryset(self, queryset):
        return queryset.annotate(**{self.get_name(): self.model_function(self.relation, **self.kwargs)})

    def get_value(self, instance):
        return getattr(instance, self.get_name())


class CountOf(SerializationSpecPluginModel):
    name = 'count'
    model_function = Count
    kwargs = {'distinct': True}  # To prevent counts clashing with each other


class Exists(CountOf):
    def get_value(self, instance):
        return super().get_value(instance) > 0


class Requires(SerializationSpecPlugin):
    """ Use this for a property which needs some underlying fields to be loaded """

    def __init__(self, fields):
        self.fields = fields

    def modify_queryset(self, queryset):
        extend_queryset(queryset, self.fields)
        return queryset

    def get_value(self, instance):
        return getattr(instance, self.key)


class Transform(SerializationSpecPlugin):
    """ Derive from this if you want to transform underlying data """

    def modify_queryset(self, queryset):
        extend_queryset(queryset, {self.key})
        return queryset

    def get_value(self, instance):
        return self.transform(getattr(instance, self.key))

    def transform(self, value):
        raise NotImplementedError


class MethodCall(SerializationSpecPlugin):
    def __init__(self, name, required_fields=None):
        self.name = name
        self.required_fields = set(required_fields) if required_fields else set()

    def modify_queryset(self, queryset):
        extend_queryset(queryset, self.required_fields)
        return queryset

    def get_value(self, instance):
        return getattr(instance, self.name)()
