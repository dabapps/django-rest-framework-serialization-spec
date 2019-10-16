#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from setuptools import setup
import re
import os
import sys


name = 'django-rest-framework-serialization-spec'
package = 'serialization_spec'
description = 'Specify API endpoint data shape declaratively in a DRF view'
url = 'https://www.dabapps.com'
author = 'DabApps'
author_email = 'engineering@dabapps.com'
license = 'BSD'
install_requires = [
    'Django>=1.11',
    'djangorestframework==3.5.3',
    'django-zen-queries==1.0.0'
]
long_description_content_type="text/markdown",
long_description = """
    ## Specify API endpoint data shape declaratively in a DRF view

    Given a serialization spec such as:

    ```
    class ItemDetail(SerializationSpecMixin, generics.RetrieveAPIView):

        queryset = Item.objects.all()
        serialization_spec = [
            'id',
            {'product': [
                'id',
                'name'
            ]},
            {'report_templates': [
                'id',
                'name'
            ]}
        ]
    ```

    1. Fetch the data required to populate this using a minimal set of queries
    2. Serialize it
    """

def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    init_py = open(os.path.join(package, '__init__.py')).read()
    return re.search("^__version__ = ['\"]([^'\"]+)['\"]", init_py, re.MULTILINE).group(1)


def get_packages(package):
    """
    Return root package and all sub-packages.
    """
    return [dirpath
            for dirpath, dirnames, filenames in os.walk(package)
            if os.path.exists(os.path.join(dirpath, '__init__.py'))]


def get_package_data(package):
    """
    Return all files under the root package, that are not in a
    package themselves.
    """
    walk = [(dirpath.replace(package + os.sep, '', 1), filenames)
            for dirpath, dirnames, filenames in os.walk(package)
            if not os.path.exists(os.path.join(dirpath, '__init__.py'))]

    filepaths = []
    for base, filenames in walk:
        filepaths.extend([os.path.join(base, filename)
                          for filename in filenames])
    return {package: filepaths}


if sys.argv[-1] == 'publish':
    os.system("python setup.py sdist upload")
    args = {'version': get_version(package)}
    print("You probably want to also tag the version now:")
    print("  git tag -a %(version)s -m 'version %(version)s'" % args)
    print("  git push --tags")
    sys.exit()


setup(
    name=name,
    version=get_version(package),
    url=url,
    license=license,
    description=description,
    long_description=long_description,
    author=author,
    author_email=author_email,
    packages=get_packages(package),
    package_data=get_package_data(package),
    install_requires=install_requires,
    classifiers=[
    ]
)