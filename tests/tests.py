import json
from django.test import TestCase
from rest_framework.test import APIClient
from django.core.urlresolvers import reverse
from django.db import connection
from django.test.utils import CaptureQueriesContext

from serialization_spec.serialization import normalise_spec
from .models import LEA, School, Teacher, Subject, Class, Student, Assignment, AssignmentStudent


class BaseTestCase(TestCase):

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def assert_status(self, response, status_code):
        return self.assertEqual(
            response.status_code,
            status_code,
            'Status code of {} does not match expectation of {}.\nThe response body states {}'.format(
                response.status_code,
                status_code,
                str(response.data)
            )
        )

    def assertJsonEqual(self, expected, actual):
        self.assertEqual(
            json.dumps(expected, indent=4, sort_keys=True),
            json.dumps(actual, indent=4, sort_keys=True)
        )


def uuid(tail):
    return '00000000-0000-0000-0000-000000000000'[:-len(tail)] + tail


class SerializationSpecTestCase(BaseTestCase):

    def setUp(self):
        self.maxDiff = None

        self.lea = LEA.objects.create(id=uuid('0'), name='Brighton & Hove')
        self.school = School.objects.create(id=uuid('1'), name='Kitteh High', lea=self.lea)
        School.objects.create(id=uuid('8'), name='Hove High', lea=self.lea)
        self.teacher = Teacher.objects.create(id=uuid('2'), name='Mr Cat', school=self.school)
        Teacher.objects.create(id=uuid('7'), name='Ms Dog', school=self.school)
        self.french = Subject.objects.create(id=uuid('3'), name='French')
        self.math = Subject.objects.create(id=uuid('4'), name='Math')
        self.french_class = Class.objects.create(id=uuid('5'), name='French A', subject=self.french, teacher=self.teacher)
        self.math_class = Class.objects.create(id=uuid('6'), name='Math B', subject=self.math, teacher=self.teacher)
        students = [
            Student.objects.create(id=uuid('1%d' % idx), name='Student %d' % idx, school=self.school)
            for idx in range(10)
        ]
        self.french_class.student_set.set(students[:7])
        self.math_class.student_set.set(students[3:])

        self.student = students[5]
        for clasz in [self.french_class, self.math_class]:
            is_math = clasz == self.math_class
            assignment = Assignment.objects.create(id=uuid('2%d' % (0 if is_math else 1)), clasz=clasz, name=clasz.name + ' Assignment')
            AssignmentStudent.objects.create(
                assignment=assignment, student=self.student, is_complete=is_math
            )
        self.assignment = assignment


