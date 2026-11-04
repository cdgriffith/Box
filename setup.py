#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
All package metadata lives in pyproject.toml.

This file only exists to optionally compile the library with Cython. If Cython is
installed in the build environment the modules are compiled, otherwise a pure Python
package is built (which is what happens with the default isolated build).
"""

import sys
from pathlib import Path

from setuptools import setup

root = Path(__file__).resolve().parent

try:
    from Cython.Build import cythonize
except ImportError:
    ext_modules = []
    print("WARNING: Cython not installed, could not optimize box.", file=sys.stderr)
else:
    ext_modules = cythonize(
        [str(file.relative_to(root)) for file in (root / "box").glob("*.py") if file.name != "__init__.py"],
        compiler_directives={"language_level": 3},
    )

setup(ext_modules=ext_modules)
