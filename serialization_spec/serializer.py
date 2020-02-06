from rest_framework.utils import model_meta
from django.db.models.fields.reverse_related import ManyToManyRel


def split(items, predicate):
    return (
        [item for item in items if predicate(item)],
        [item for item in items if not predicate(item)],
    )


def get_reverse_related_object_ids(own_ids, model, key):
    relation = model_meta.get_field_info(model).reverse_relations[key]
    reverse_fk = next(
        rel.field.name
        for rel in model._meta.related_objects
        if rel.get_accessor_name() == key
    )
    related_objects = relation.related_model.objects.filter(**{reverse_fk + '__in': own_ids})
    data_dict = {}
    for own_id, other_id in related_objects.values_list(reverse_fk, 'id'):
        data_dict[own_id] = data_dict.get(own_id, []) + [other_id]
    return data_dict


def _get_m2m_related_object_ids(own_ids, model, key):
    relation = model_meta.get_field_info(model).forward_relations[key]
    m2m_field_name = relation.model_field.m2m_field_name()
    m2m_reverse_field_name = relation.model_field.m2m_reverse_field_name()
    related_objects = relation.model_field.remote_field.through.objects.filter(**{m2m_field_name + '__in': own_ids})
    return related_objects.values_list(m2m_field_name, m2m_reverse_field_name)


def get_m2m_related_object_ids(own_ids, model, key):
    data_dict = {}
    for own_id, other_id in _get_m2m_related_object_ids(own_ids, model, key):
        data_dict[own_id] = data_dict.get(own_id, []) + [other_id]
    return data_dict


def _get_reverse_m2m_related_object_ids(own_ids, model, key):
    rel = model._meta.fields_map[key]
    m2m_field_name = rel.field.m2m_field_name()
    m2m_reverse_field_name = rel.field.m2m_reverse_field_name()
    related_objects = rel.field.remote_field.through.objects.filter(**{m2m_reverse_field_name + '__in': own_ids})
    return related_objects.values_list(m2m_reverse_field_name, m2m_field_name)


def get_reverse_m2m_related_object_ids(own_ids, model, key):
    data_dict = {}
    for own_id, other_id in _get_reverse_m2m_related_object_ids(own_ids, model, key):
        data_dict[own_id] = data_dict.get(own_id, []) + [other_id]
    return data_dict


def get_reverse_related_objects(own_ids, model, key, spec):
    relation = model_meta.get_field_info(model).reverse_relations[key]
    reverse_fk = next(
        rel.field.name
        for rel in model._meta.related_objects
        if rel.get_accessor_name() == key
    )
    related_objects = relation.related_model.objects.filter(**{reverse_fk + '__in': own_ids})

    data = serialize(related_objects, spec + [reverse_fk])
    data_dict = {}
    for each in data:
        data_dict[each[reverse_fk]] = data_dict.get(each[reverse_fk], []) + [each]
    if reverse_fk not in spec:
        for each in data_dict.values():
            for item in each:
                del item[reverse_fk]
    return data_dict


def get_m2m_related_objects(own_ids, model, key, spec):
    m2m_related_object_ids = _get_m2m_related_object_ids(own_ids, model, key)
    other_ids = [other_id for own_id, other_id in m2m_related_object_ids]
    relation = model_meta.get_field_info(model).forward_relations[key]
    related_objects = relation.related_model.objects.filter(id__in=other_ids)

    other_data = serialize(related_objects, spec + ['id'])
    other_data_dict = {}
    for each in other_data:
        other_data_dict[each['id']] = each
    if 'id' not in spec:
        for each in other_data_dict.values():
            del each['id']
    data_dict = {}
    for own_id, other_id in m2m_related_object_ids:
        data_dict[own_id] = data_dict.get(own_id, []) + [other_data_dict[other_id]]
    return data_dict


def get_reverse_m2m_related_objects(own_ids, model, key, spec):
    m2m_related_object_ids = _get_reverse_m2m_related_object_ids(own_ids, model, key)
    other_ids = [other_id for own_id, other_id in m2m_related_object_ids]
    rel = model._meta.fields_map[key]
    related_objects = rel.field.remote_field.related_model.objects.filter(id__in=other_ids)

    other_data = serialize(related_objects, spec + ['id'])
    other_data_dict = {}
    for each in other_data:
        other_data_dict[each['id']] = each
    if 'id' not in spec:
        for each in other_data_dict.values():
            del each['id']
    data_dict = {}
    for own_id, other_id in m2m_related_object_ids:
        data_dict[own_id] = data_dict.get(own_id, []) + [other_data_dict[other_id]]
    return data_dict


