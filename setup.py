#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
import os
import re

# Fix for issues with testing, experienced on win10
import multiprocessing

root = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(root, "box", "__init__.py"), "r") as init_file:
    init_content = init_file.read()

attrs = dict(re.findall(r"__([a-z]+)__ *= *['\"](.+)['\"]", init_content))

with open("README.rst", "r") as readme_file:
    long_description = readme_file.read()

setup(
    name='python-box',
    version=attrs['version'],
    url='https://github.com/cdgriffith/Box',
    license='MIT',
    author=attrs['author'],
    install_requires=['toml', 'ruamel.yaml'],
    author_email='chris@cdgriffith.com',
    description='Advanced Python dictionaries with dot notation access',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    py_modules=['box'],
    packages=['box'],
    python_requires='>=3.6',
    include_package_data=True,
    platforms='any',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
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
    ]
)