class DetailViewTestCase(SerializationSpecTestCase):

    def test_single_fk_and_reverse_fk(self):
        with CaptureQueriesContext(connection) as capture:
            url = reverse('teacher-detail', kwargs={'id': str(self.teacher.id)})
            response = self.client.get(url)

        self.assertJsonEqual(
            [query['sql'] for query in capture.captured_queries],
            [
                """SELECT "tests_teacher"."id", "tests_teacher"."name", "tests_teacher"."school_id", "tests_school"."id", "tests_school"."created", "tests_school"."modified", "tests_school"."name", "tests_school"."lea_id" FROM "tests_teacher" INNER JOIN "tests_school" ON ("tests_teacher"."school_id" = "tests_school"."id") WHERE "tests_teacher"."id" = '00000000-0000-0000-0000-000000000002'::uuid""",
                """SELECT "tests_class"."id", "tests_class"."name", "tests_class"."teacher_id" FROM "tests_class" WHERE "tests_class"."teacher_id" IN ('00000000-0000-0000-0000-000000000002'::uuid)"""
            ]
        )

        self.assertJsonEqual(response.data, {
            'id': uuid('2'),
            'name': 'Mr Cat',
            'school': {  # FK
                'id': uuid('1'),
                'name': 'Kitteh High',
            },
            "class_set": [  # reverse FK
                {
                    "id": uuid("6"),
                    "name": "Math B"
                },
                {
                    "id": uuid("5"),
                    "name": "French A"
                }
            ],
        })

    def test_single_many_to_many(self):
        with CaptureQueriesContext(connection) as capture:
            url = reverse('student-detail', kwargs={'id': str(self.student.id)})
            response = self.client.get(url)

        self.assertJsonEqual(
            [query['sql'] for query in capture.captured_queries],
            [
                """SELECT "tests_student"."id", "tests_student"."name" FROM "tests_student" WHERE "tests_student"."id" = '00000000-0000-0000-0000-000000000015'::uuid""",
                """SELECT ("tests_student_classes"."student_id") AS "_prefetch_related_val_student_id", "tests_class"."id", "tests_class"."name" FROM "tests_class" INNER JOIN "tests_student_classes" ON ("tests_class"."id" = "tests_student_classes"."class_id") WHERE "tests_student_classes"."student_id" IN ('00000000-0000-0000-0000-000000000015'::uuid)"""
            ]
        )

        self.assertJsonEqual(response.data, {
            'id': uuid('15'),
            'name': 'Student 5',
            "classes": [  # M:M
                {
                    "id": uuid("5"),
                    "name": "French A"
                },
                {
                    "id": uuid("6"),
                    "name": "Math B"
                },
            ],
        })

    def test_single_fk_on_fk(self):
        with CaptureQueriesContext(connection) as capture:
            url = reverse('class-detail', kwargs={'id': str(self.math_class.id)})
            response = self.client.get(url)

        self.assertJsonEqual(
            [query['sql'] for query in capture.captured_queries],
            [
                """SELECT "tests_class"."id", "tests_class"."name", "tests_class"."teacher_id", "tests_teacher"."id", "tests_teacher"."created", "tests_teacher"."modified", "tests_teacher"."name", "tests_teacher"."school_id", "tests_school"."id", "tests_school"."created", "tests_school"."modified", "tests_school"."name", "tests_school"."lea_id" FROM "tests_class" INNER JOIN "tests_teacher" ON ("tests_class"."teacher_id" = "tests_teacher"."id") INNER JOIN "tests_school" ON ("tests_teacher"."school_id" = "tests_school"."id") WHERE "tests_class"."id" = '00000000-0000-0000-0000-000000000006'::uuid"""
            ]
        )

        self.assertJsonEqual(response.data, {
            'id': uuid('6'),
            'name': 'Math B',
            "teacher": {  # FK
                "id": uuid("2"),
                "name": "Mr Cat",
                "school": {  # FK > FK
                    "id": uuid("1"),
                    "name": "Kitteh High"
                },
            },
        })

    def test_single_fk_on_many_to_many(self):
        with CaptureQueriesContext(connection) as capture:
            url = reverse('subject-detail', kwargs={'id': str(self.math.id)})
            response = self.client.get(url)

        self.assertJsonEqual(
            [query['sql'] for query in capture.captured_queries],
            [
                """SELECT "tests_subject"."id", "tests_subject"."name" FROM "tests_subject" WHERE "tests_subject"."id" = '00000000-0000-0000-0000-000000000004'::uuid""",
                """SELECT "tests_class"."id", "tests_class"."subject_id", "tests_class"."name", "tests_class"."teacher_id", "tests_teacher"."id", "tests_teacher"."created", "tests_teacher"."modified", "tests_teacher"."name", "tests_teacher"."school_id" FROM "tests_class" INNER JOIN "tests_teacher" ON ("tests_class"."teacher_id" = "tests_teacher"."id") WHERE "tests_class"."subject_id" IN ('00000000-0000-0000-0000-000000000004'::uuid)"""
            ]
        )

        self.assertJsonEqual(response.data, {
            "id": uuid("4"),
            "name": "Math",
            "class_set": [
                {
                    "id": uuid("6"),
                    "name": "Math B",
                    "teacher": {
                        "id": uuid("2"),
                        "name": "Mr Cat"
                    }
                }
            ],
        })

    def test_single_reverse_fk_on_fk(self):
        with CaptureQueriesContext(connection) as capture:
            url = reverse('school-detail', kwargs={'id': str(self.school.id)})
            response = self.client.get(url)

        self.assertJsonEqual(
            [query['sql'] for query in capture.captured_queries],
            [
                """SELECT "tests_school"."id", "tests_school"."name", "tests_school"."lea_id", "tests_lea"."id", "tests_lea"."created", "tests_lea"."modified", "tests_lea"."name" FROM "tests_school" INNER JOIN "tests_lea" ON ("tests_school"."lea_id" = "tests_lea"."id") WHERE "tests_school"."id" = '00000000-0000-0000-0000-000000000001'::uuid""",
                """SELECT "tests_school"."id", "tests_school"."name", "tests_school"."lea_id" FROM "tests_school" WHERE "tests_school"."lea_id" IN ('00000000-0000-0000-0000-000000000000'::uuid)"""
            ]
        )

        self.assertJsonEqual(response.data, {
            "id": uuid("1"),
            "name": "Kitteh High",
            "lea": {
                "id": uuid("0"),
                "name": "Brighton & Hove",
                "school_set": [
                    {
                        "id": uuid("8"),
                        "name": "Hove High"
                    },
                    {
                        "id": uuid("1"),
                        "name": "Kitteh High"
                    }
                ]
            },
        })

    def test_single_many_to_many_with_through(self):
        with CaptureQueriesContext(connection) as capture:
            url = reverse('student-with-assignments-detail', kwargs={'id': str(self.student.id)})
            response = self.client.get(url)

        self.assertJsonEqual(
            [query['sql'] for query in capture.captured_queries],
            [
                """SELECT "tests_student"."id", "tests_student"."name" FROM "tests_student" WHERE "tests_student"."id" = '00000000-0000-0000-0000-000000000015'::uuid""",
                """SELECT ("tests_assignmentstudent"."student_id") AS "_prefetch_related_val_student_id", "tests_assignment"."id", "tests_assignment"."name" FROM "tests_assignment" INNER JOIN "tests_assignmentstudent" ON ("tests_assignment"."id" = "tests_assignmentstudent"."assignment_id") WHERE "tests_assignmentstudent"."student_id" IN ('00000000-0000-0000-0000-000000000015'::uuid)""",
                """SELECT "tests_assignmentstudent"."id", "tests_assignmentstudent"."is_complete", "tests_assignmentstudent"."assignment_id", "tests_assignmentstudent"."student_id", "tests_assignment"."id", "tests_assignment"."created", "tests_assignment"."modified", "tests_assignment"."name", "tests_assignment"."clasz_id" FROM "tests_assignmentstudent" INNER JOIN "tests_assignment" ON ("tests_assignmentstudent"."assignment_id" = "tests_assignment"."id") WHERE "tests_assignmentstudent"."student_id" IN ('00000000-0000-0000-0000-000000000015'::uuid)"""
            ]
        )

        self.assertJsonEqual(response.data, {
            'id': uuid('15'),
            'name': 'Student 5',
            "assignments": [  # M:M
                {"name": "French A Assignment"},
                {"name": "Math B Assignment"}
            ],
            "assignmentstudent_set": [  # M:M through relation
                {
                    "assignment": {"name": "French A Assignment"},
                    "is_complete": False
                },
                {
                    "assignment": {"name": "Math B Assignment"},
                    "is_complete": True
                }
            ],
        })

    def test_single_count_plugin(self):
        with CaptureQueriesContext(connection) as capture:
            url = reverse('assignment-detail', kwargs={'id': str(self.assignment.id)})
            response = self.client.get(url)

        self.assertJsonEqual(
            [query['sql'] for query in capture.captured_queries],
            [
                "SELECT \"tests_assignment\".\"id\", \"tests_assignment\".\"name\", \"tests_assignment\".\"clasz_id\", \"tests_class\".\"id\", \"tests_class\".\"created\", \"tests_class\".\"modified\", \"tests_class\".\"subject_id\", \"tests_class\".\"name\", \"tests_class\".\"teacher_id\", \"tests_teacher\".\"id\", \"tests_teacher\".\"created\", \"tests_teacher\".\"modified\", \"tests_teacher\".\"name\", \"tests_teacher\".\"school_id\" FROM \"tests_assignment\" INNER JOIN \"tests_class\" ON (\"tests_assignment\".\"clasz_id\" = \"tests_class\".\"id\") INNER JOIN \"tests_teacher\" ON (\"tests_class\".\"teacher_id\" = \"tests_teacher\".\"id\") WHERE \"tests_assignment\".\"id\" = '00000000-0000-0000-0000-000000000020'::uuid",
                "SELECT (\"tests_assignmentstudent\".\"assignment_id\") AS \"_prefetch_related_val_assignment_id\", \"tests_student\".\"id\", \"tests_student\".\"name\", COUNT(\"tests_student_classes\".\"class_id\") AS \"classes_count\" FROM \"tests_student\" LEFT OUTER JOIN \"tests_student_classes\" ON (\"tests_student\".\"id\" = \"tests_student_classes\".\"student_id\") INNER JOIN \"tests_assignmentstudent\" ON (\"tests_student\".\"id\" = \"tests_assignmentstudent\".\"student_id\") WHERE \"tests_assignmentstudent\".\"assignment_id\" IN ('00000000-0000-0000-0000-000000000020'::uuid) GROUP BY (\"tests_assignmentstudent\".\"assignment_id\"), \"tests_student\".\"id\"",
                "SELECT (\"tests_student_classes\".\"student_id\") AS \"_prefetch_related_val_student_id\", \"tests_class\".\"id\" FROM \"tests_class\" INNER JOIN \"tests_student_classes\" ON (\"tests_class\".\"id\" = \"tests_student_classes\".\"class_id\") WHERE \"tests_student_classes\".\"student_id\" IN ('00000000-0000-0000-0000-000000000015'::uuid)",
            ]
        )

        self.assertJsonEqual(response.data, {
            "id": uuid("20"),
            "name": "Math B Assignment",
            "assignees": [
                {
                    "id": uuid("15"),
                    "name": "Student 5",
                    "classes_count": 2,
                    "classes": [
                        uuid("5"),
                        uuid("6"),
                    ]
                }
            ],
            "class_name": "Math B - Mr Cat",
        })


