#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Must import multiprocessing as a fix for issues with testing, experienced on win10
import multiprocessing  # noqa: F401
import os
import re
from pathlib import Path
import sys

from setuptools import setup

root = os.path.abspath(os.path.dirname(__file__))

try:
    from Cython.Build import cythonize
except ImportError:
    extra = None
else:
    extra = cythonize(
        [str(file.relative_to(root)) for file in Path(root, "box").glob("*.py") if file.name != "__init__.py"],
        compiler_directives={"language_level": 3},
    )

with open(os.path.join(root, "box", "__init__.py"), "r") as init_file:
    init_content = init_file.read()

attrs = dict(re.findall(r"__([a-z]+)__ *= *['\"](.+)['\"]", init_content))

with open("README.rst", "r") as readme_file:
    long_description = readme_file.read()

setup(
    name="python-box",
    version=attrs["version"],
    url="https://github.com/cdgriffith/Box",
    license="MIT",
    author=attrs["author"],
    install_requires=[],
    author_email="chris@cdgriffith.com",
    description="Advanced Python dictionaries with dot notation access",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    py_modules=["box"],
    packages=["box"],
    ext_modules=extra,
    python_requires=">=3.7",
    include_package_data=True,
    platforms="any",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: Implementation :: CPython",
        "Development Status :: 5 - Production/Stable",
        "Natural Language :: English",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Utilities",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    extras_require={
        "all": ["ruamel.yaml>=0.17", "tomli; python_version < '3.11'", "tomli-w", "msgpack"],
        "yaml": ["ruamel.yaml>=0.17"],
        "ruamel.yaml": ["ruamel.yaml>=0.17"],
        "PyYAML": ["PyYAML"],
        "tomli": ["tomli; python_version < '3.11'", "tomli-w"],
        "toml": ["toml"],
        "msgpack": ["msgpack"],
    },
)

if not extra:
    print("WARNING: Cython not installed, could not optimize box.", file=sys.stderr)
