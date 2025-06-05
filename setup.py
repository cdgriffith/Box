#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Minimal setup.py for building Cython extensions with modern build tools.
Most configuration is now in pyproject.toml.
"""

import multiprocessing  # noqa: F401 - Fix for multiprocessing issues on Windows
from pathlib import Path
from setuptools import setup, Extension

try:
    from Cython.Build import cythonize
    USE_CYTHON = True
except ImportError:
    USE_CYTHON = False

# Find all Python files in box/ except __init__.py
root = Path(__file__).parent
box_dir = root / "box"
py_files = [f for f in box_dir.glob("*.py") if f.name != "__init__.py"]

if USE_CYTHON:
    # Convert to Cython extensions
    ext_modules = cythonize(
        [str(f.relative_to(root)) for f in py_files],
        compiler_directives={"language_level": 3},
        build_dir="build"
    )
else:
    # Fall back to pure Python
    ext_modules = []

setup(ext_modules=ext_modules)