#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from distutils.command.build_ext import build_ext

from pathlib import Path

root = os.path.abspath(os.path.dirname(__file__))

try:
    from Cython.Build import cythonize
except ImportError:
    # Got to provide this function. Otherwise, poetry will fail
    def build(setup_kwargs):
        pass


# Cython is installed. Compile
else:
    # This function will be executed in setup.py:
    def build(setup_kwargs):
        # Build
        setup_kwargs.update(
            {
                "ext_modules": cythonize(
                    [
                        str(file.relative_to(root))
                        for file in Path(root, "box").glob("*.py")
                        if file.name != "__init__.py"
                    ],
                    compiler_directives={"language_level": 3},
                ),
            }
        )
