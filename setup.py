#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
import os
import re

# Fix for issues with testing, experienced on win10
import multiprocessing

root = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(root, "box.py"), "r") as reuse_file:
    reuse_content = reuse_file.read()

attrs = dict(re.findall(r"__([a-z]+)__ *= *['\"](.+)['\"]", reuse_content))

with open("README.rst", "r") as readme_file:
    long_description = readme_file.read()

setup(
    name='python-box',
    version=attrs['version'],
    url='https://github.com/cdgriffith/Box',
    license='MIT',
    author=attrs['author'],
    tests_require=["pytest", "coverage >= 3.6", "pytest-cov"],
    install_requires=[],
    author_email='chris@cdgriffith.com',
    description='Advanced Python dictionaries with dot notation access',
    long_description=long_description,
    scripts=['box.py'],
    py_modules=['box'],
    include_package_data=True,
    platforms='any',
    setup_requires=['pytest-runner'],
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Development Status :: 5 - Production/Stable',
        'Natural Language :: English',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Utilities',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries :: Python Modules'
        ],
    extras_require={
        'testing': ["pytest", "coverage >= 3.6", "pytest-cov"],
        },
)
