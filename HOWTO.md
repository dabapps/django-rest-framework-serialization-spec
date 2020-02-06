
## How to raise your API game
We have built an internal library to help us build performant and maintainable API read endpoints using Django Rest Framework. Using it will help you avoid many of the pitfalls mentioned in [API Best Practices](https://docs.dabapps.com/backend/api-best-practices/), and speed up development too.

**SerializationSpecMixin** is a mixin intended to be used with DRF's generic views ([RetrieveAPIView](https://www.django-rest-framework.org/api-guide/generic-views/#retrieveapiview) or [ListAPIView](https://www.django-rest-framework.org/api-guide/generic-views/#listapiview)). It implements the`get_queryset()` and `get_serializer()` methods for you, based on a configuration you specify in a single new class attribute, `serialization_spec`. Because it is only a mixin for a standard DRF view, other aspects of generic views such as search, filters, or pagination, will work in just the same way.

### Example 1: `StudentDetail`

```python
from rest_framework.generics import RetrieveAPIView
from serialization_spec.serialization import SerializationSpecMixin

class StudentDetail(SerializationSpecMixin, RetrieveAPIView):
    queryset = Student.objects.all()
    
    serialization_spec = [
        'id',
        'name',
        {'class_set': [
            'id',
            'name',
            'teacher'
        ]},
    ]
```

In this case, a single `Student` instance is retrieved based on the ID in the URL. Its `id` and `name` attributes will be loaded from the database, along with the `id` and `name` of any `Class`es that the student belongs to. The `teacher` key will correspond to the ID of the class's teacher.

The library will build a query that will request only the required fields from the database, including use of [select_related()](https://docs.djangoproject.com/en/3.0/ref/models/querysets/#select-related) as appropriate to load related objects. It will also create a serializer to return just these attributes using [ModelSerializer](https://www.django-rest-framework.org/tutorial/1-serialization/#using-modelserializers).

### Example 2: `StudentList`

```python
from rest_framework.generics import ListAPIView
from serialization_spec.serialization import SerializationSpecMixin
from apps.core.pagination import StandardResultsSetPagination

class StudentList(SerializationSpecMixin, ListAPIView):
    queryset = Student.objects.all()
    pagination_class = StandardResultsSetPagination
    
    serialization_spec = [
        'id',
        'name',
        {'class_set': [
            'id',
            'name',
            'teacher'
        ]},
    ]
```

In this case, a page of `Student` instances are retrieved. For each one, `id` and `name` attributes are returned, along with the `id` and `name` of any `Class`es that each student belongs to. The `teacher` key will correspond to the ID of the class's teacher.

The library will build a query that will request only the required fields from the database, including use of [prefetch_related()](https://docs.djangoproject.com/en/3.0/ref/models/querysets/#prefetch-related) as appropriate to load related objects. It will also create a serializer to return just these attributes using [ModelSerializer](https://www.django-rest-framework.org/tutorial/1-serialization/#using-modelserializers).

### Serialization Spec format

The `serialization_spec` is a list of fields or relations to be fetched and returned. In the case of relations, you are also able to specify what fields or relations are required in the nested object(s), recursively.

#### Examples

| Spec | Output | Outcome |
|--|--|--|
| `['name']` | `{'name': 'Fish'}` | The `name` field |
| `['id', 'name']` | `{'id': 1, 'name': 'Fish'}` | All requested fields |
| `['organisation']` | `{'organisation': 99}` | A foreign key's ID |
| `['organisations']` | `{'organisations': [88, 99]}` | A list of related object IDs |
| `[{'organisation': ['name']}]` | `{'organisation': {'name': 'My Org'}}` | A nested related object |
| `[{'organisations': ['name']}]` | `{'organisations': [{'name': 'Org 1'}, {'name': 'Org 2'}]}` | A list of related objects |

### Plugins

This straightforward mapping of model fields onto the returned structure can get you a long way, and in fact it helps keep your API simple and comprehensible to stay close to the model structure in this way.

However inevitably there are situations when the data must be transformed, and the library includes a plugins system to allow you to achieve this. A useful set of basic plugins is provided, as well as a framework to build your own.

#### `CountOf`

When you need to know the number of a set of related objects, but don't care what their values are.

```python
    serialization_spec = [
        # ...
        {'num_students': CountOf('student_set')},
    ]
```

#### `Exists`

When you need to know whether or not any related objects exist.

```python
    serialization_spec = [
        # ...
        {'has_students': Exists('students')},
    ]
```

#### `Requires`
Sometimes a model property requires certain underlying field(s) to be loaded to be able to return a value
```python
from django.db import models

class Student(models.Model):
    # ...
    year_group = models.IntegerField()

    @property
    def key_stage(self):
        if 0 < self.year_group <= 2:
            return 'KS1'
        elif 2 < self.year_group <= 6:
            return 'KS2'
        else return None
```
```python
    serialization_spec = [
        # ...
        {'key_stage': Requires(['year_group'])}
    ]
```

### Building bespoke plugins
A plugin can be built for any purpose. You need to provide two things: how it should modify the underlying queryset, and how the value can be derived from this prefetched data.

Here is an example where we are using `Case...When` to annotate information about related objects to our queryset and then processing that to find out the total number of completed users.

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
```

```python
    serialization_spec = [
        # ...
        {'users_completed_count': UsersCompletedCount()}
    ]
```

You can also specify the queryset using another level of `serialization_spec`:

```python
class UsersCompletedCount(SerializationSpecPlugin):
    serialization_spec = [
        'respondents_count': CountOf('respondent_set'),
        'raters_count': CountOf('rater_set'),
    ]

    def get_value(self, instance):
        return instance.respondents_count + instance.raters_count
```

```python
    serialization_spec = [
        # ...
        {'users_completed_count': UsersCompletedCount()}
    ]
```

Plugins have access to the following instance variables which may be helpful:
* `self.key` if they need to know their key in the `serialization_spec`
* `self.request_user`

### Filtering a relation

#### `Filtered`

In order to filter a 1:M relation, use `Filtered`. You provide a [django `Q()` object](https://docs.djangoproject.com/en/2.2/topics/db/queries/#complex-lookups-with-q-objects) and a child serialization spec:

```python
    serialization_spec = [
        # ...
        {'users': Filtered(Q(completed=True), [
             'id',
             'full_name',
        ]}
    ]
```

If you need to alias the relation then you can specify the underlying field name as an optional first argument:

```python
    serialization_spec = [
        # ...
        {'completed_users': Filtered('users', Q(completed=True), [
             'id',
             'full_name',
        ]}
    ]
```

#### `Aliased`

There is also a convenience, `Aliased`, for aliasing a relation without filtering:

```python
    serialization_spec = [
        # ...
        {'users': Aliased('user_set', [
             'id',
             'full_name',
        ]}
    ]
```

