from rest_framework import generics
from serialization_spec.serialization import SerializationSpecMixin, CountOf
from .models import Teacher, Student, Class, Subject, School, Assignment


class TeacherDetailView(SerializationSpecMixin, generics.RetrieveAPIView):

    queryset = Teacher.objects.all()
    lookup_field = 'id'

    serialization_spec = [
        'id',
        'name',
        {'school': [
            'id',
            'name',
        ]},
        {'class_set': [
            'id',
            'name'
        ]}
    ]


class TeacherListView(SerializationSpecMixin, generics.ListAPIView):

    queryset = Teacher.objects.order_by('name')
    lookup_field = 'id'

    serialization_spec = [
        'id',
        'name',
        {'school': [
            'id',
            'name',
        ]},
        {'class_set': [
            'id',
            'name'
        ]}
    ]


class StudentDetailView(SerializationSpecMixin, generics.RetrieveAPIView):

    queryset = Student.objects.all()
    lookup_field = 'id'

    serialization_spec = [
        'id',
        'name',
        {'classes': [
            'id',
            'name'
        ]}
    ]


class ClassDetailView(SerializationSpecMixin, generics.RetrieveAPIView):

    queryset = Class.objects.all()
    lookup_field = 'id'

    serialization_spec = [
        'id',
        'name',
        {'teacher': [
            'id',
            'name',
            {'school': [
                'id',
                'name'
            ]}
        ]}
    ]


class SubjectDetailView(SerializationSpecMixin, generics.RetrieveAPIView):

    queryset = Subject.objects.all()
    lookup_field = 'id'

    serialization_spec = [
        'id',
        'name',
        {'class_set': [
            'id',
            'name',
            {'teacher': [
                'id',
                'name'
            ]}
        ]}
    ]


class SchoolDetailView(SerializationSpecMixin, generics.RetrieveAPIView):

    queryset = School.objects.all()
    lookup_field = 'id'

    serialization_spec = [
        'id',
        'name',
        {'lea': [
            'id',
            'name',
            {'school_set': [
                'id',
                'name'
            ]}
        ]}
    ]


class StudentWithAssignmentsDetailView(SerializationSpecMixin, generics.RetrieveAPIView):

    queryset = Student.objects.all()
    lookup_field = 'id'

    serialization_spec = [
        'id',
        'name',
        {'assignments': [
            'name'
        ]},
        {'assignmentstudent_set': [
            'is_complete',
            {'assignment': [
                'name'
            ]},
        ]},
    ]


class AssignmentDetailView(SerializationSpecMixin, generics.RetrieveAPIView):

    queryset = Assignment.objects.all()
    lookup_field = 'id'

    serialization_spec = [
        'id',
        'name',
        {'assignees': [
            'id',
            'name',
            {'classes_count': CountOf('classes')},
            'classes',
        ]}
    ]
