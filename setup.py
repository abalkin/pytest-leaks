#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import io
from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    with io.open(file_path, encoding='utf-8') as f:
        return f.read()


AUTHORS = [
    "Alexander Belopolsky",
    "Pauli Virtanen"
]


setup(
    name='pytest-leaks',
    use_scm_version={"write_to": "pytest_leaks/_version.py"},
    author=", ".join(AUTHORS),
    author_email='alexander.belopolsky@gmail.com',
    maintainer=", ".join(AUTHORS),
    maintainer_email='alexander.belopolsky@gmail.com',
    license='MIT and Python-2.0',
    url='https://github.com/abalkin/pytest-leaks',
    description='A pytest plugin to trace resource leaks.',
    long_description=read('README.md'),
    long_description_content_type="text/markdown",
    packages=['pytest_leaks'],
    install_requires=['pytest>=3'],
    setup_requires=["setuptools-scm", "setuptools>=40.0"],
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*',
    classifiers=[
        'Development Status :: 1 - Planning',
        'Framework :: Pytest',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: Python Software Foundation License',
        'License :: OSI Approved :: MIT License',
    ],
    entry_points={
        'pytest11': [
            'leaks = pytest_leaks.plugin',
        ],
    },
)
