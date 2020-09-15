from django.test import TestCase

from serialization_spec.serialization import normalise_spec


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
                'two': [
                    'three',
                ],
                'four': [],
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
            {'two': [
                'three',
            ]},
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
            {'two': [
                'three',
                'four',
            ]},
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
