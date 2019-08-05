# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from typing import Dict, Tuple, List  # noqa
import dj_database_url
import os
import environ
import logging

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ''),
    TEST_RUNNER=(str, 'django.test.runner.DiscoverRunner'),
    IN_TEST=(bool, False),
    ALLOW_WEAK_PASSWORDS=(bool, False),
    SECURE_SSL_REDIRECT=(bool, False),
    ENFORCE_HOST=(list, ''),
    RAVEN_DSN=(str, ''),
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = env('SECRET_KEY')

DEBUG = env('DEBUG')

# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',

    'rest_framework',
    'tests',
    'serialization_spec',
]  # type: List[str]

ROOT_URLCONF = 'tests.urls'

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ['DATABASE_URL'],
        conn_max_age=300
    )
}

REST_FRAMEWORK = {
    'PAGE_SIZE': 10
}


TEST_RUNNER = env('TEST_RUNNER')

if env('IN_TEST'):
    logging.disable(logging.ERROR)
