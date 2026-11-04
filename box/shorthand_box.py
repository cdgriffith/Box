#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

from box.box import Box

__all__ = ["SBox", "DDBox"]


class SBox(Box):
    """
    ShorthandBox (SBox) allows for
    property access of `dict` `json` and `yaml`
    """

    _protected_keys = dir({}) + [
        "to_dict",
        "to_json",
        "to_yaml",
        "json",
        "yaml",
        "from_yaml",
        "from_json",
        "dict",
        "toml",
        "from_toml",
        "to_toml",
    ]

    @property
    def dict(self) -> dict:
        return self.to_dict()

    @property
    def json(self) -> str:
        return self.to_json()

    @property
    def yaml(self) -> str:
        return self.to_yaml()

    @property
    def toml(self) -> str:
        return self.to_toml()

    def __repr__(self):
        return f"{self.__class__.__name__}({self})"


class DDBox(SBox):
    """SBox with box_dots and default_box turned on by default"""

    _box_defaults = {"box_dots": True, "default_box": True}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self})"
