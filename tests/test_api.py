import django
import json
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from django.db import connection
from django.test.utils import CaptureQueriesContext

from .models import LEA, School, Teacher, Subject, Class, Student, Assignment, AssignmentStudent


def django_version_compat(captured_queries):
    # Handles changes introduced by https://code.djangoproject.com/ticket/6785
    def fix_query(query):
        if query["sql"].endswith(" LIMIT 21"):
            query["sql"] = query["sql"].replace(" LIMIT 21", "")
        if "  LIMIT" in query["sql"]:
            query["sql"] = query["sql"].replace("  LIMIT", " LIMIT")
        return query
    return [fix_query(query) for query in captured_queries]


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
                id=uuid('3%d' % (0 if is_math else 1)), assignment=assignment, student=self.student, is_complete=is_math
            )
        self.assignment = assignment


class DetailViewTestCase(SerializationSpecTestCase):

    def test_single_fk_and_reverse_fk(self):
        with CaptureQueriesContext(connection) as capture:
            url = reverse('teacher-detail', kwargs={'id': str(self.teacher.id)})
            response = self.client.get(url)

        self.assertJsonEqual(
            sorted(query['sql'] for query in django_version_compat(capture.captured_queries)),
            [
                """SELECT "tests_class"."id", "tests_class"."name", "tests_class"."teacher_id" FROM "tests_class" WHERE "tests_class"."teacher_id" IN ('00000000000000000000000000000002') ORDER BY "tests_class"."id" ASC""",
                """SELECT "tests_teacher"."id", "tests_teacher"."name", "tests_teacher"."school_id", "tests_school"."id", "tests_school"."created", "tests_school"."modified", "tests_school"."name", "tests_school"."lea_id" FROM "tests_teacher" INNER JOIN "tests_school" ON ("tests_teacher"."school_id" = "tests_school"."id") WHERE "tests_teacher"."id" = '00000000000000000000000000000002'""",
            ]
        )

        self.assertJsonEqual(response.data, {
            'id': uuid('2'),
            'name': 'Mr Cat',
            'school': {  # FK
                'id': uuid('1'),
                'name': 'Kitteh High',
            },
            "classes": [  # reverse FK
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

    def test_single_many_to_many(self):
        with CaptureQueriesContext(connection) as capture:
            url = reverse('student-detail', kwargs={'id': str(self.student.id)})
            response = self.client.get(url)

        self.assertJsonEqual(
            sorted(query['sql'] for query in django_version_compat(capture.captured_queries)),
            [
                """SELECT "tests_student"."id", "tests_student"."name" FROM "tests_student" WHERE "tests_student"."id" = '00000000000000000000000000000015'""",
                """SELECT ("tests_student_classes"."student_id") AS "_prefetch_related_val_student_id", "tests_class"."id", "tests_class"."name" FROM "tests_class" INNER JOIN "tests_student_classes" ON ("tests_class"."id" = "tests_student_classes"."class_id") WHERE "tests_student_classes"."student_id" IN ('00000000000000000000000000000015') ORDER BY "tests_class"."id" ASC"""
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

    def test_single_fk_on_fk_and_reverse_m2m(self):
        with CaptureQueriesContext(connection) as capture:
            url = reverse('class-detail', kwargs={'id': str(self.math_class.id)})
            response = self.client.get(url)

        self.assertJsonEqual(
            sorted(query['sql'] for query in django_version_compat(capture.captured_queries)),
            [
                """SELECT "tests_class"."id", "tests_class"."name", "tests_class"."teacher_id", "tests_teacher"."id", "tests_teacher"."created", "tests_teacher"."modified", "tests_teacher"."name", "tests_teacher"."school_id", "tests_school"."id", "tests_school"."created", "tests_school"."modified", "tests_school"."name", "tests_school"."lea_id" FROM "tests_class" INNER JOIN "tests_teacher" ON ("tests_class"."teacher_id" = "tests_teacher"."id") INNER JOIN "tests_school" ON ("tests_teacher"."school_id" = "tests_school"."id") WHERE "tests_class"."id" = '00000000000000000000000000000006'""",
                """SELECT ("tests_student_classes"."class_id") AS "_prefetch_related_val_class_id", "tests_student"."id", "tests_student"."name" FROM "tests_student" INNER JOIN "tests_student_classes" ON ("tests_student"."id" = "tests_student_classes"."student_id") WHERE "tests_student_classes"."class_id" IN ('00000000000000000000000000000006') ORDER BY "tests_student"."id" ASC"""
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
            'student_set': [
                {'name': 'Student 3'}, {'name': 'Student 4'}, {'name': 'Student 5'}, {'name': 'Student 6'}, {'name': 'Student 7'}, {'name': 'Student 8'}, {'name': 'Student 9'},
            ]
        })

    def test_single_fk_on_many_to_many(self):
        with CaptureQueriesContext(connection) as capture:
            url = reverse('subject-detail', kwargs={'id': str(self.math.id)})
            response = self.client.get(url)

        self.assertJsonEqual(
            sorted(query['sql'] for query in django_version_compat(capture.captured_queries)),
            [
                """SELECT "tests_class"."id", "tests_class"."subject_id", "tests_class"."name", "tests_class"."teacher_id", "tests_teacher"."id", "tests_teacher"."created", "tests_teacher"."modified", "tests_teacher"."name", "tests_teacher"."school_id" FROM "tests_class" INNER JOIN "tests_teacher" ON ("tests_class"."teacher_id" = "tests_teacher"."id") WHERE "tests_class"."subject_id" IN ('00000000000000000000000000000004') ORDER BY "tests_class"."id" ASC""",
                """SELECT "tests_subject"."id", "tests_subject"."name" FROM "tests_subject" WHERE "tests_subject"."id" = '00000000000000000000000000000004'""",
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
            sorted(query['sql'] for query in django_version_compat(capture.captured_queries)),
            [
                """SELECT "tests_school"."id", "tests_school"."name", "tests_school"."lea_id" FROM "tests_school" WHERE "tests_school"."lea_id" IN ('00000000000000000000000000000000') ORDER BY "tests_school"."id" ASC""",
                """SELECT "tests_school"."id", "tests_school"."name", "tests_school"."lea_id", "tests_lea"."id", "tests_lea"."created", "tests_lea"."modified", "tests_lea"."name" FROM "tests_school" INNER JOIN "tests_lea" ON ("tests_school"."lea_id" = "tests_lea"."id") WHERE "tests_school"."id" = '00000000000000000000000000000001'""",
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
                        "id": uuid("1"),
                        "name": "Kitteh High"
                    },
                    {
                        "id": uuid("8"),
                        "name": "Hove High"
                    },
                ]
            },
        })

    def test_single_many_to_many_with_through(self):
        with CaptureQueriesContext(connection) as capture:
            url = reverse('student-with-assignments-detail', kwargs={'id': str(self.student.id)})
            response = self.client.get(url)

        self.assertJsonEqual(
            sorted(query['sql'] for query in django_version_compat(capture.captured_queries)),
            [
                """SELECT "tests_assignmentstudent"."id", "tests_assignmentstudent"."is_complete", "tests_assignmentstudent"."assignment_id", "tests_assignmentstudent"."student_id", "tests_assignment"."id", "tests_assignment"."created", "tests_assignment"."modified", "tests_assignment"."name", "tests_assignment"."clasz_id" FROM "tests_assignmentstudent" INNER JOIN "tests_assignment" ON ("tests_assignmentstudent"."assignment_id" = "tests_assignment"."id") WHERE "tests_assignmentstudent"."student_id" IN ('00000000000000000000000000000015') ORDER BY "tests_assignmentstudent"."id" ASC""",
                """SELECT "tests_student"."id", "tests_student"."name" FROM "tests_student" WHERE "tests_student"."id" = '00000000000000000000000000000015'""",
                """SELECT ("tests_assignmentstudent"."student_id") AS "_prefetch_related_val_student_id", "tests_assignment"."id", "tests_assignment"."name" FROM "tests_assignment" INNER JOIN "tests_assignmentstudent" ON ("tests_assignment"."id" = "tests_assignmentstudent"."assignment_id") WHERE "tests_assignmentstudent"."student_id" IN ('00000000000000000000000000000015') ORDER BY "tests_assignment"."id" ASC""",
            ]
        )

        self.assertJsonEqual(response.data, {
            'id': uuid('15'),
            'name': 'Student 5',
            "assignments": [  # M:M
                {"name": "Math B Assignment"},
                {"name": "French A Assignment"},
            ],
            "assignmentstudent_set": [  # M:M through relation
                {
                    "assignment": {"name": "Math B Assignment"},
                    "is_complete": True
                },
                {
                    "assignment": {"name": "French A Assignment"},
                    "is_complete": False
                },
            ],
        })

    def test_single_count_plugin(self):
        with CaptureQueriesContext(connection) as capture:
            url = reverse('assignment-detail', kwargs={'id': str(self.assignment.id)})
            response = self.client.get(url)

        if django.VERSION >= (3, 1, 0):
            self.assertJsonEqual(
                sorted(query['sql'] for query in django_version_compat(capture.captured_queries)),
                [
                    """SELECT "tests_assignment"."id", "tests_assignment"."name", "tests_assignment"."clasz_id" FROM "tests_assignment" WHERE "tests_assignment"."id" = '00000000000000000000000000000020'""",
                    """SELECT "tests_class"."id", "tests_class"."name", "tests_class"."teacher_id", COUNT(DISTINCT "tests_student_classes"."student_id") AS "student_count", "tests_teacher"."id", "tests_teacher"."created", "tests_teacher"."modified", "tests_teacher"."name", "tests_teacher"."school_id" FROM "tests_class" LEFT OUTER JOIN "tests_student_classes" ON ("tests_class"."id" = "tests_student_classes"."class_id") INNER JOIN "tests_teacher" ON ("tests_class"."teacher_id" = "tests_teacher"."id") WHERE "tests_class"."id" IN ('00000000000000000000000000000006') GROUP BY "tests_class"."id", "tests_class"."name", "tests_class"."teacher_id", "tests_teacher"."id", "tests_teacher"."created", "tests_teacher"."modified", "tests_teacher"."name", "tests_teacher"."school_id\"""",
                    """SELECT ("tests_assignmentstudent"."assignment_id") AS "_prefetch_related_val_assignment_id", "tests_student"."id", "tests_student"."name", COUNT(DISTINCT "tests_student_classes"."class_id") AS "classes_count" FROM "tests_student" LEFT OUTER JOIN "tests_student_classes" ON ("tests_student"."id" = "tests_student_classes"."student_id") INNER JOIN "tests_assignmentstudent" ON ("tests_student"."id" = "tests_assignmentstudent"."student_id") WHERE "tests_assignmentstudent"."assignment_id" IN ('00000000000000000000000000000020') GROUP BY ("tests_assignmentstudent"."assignment_id"), "tests_student"."id", "tests_student"."name\"""",
                    """SELECT ("tests_student_classes"."student_id") AS "_prefetch_related_val_student_id", "tests_class"."id" FROM "tests_class" INNER JOIN "tests_student_classes" ON ("tests_class"."id" = "tests_student_classes"."class_id") WHERE "tests_student_classes"."student_id" IN ('00000000000000000000000000000015') ORDER BY "tests_class"."id" ASC""",
                ]
            )
        else:
            self.assertJsonEqual(
                sorted(query['sql'] for query in django_version_compat(capture.captured_queries)),
                [
                    """SELECT "tests_assignment"."id", "tests_assignment"."name", "tests_assignment"."clasz_id" FROM "tests_assignment" WHERE "tests_assignment"."id" = '00000000000000000000000000000020'""",
                    """SELECT "tests_class"."id", "tests_class"."name", "tests_class"."teacher_id", COUNT(DISTINCT "tests_student_classes"."student_id") AS "student_count", "tests_teacher"."id", "tests_teacher"."created", "tests_teacher"."modified", "tests_teacher"."name", "tests_teacher"."school_id" FROM "tests_class" LEFT OUTER JOIN "tests_student_classes" ON ("tests_class"."id" = "tests_student_classes"."class_id") INNER JOIN "tests_teacher" ON ("tests_class"."teacher_id" = "tests_teacher"."id") WHERE "tests_class"."id" IN ('00000000000000000000000000000006') GROUP BY "tests_class"."id", "tests_class"."name", "tests_class"."teacher_id", "tests_teacher"."id", "tests_teacher"."created", "tests_teacher"."modified", "tests_teacher"."name", "tests_teacher"."school_id" ORDER BY "tests_class"."id" ASC""",
                    """SELECT ("tests_assignmentstudent"."assignment_id") AS "_prefetch_related_val_assignment_id", "tests_student"."id", "tests_student"."name", COUNT(DISTINCT "tests_student_classes"."class_id") AS "classes_count" FROM "tests_student" LEFT OUTER JOIN "tests_student_classes" ON ("tests_student"."id" = "tests_student_classes"."student_id") INNER JOIN "tests_assignmentstudent" ON ("tests_student"."id" = "tests_assignmentstudent"."student_id") WHERE "tests_assignmentstudent"."assignment_id" IN ('00000000000000000000000000000020') GROUP BY ("tests_assignmentstudent"."assignment_id"), "tests_student"."id", "tests_student"."name" ORDER BY "tests_student"."id" ASC""",
                    """SELECT ("tests_student_classes"."student_id") AS "_prefetch_related_val_student_id", "tests_class"."id" FROM "tests_class" INNER JOIN "tests_student_classes" ON ("tests_class"."id" = "tests_student_classes"."class_id") WHERE "tests_student_classes"."student_id" IN ('00000000000000000000000000000015') ORDER BY "tests_class"."id" ASC""",
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
            "clasz": {
                "num_students": 7
            },
        })


class ListViewTestCase(SerializationSpecTestCase):

    def test_single_fk_and_reverse_fk(self):
        with CaptureQueriesContext(connection) as capture:
            response = self.client.get(reverse('teacher-list'))

        self.assertJsonEqual(
            sorted(query['sql'] for query in django_version_compat(capture.captured_queries)),
            [
                """SELECT "tests_class"."id", "tests_class"."name", "tests_class"."teacher_id" FROM "tests_class" WHERE "tests_class"."teacher_id" IN ('00000000000000000000000000000002', '00000000000000000000000000000007') ORDER BY "tests_class"."id" ASC""",
                """SELECT "tests_school"."id", "tests_school"."name" FROM "tests_school" WHERE "tests_school"."id" IN ('00000000000000000000000000000001') ORDER BY "tests_school"."id" ASC""",
                """SELECT "tests_teacher"."id", "tests_teacher"."name", "tests_teacher"."school_id" FROM "tests_teacher" ORDER BY "tests_teacher"."name" ASC LIMIT 2""",
                """SELECT COUNT(*) AS "__count" FROM "tests_teacher\""""
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


class MisconfiguredViewTestCase(SerializationSpecTestCase):

    def test_view_must_have_serialization_spec(self):
        with self.assertRaises(ImproperlyConfigured) as cm:
            self.client.get(reverse('misconfigured'))

        self.assertEqual(str(cm.exception), 'SerializationSpecMixin requires serialization_spec or get_serialization_spec')


class CollidingFieldsRegressionTestCase(SerializationSpecTestCase):

    def test_multiple_many_to_many_fields_do_not_collide(self):
        url = reverse('student-with-classes-and-assignments-detail', kwargs={'id': str(self.student.id)})
        response = self.client.get(url)

        self.assertJsonEqual(response.data, {
            'id': uuid('15'),
            'name': 'Student 5',
            "assignments": [
                uuid('20'),
                uuid('21'),
            ],
            "classes": [
                uuid('5'),
                uuid('6'),
            ],
        })
