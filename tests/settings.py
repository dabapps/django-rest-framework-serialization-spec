# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from typing import Dict, Tuple, List  # noqa

SECRET_KEY = "abcde12345"

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',

    'rest_framework',
    'tests',
    'serialization_spec',
]  # type: List[str]

ROOT_URLCONF = 'tests.urls'

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

REST_FRAMEWORK = {
    'PAGE_SIZE': 10,
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
}
