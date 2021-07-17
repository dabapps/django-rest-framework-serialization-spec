from .test_api import SerializationSpecTestCase, uuid
from .models import Teacher, Class

from django.db.models.query import Q
from django_readers import pairs, specs
from rest_framework import generics
from unittest.mock import MagicMock
from serialization_spec.serialization import SerializationSpecMixin, SerializationSpecPlugin, Filtered, Aliased


class PluginsTestCase(SerializationSpecTestCase):

    class TeacherDetailView(SerializationSpecMixin, generics.RetrieveAPIView):
        queryset = Teacher.objects.all()

    def setUp(self):
        super().setUp()

        self.request = MagicMock()
        self.request.method = 'GET'
        self.request.user = 'USER_1'
        self.detail_view = self.TeacherDetailView(
            request=self.request,
            kwargs={'pk': Teacher.objects.first().id},
            format_kwarg=None
        )

    def test_simple_spec(self):
        self.detail_view.serialization_spec = [
            'id',
            'name'
        ]

        response = self.detail_view.retrieve(self.request)
        self.assertJsonEqual(response.data, {
            "id": "00000000-0000-0000-0000-000000000002",
            "name": "Mr Cat"
        })

    def test_get_spec(self):
        setattr(self.TeacherDetailView, 'get_serialization_spec', lambda self: [
            'id',
            'name'
        ])

        response = self.detail_view.retrieve(self.request)
        self.assertJsonEqual(response.data, {
            "id": "00000000-0000-0000-0000-000000000002",
            "name": "Mr Cat"
        })

        delattr(self.TeacherDetailView, 'get_serialization_spec')

    def test_spec_with_plugin(self):
        class SchoolNameUpper(SerializationSpecPlugin):
            serialization_spec = [
                {'school': [
                    'name',
                ]}
            ]

            def get_value(self, instance):
                return instance.school.name.upper()

        self.detail_view.serialization_spec = [
            {'school_name_upper': SchoolNameUpper()},
        ]

        with self.assertNumQueries(2):
            response = self.detail_view.retrieve(self.request)

        self.assertJsonEqual(response.data, {
            "school_name_upper": "KITTEH HIGH"
        })

    def test_merge_specs(self):
        class ClassNames(SerializationSpecPlugin):
            serialization_spec = [
                specs.relationship('class_set', [
                    'name',
                ], to_attr="class_set_for_name")
            ]

            def get_value(self, instance):
                return ', '.join(each.name for each in instance.class_set_for_name)

        class SubjectNames(SerializationSpecPlugin):
            serialization_spec = [
                specs.relationship('class_set', [
                    {'subject': [
                        'name',
                    ]}
                ], to_attr="class_set_for_subject_name")
            ]

            def get_value(self, instance):
                return ', '.join(each.subject.name for each in instance.class_set_for_subject_name)

        self.detail_view.serialization_spec = [
            'name',
            {'subject_names': SubjectNames()},
            {'classes_names': ClassNames()},
        ]

        response = self.detail_view.retrieve(self.request)

        self.assertJsonEqual(response.data, {
            "name": "Mr Cat",
            "classes_names": "French A, Math B",
            "subject_names": "French, Math"
        })

    def test_reverse_fk_list_ids(self):
        self.detail_view.serialization_spec = [
            {"class_set": pairs.pk_list('class_set')}
        ]

        response = self.detail_view.retrieve(self.request)
        self.assertEqual(
            [str(id) for id in response.data['class_set']],
            [uuid('5'), uuid('6')]
        )

    def test_many_to_many_list_ids(self):
        class ClassDetailView(SerializationSpecMixin, generics.RetrieveAPIView):
            queryset = Class.objects.all()

            serialization_spec = [
                {"student_set": pairs.pk_list('student_set')}
            ]

        detail_view = ClassDetailView(
            request=self.request,
            kwargs={'pk': Class.objects.first().id},
            format_kwarg=None
        )

        response = detail_view.retrieve(self.request)
        self.assertEqual(
            [str(id) for id in response.data['student_set']],
            [uuid('10'), uuid('11'), uuid('12'), uuid('13'), uuid('14'), uuid('15'), uuid('16')]
        )

    def test_spec_with_nested_plugin(self):
        class LeaName(SerializationSpecPlugin):
            serialization_spec = [
                {'lea': [
                    'name',
                ]}
            ]

            def get_value(self, instance):
                return instance.lea.name

        class SchoolNameUpper(SerializationSpecPlugin):
            serialization_spec = [
                {'school': [
                    'name',
                    {'lea_name': LeaName()}
                ]}
            ]

            def get_value(self, instance):
                return (instance.school.lea.name + ': ' + instance.school.name).upper()

        self.detail_view.serialization_spec = [
            {'school_name_upper': SchoolNameUpper()},
        ]

        with self.assertNumQueries(3):
            response = self.detail_view.retrieve(self.request)

        self.assertJsonEqual(response.data, {
            "school_name_upper": "BRIGHTON & HOVE: KITTEH HIGH"
        })

    def test_spec_with_filter(self):
        self.detail_view.serialization_spec = [
            {'school': [
                'name',
                {'teacher_set': Filtered(Q(name__icontains='cat'), [
                    'name'
                ])}
            ]},
        ]

        with self.assertNumQueries(3):
            response = self.detail_view.retrieve(self.request)
        self.assertJsonEqual(response.data, {
            "school": {
                "name": "Kitteh High",
                "teacher_set": [
                    {
                        "name": "Mr Cat"
                    },
                ]
            }
        })

    def test_spec_with_aliased_field(self):
        self.detail_view.serialization_spec = [
            {'school': [
                {'title': Aliased('name')},
                {'teachers': Aliased('teacher_set', [
                    'name'
                ])}
            ]},
        ]

        with self.assertNumQueries(3):
            response = self.detail_view.retrieve(self.request)

        self.assertJsonEqual(response.data, {
            "school": {
                "title": "Kitteh High",
                "teachers": [
                    {"name": "Mr Cat"},
                    {"name": "Ms Dog"},
                ]
            }
        })
