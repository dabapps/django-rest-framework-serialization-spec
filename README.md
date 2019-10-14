𝗘𝗫𝗣𝗘𝗥𝗜𝗠𝗘𝗡𝗧𝗔𝗟

[![Build Status](https://travis-ci.com/dabapps/serialization-spec.svg?token=8zR1s286kqp7Z1h1qj91&branch=master)](https://travis-ci.com/dabapps/serialization-spec)

# Serialization Spec
Write a single specification for a read endpoint which can be used to generate the optimal query and the serializers to serialize.

```python
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
```

This specification results in two steps:

1. fetch the data required to populate this, making judicious use of `.only()`, `.prefetch_related()` and `.select_related()` to issue minimal database queries

2. serializing these fields to output json based on the model field type

The mixin implements `get_queryset()` and `get_serializer()` in case you need to override any part of it.
