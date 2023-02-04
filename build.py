#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from setuptools.command.build_ext import build_ext

from pathlib import Path
import shutil

root = Path(__file__).parent


def copy_files():
    # Why does poetry put include files at the root of site-packages? So bad! Copy them inside the package
    shutil.copy(root / "AUTHORS.rst", root / "box" / "AUTHORS.rst")
    shutil.copy(root / "CHANGES.rst", root / "box" / "CHANGES.rst")
    shutil.copy(root / "LICENSE", root / "box" / "LICENSE")
    shutil.copy(root / "box_logo.png", root / "box" / "box_logo.png")


try:
    from Cython.Build import cythonize
except ImportError:
    # Got to provide this function. Otherwise, poetry will fail
    def build(setup_kwargs):
        copy_files()


# Cython is installed. Compile
else:
    # This function will be executed in setup.py:
    def build(setup_kwargs):
        copy_files()
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