class ListViewTestCase(SerializationSpecTestCase):

    def test_single_fk_and_reverse_fk(self):
        with CaptureQueriesContext(connection) as capture:
            response = self.client.get(reverse('teacher-list'))

        self.assertJsonEqual(
            [query['sql'] for query in capture.captured_queries],
            [
                "SELECT COUNT(*) AS \"__count\" FROM \"tests_teacher\"",
                "SELECT \"tests_teacher\".\"id\", \"tests_teacher\".\"name\", \"tests_teacher\".\"school_id\" FROM \"tests_teacher\" ORDER BY \"tests_teacher\".\"name\" ASC LIMIT 2",
                "SELECT \"tests_school\".\"id\", \"tests_school\".\"name\" FROM \"tests_school\" WHERE \"tests_school\".\"id\" IN ('00000000-0000-0000-0000-000000000001'::uuid)",
                "SELECT \"tests_class\".\"id\", \"tests_class\".\"name\", \"tests_class\".\"teacher_id\" FROM \"tests_class\" WHERE \"tests_class\".\"teacher_id\" IN ('00000000-0000-0000-0000-000000000002'::uuid, '00000000-0000-0000-0000-000000000007'::uuid)"
            ]
        )

        self.assertJsonEqual(response.data, {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [
                {
                    'id': uuid('2'),
                    'name': 'Mr Cat',
                    'school': {  # FK
                        'id': uuid('1'),
                        'name': 'Kitteh High',
                    },
                    "class_set": [  # reverse FK
                        {
                            "id": uuid("5"),
                            "name": "French A"
                        },
                        {
                            "id": uuid("6"),
                            "name": "Math B"
                        },
                    ],
                },
                {
                    "id": uuid('7'),
                    "name": "Ms Dog",
                    "school": {
                        "id": uuid("1"),
                        "name": "Kitteh High"
                    },
                    "class_set": [],
                }
            ]
        })


