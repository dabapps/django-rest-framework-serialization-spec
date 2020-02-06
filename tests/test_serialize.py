from django.test import TestCase

from .models import LEA, School, Teacher, Subject, Class, Student, Assignment, AssignmentStudent

from serialization_spec.serializer import serializej


class SerializationTestCase(TestCase):
    def setUp(self):
        self.lea = LEA.objects.create(name='Brighton & Hove')
        self.school = School.objects.create(name='Kitteh High', lea=self.lea)
        School.objects.create(name='Hove High', lea=self.lea)
        self.teacher = Teacher.objects.create(name='Mr Cat', school=self.school)
        Teacher.objects.create(name='Ms Dog', school=self.school)
        self.french = Subject.objects.create(name='French')
        self.math = Subject.objects.create(name='Math')
        self.french_class = Class.objects.create(name='French A', subject=self.french, teacher=self.teacher)
        self.math_class = Class.objects.create(name='Math B', subject=self.math, teacher=self.teacher)
        students = [
            Student.objects.create(name='Student %d' % idx, school=self.school)
            for idx in range(4)
        ]
        self.french_class.student_set.set(students[:2])
        self.math_class.student_set.set(students[2:])

        self.student = students[0]
        self.assignments = []
        for clasz in [self.french_class, self.math_class]:
            is_math = clasz == self.math_class
            assignment = Assignment.objects.create(clasz=clasz, name=clasz.name + ' Assignment')
            AssignmentStudent.objects.create(
                assignment=assignment, student=self.student, is_complete=is_math
            )
            self.assignments.append(assignment)

    def test_fields(self):
        serialization_spec = [
            'id',
            'name',
        ]
        data = serializej(Class.objects.all(), serialization_spec)
        self.assertEqual(data, [
            {'id': str(self.french_class.id), 'name': 'French A'},
            {'id': str(self.math_class.id), 'name': 'Math B'},
        ])

    def test_fk(self):
        serialization_spec = [
            'name',
            'subject',
        ]
        data = serializej(Class.objects.all(), serialization_spec)
        self.assertEqual(data, [
            {'name': 'French A', 'subject': str(self.french.id)},
            {'name': 'Math B', 'subject': str(self.math.id)},
        ])

    def test_reverse_fk(self):
        serialization_spec = [
            'name',
            'assignment_set',
        ]
        data = serializej(Class.objects.all(), serialization_spec)
        self.assertEqual(data, [
            {'name': 'French A', 'assignment_set': [str(self.assignments[0].id)]},
            {'name': 'Math B', 'assignment_set': [str(self.assignments[1].id)]},
        ])

    def test_fk_with_spec(self):
        serialization_spec = [
            'name',
            ('subject', [
                'name'
            ]),
        ]
        data = serializej(Class.objects.all(), serialization_spec)
        self.assertEqual(data, [
            {'name': 'French A', 'subject': {'name': 'French'}},
            {'name': 'Math B', 'subject': {'name': 'Math'}},
        ])

    def test_fk_with_nested_spec(self):
        serialization_spec = [
            ('teacher', [
                'name',
                ('school', [
                    'name'
                ])
            ])
        ]
        data = serializej(Class.objects.all()[:1], serialization_spec)
        self.assertEqual(data, [
            {
                'teacher': {
                    'name': 'Mr Cat',
                    'school': {
                        'name': 'Kitteh High',
                    }
                }
            },
        ])

    def xtest_reverse_fk_with_spec(self):
        serialization_spec = [
            'name',
            ('teacher_set', [
                'name',
            ])
        ]
        data = serializej(School.objects.all(), serialization_spec)
        self.assertEqual(data, [{
            'name': 'Kitteh High',
            'teacher_set': [
                {'name': 'Mr Cat'},
                {'name': 'Ms Dog'},
            ]
        }])

    def test_m2m(self):
        serialization_spec = [
            'name',
            'classes'
        ]
        data = serializej(Student.objects.all(), serialization_spec)
        self.assertEqual(data, [
            {'name': 'Student 0', 'classes': [str(self.french_class.id)]},
            {'name': 'Student 1', 'classes': [str(self.french_class.id)]},
            {'name': 'Student 2', 'classes': [str(self.math_class.id)]},
            {'name': 'Student 3', 'classes': [str(self.math_class.id)]},
        ])

    def test_m2m_with_spec(self):
        serialization_spec = [
            'name',
            ('classes', [
                'name'
            ])
        ]
        data = serializej(Student.objects.all(), serialization_spec)
        self.assertEqual(data, [
            {'name': 'Student 0', 'classes': [{'name': 'French A'}]},
            {'name': 'Student 1', 'classes': [{'name': 'French A'}]},
            {'name': 'Student 2', 'classes': [{'name': 'Math B'}]},
            {'name': 'Student 3', 'classes': [{'name': 'Math B'}]},
        ])

    def test_reverse_m2m(self):
        serialization_spec = [
            'name',
            'assignees',
        ]
        data = serializej(Assignment.objects.all(), serialization_spec)
        self.assertEqual(data, [
            {'name': 'French A Assignment', 'assignees': [str(self.student.id)]},
            {'name': 'Math B Assignment', 'assignees': [str(self.student.id)]},
        ])

    def test_reverse_m2m_with_spec(self):
        serialization_spec = [
            'name',
            ('assignees', [
                'name'
            ])
        ]
        data = serializej(Assignment.objects.all(), serialization_spec)
        self.assertEqual(data, [
            {'assignees': [{'name': 'Student 0'}], 'name': 'French A Assignment'},
            {'assignees': [{'name': 'Student 0'}], 'name': 'Math B Assignment'},
        ])
