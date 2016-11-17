#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import codecs
from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding='utf-8').read()


setup(
    name='pytest-leaks',
    version='0.2.0',
    author='Alexander Belopolsky',
    author_email='alexander.belopolsky@gmail.com',
    maintainer='Alexander Belopolsky',
    maintainer_email='alexander.belopolsky@gmail.com',
    license='MIT',
    url='https://github.com/abalkin/pytest-leaks',
    description='A pytest plugin to trace resource leaks.',
    long_description=read('README.rst'),
    py_modules=['pytest_leaks'],
    install_requires=['pytest>=2.9.2'],
    classifiers=[
        'Development Status :: 1 - Planning',
        'Framework :: Pytest',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
    ],
    entry_points={
        'pytest11': [
            'leaks = pytest_leaks',
        ],
    },
)
