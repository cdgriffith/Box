#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from box.box import Box


class SBox(Box):
    """
    ShorthandBox (SBox) allows for
    property access of `dict` `json` and `yaml`
    """
    _protected_keys = dir({}) + ['to_dict', 'tree_view', 'to_json', 'to_yaml',
                                 'json', 'yaml', 'from_yaml', 'from_json',
                                 'dict']

    @property
    def dict(self):
        return self.to_dict()

    @property
    def json(self):
        return self.to_json()

    @property
    def yaml(self):
        return self.to_yaml()

    def __repr__(self):
        return '<ShorthandBox: {0}>'.format(str(self.to_dict()))