def get_forward_related_objects(fks, model, key, spec):
    relation = model_meta.get_field_info(model).forward_relations[key]
    related_objects = relation.related_model.objects.filter(id__in=fks)
    data = serialize(related_objects, spec + ['id'])
    data_dict = {each['id']: each for each in data}
    if 'id' not in spec:
        for each in data_dict.values():
            del each['id']
    return data_dict


def validate_serialization_spec(model, serialization_spec):
    field_info = model_meta.get_field_info(model)
    fields, tuples = split(serialization_spec, lambda each: isinstance(each, str))

    def is_reverse(key):
        return key in field_info.reverse_relations

    def is_forward(key):
        return key in field_info.forward_relations

    def is_m2m(key):
        return key in field_info.forward_relations and field_info.forward_relations[key].to_many

    def is_reverse_m2m(key):
        return type(model._meta.fields_map.get(key)) is ManyToManyRel

    reverse_fks, fields = split(fields, is_reverse)
    reverse_m2ms, reverse_fks = split(reverse_fks, is_reverse_m2m)
    m2m_fields, fields = split(fields, is_m2m)
    fks, fields = split(fields, is_forward)

    reverse_fk_objects, fk_objects = split(tuples, lambda each: is_reverse(each[0]))
    reverse_m2m_objects, reverse_fk_objects = split(reverse_fk_objects, lambda each: is_reverse_m2m(each[0]))
    m2m_objects, fk_objects = split(fk_objects, lambda each: is_m2m(each[0]))

    return (
        fields,
        fks,
        reverse_fks,
        reverse_m2ms,
        m2m_fields,
        fk_objects,
        reverse_fk_objects,
        reverse_m2m_objects,
        m2m_objects
    )


def serialize(queryset, serialization_spec):
    model = queryset.model

    (
        fields,
        fks,
        reverse_fks,
        reverse_m2ms,
        m2m_fields,
        fk_objects,
        reverse_fk_objects,
        reverse_m2m_objects,
        m2m_objects
    ) = validate_serialization_spec(model, serialization_spec)

    needs_id = reverse_fks or reverse_fk_objects or m2m_fields or m2m_objects or reverse_m2ms or reverse_m2m_objects
    to_fetch = fields + fks + (['id'] if needs_id else []) + ([fk for fk, _ in fk_objects])
    data = list(queryset.values(*to_fetch))

    if needs_id:
        own_ids = [each['id'] for each in data]

        for extra_fields in [reverse_fks, m2m_fields, reverse_m2ms]:
            if extra_fields:
                for key in extra_fields:
                    if extra_fields is reverse_fks:
                        related_items = get_reverse_related_object_ids(own_ids, model, key)
                    elif extra_fields is m2m_fields:
                        related_items = get_m2m_related_object_ids(own_ids, model, key)
                    elif extra_fields is reverse_m2ms:
                        related_items = get_reverse_m2m_related_object_ids(own_ids, model, key)

                    for each in data:
                        each[key] = related_items[each['id']]

        for extra_objects in [reverse_fk_objects, m2m_objects, reverse_m2m_objects]:
            if extra_objects:
                for key, spec in extra_objects:
                    if extra_objects is reverse_fk_objects:
                        related_items = get_reverse_related_objects(own_ids, model, key, spec)
                    elif extra_objects is reverse_m2m_objects:
                        related_items = get_reverse_m2m_related_objects(own_ids, model, key, spec)
                    else:
                        related_items = get_m2m_related_objects(own_ids, model, key, spec)

                    for each in data:
                        each[key] = related_items[each['id']]

        if 'id' not in fields:
            for each in data:
                del each['id']

    if fk_objects:
        for key, spec in fk_objects:
            fks = [each[key] for each in data]
            related_objects = get_forward_related_objects(fks, model, key, spec)

            for each in data:
                each[key] = related_objects[each[key]]

    return data


def jsonify(data):
    if data is None or type(data) in [int, bool, str]:
        return data
    if isinstance(data, list):
        return [jsonify(value) for value in data]
    if isinstance(data, dict):
        return {key: jsonify(value) for key, value in data.items()}
    return str(data)


def serializej(qs, spec):
    data = serialize(qs, spec)
    return jsonify(data)


def serializep(qs, spec):
    import json
    json_data = serializej(qs, spec)
    print(json.dumps(json_data, indent=2))
