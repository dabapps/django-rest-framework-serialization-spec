**EXPERIMENTAL**

[![Build Status](https://travis-ci.com/dabapps/django-rest-framework-serialization-spec.svg?token=8zR1s286kqp7Z1h1qj91&branch=master)](https://travis-ci.com/dabapps/django-rest-framework-serialization-spec)

# Serialization Spec Mixin

This mixin for [Django REST Framework](https://www.django-rest-framework.org/) [APIView](https://www.django-rest-framework.org/api-guide/generic-views/)s allows you to declaratively specify an API endpoint. The specification defines the shape of the data to be fetched by [Django](https://www.djangoproject.com/)'s ORM, and then uses  REST Framework's serializers to output structured data.

By automatic application of `.prefetch_related()`, `.select_related()` and `.only()` during the querying, no further fetching is done during serialization and as a result the [N + 1 SELECTs problem](https://stackoverflow.com/questions/97197/what-is-the-n1-selects-problem-in-orm-object-relational-mapping) can be avoided. In addition problems arising from manual prefetching such as overfetching, underfetching and duplicate fetching are also avoided.

## Example

```python
from rest_framework.generics import RetrieveAPIView
from serialization_spec.serialization import SerializationSpecMixin

class AnimalDetail(SerializationSpecMixin, RetrieveAPIView):

    queryset = Animal.objects.all()
    
    serialization_spec = [
        'id',
        'name',
        {'breeds': [
            'id',
            'name',
        ]},
    ]
```

When this view is accessed via its URL it returns the following response data:
```
GET:/animals/1
```
```json
{
    "id": 1,
    "name": "Doggos",
    "breeds": [
        {
            "id": 1,
            "name": "Labrador",
        },
        {
            "id": 2,
            "name": "Poodle",
        },
    ]
}
```

These are the SQL queries that were made:
```sql
SELECT animal.id, animal.name FROM animal WHERE animal.id = 1;

SELECT (animal_breeds.animal_id) AS _prefetch_related_val_animal_id,
        breed.id,
        breed.name
    FROM breed
    INNER JOIN animal_breeds
        ON (breed.id = animal_breeds.breed_id)
    WHERE animal_breeds.animal_id IN (1);
```

## Implementation

The mixin implements `get_queryset()` and `get_serializer_class()` which you can subsequently override to specialise or refine the behaviour.

#### SerializerSpecMixin.get_queryset(self)
Iterate over `serialization_spec` and build an optimised queryset.

#### SerializerSpecMixin.get_serializer_class(self)
Iterate over `serialization_spec` and build a nested hierarchy of `ModelSerializer`s which will serialize the model data already fetched in `get_queryset()`.

## Plugins
As well as access to model fields, you can also specify computations to be applied.
A useful set of these is provided, as well as a framework to build bespoke ones.

#### CountOf, Exists
Illustrated most straightforwardly with an example:
```python
    serialization_spec = [
        # ...
        {'has_breeds': Exists('breeds')},
        {'num_breeds': CountOf('breeds')},
    ]
```

#### Requires
Sometimes a model property requires certain underlying fields to be loaded:
```python
from django.db import models

class Animal(models.Model):
    # ...
    age = models.IntegerField()

    @property
    def status(self):
        return 'retired' if self.age > 10 else 'active'
```
```python
    serialization_spec = [
        # ...
        {'status': Requires(['age'])}
    ]
```

### Building bespoke plugins
A plugin can be built for any purpose. It must simply specify how it should modify the underlying queryset, either with annotations or prefetches explicitly, or with an internal `serialization_spec`, and then how the value can be derived from this prefetched data:

```python
from serialization_spec.serialization import SerializationSpecPlugin

class UsersCompletedCount(SerializationSpecPlugin):
    def modify_queryset(self, queryset):
        return queryset.annotate(
            users_completed_count=Count(Case(When(users__completed__isnull=False, then=1))),
            raters_completed_count=Count(Case(When(users__raters__completed__isnull=False, then=1)))
        )

    def get_value(self, instance):
        return instance.users_completed_count + instance.raters_completed_count

# ...

    serialization_spec = [
        # ...
        {'users_completed_count': UsersCompletedCount()}
    ]
```

Plugins may also refer to `self.key` if they need to know the key beneath which they were inserted into the `serialization_spec`.

## Filtered
`Filtered` works much like a Plugin but is handled differently in the implementation. It used where the set of values needed on a 1:M relation should have a filter applied to it. It takes a [django `Q()` object](https://docs.djangoproject.com/en/2.2/topics/db/queries/#complex-lookups-with-q-objects) as well as a child serialization spec:

```python
    serialization_spec = [
        # ...
        {'users': Filtered(Q(completed=True), [
             'id',
             'full_name',
        ]}
    ]
```
