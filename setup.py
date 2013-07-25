# -*- encoding: utf-8 -*-
import os
from setuptools import setup, find_packages
import referee as app


def read(fname):
    try:
        return open(os.path.join(os.path.dirname(__file__), fname)).read()
    except IOError:
        return ''

setup(
    name="django-referee",
    version=app.__version__,
    description=read('DESCRIPTION'),
    long_description=read('README.rst'),
    license='The MIT License',
    platforms=['OS Independent'],
    keywords='django, app, reusable',
    author='Björn Andersson',
    author_email='ba@sanitarium.se',
    url="https://github.com/gaqzi/django-referee",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'django',
        'django_libs',
        'datetime_truncate',
    ],
)
