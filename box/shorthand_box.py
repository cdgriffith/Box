#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
    def dict(self):
        return self.to_dict()

    @property
    def json(self):
        return self.to_json()

    @property
    def yaml(self):
        return self.to_yaml()

    @property
    def toml(self):
        return self.to_toml()

    def __repr__(self):
        return f"SBox({self})"

    def copy(self):
        return SBox(super(SBox, self).copy())

    def __copy__(self):
        return SBox(super(SBox, self).copy())


class DDBox(SBox):
    def __init__(self, *args, **kwargs):
        kwargs["box_dots"] = True
        kwargs["default_box"] = True
        super().__init__(*args, **kwargs)

    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls, *args, **kwargs)
        obj._box_config["box_dots"] = True
        obj._box_config["default_box"] = True
        return obj

    def __repr__(self):
        return f"DDBox({self})"
