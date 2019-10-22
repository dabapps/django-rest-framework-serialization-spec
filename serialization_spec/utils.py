def extend_queryset(queryset, fields):
    """ Extend an already-`.only()`d queryset with more fields """
    existing, defer = queryset.query.deferred_loading
    existing_set = set(existing)
    existing_set.update(fields)
    queryset.query.deferred_loading = (frozenset(existing_set), defer)