class NormalisationTestCase(TestCase):

    def test_base_case(self):
        spec = [
            'one',
            {'two': [
                'three',
            ]},
            {'four': []},
        ]

        self.assertEqual(normalise_spec(spec), [
            'one',
            {
                'four': [],
                'two': [
                    'three',
                ],
            },
        ])

    def test_merge_dupes_one_level(self):
        spec = [
            'one',
            {'two': [
                'three',
            ]},
            'one',
        ]

        self.assertEqual(normalise_spec(spec), [
            'one',
            {
                'two': [
                    'three',
                ],
            },
        ])

    def test_merge_dupes_two_levels(self):
        spec = [
            'one',
            {'two': [
                'three',
            ]},
            {'two': [
                'four',
            ]},
        ]

        self.assertEqual(normalise_spec(spec), [
            'one',
            {
                'two': [
                    'three',
                    'four',
                ],
            },
        ])

    def test_merge_dupes_three_levels(self):
        spec = [
            'one',
            {'two': [
                {'three': [
                    'five'
                ]}
            ]},
            {'two': [
                'four',
                {'three': [
                    'five',
                    'six'
                ]}
            ]},
        ]

        self.assertEqual(normalise_spec(spec), [
            'one',
            {'two': [
                'four',
                {'three': [
                    'five',
                    'six',
                ]}
            ]}
        ])
