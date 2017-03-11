#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright (c) 2017 - Chris Griffith - MIT License
"""
Improved dictionary management. Inspired by
javascript style referencing, as it's one of the few things they got right.
"""
import sys

try:
    from collections.abc import Mapping, Iterable
except ImportError:
    Mapping = dict
    Iterable = (tuple, list)

if sys.version_info >= (3, 0):
    basestring = str

__all__ = ['Box', 'ConfigBox']
__author__ = "Chris Griffith"
__version__ = "1.0.0"


def _recursive_create(self, iterable):
    for k, v in iterable:
        if isinstance(v, dict):
            v = Box(v)
        setattr(self, k, v)


class Box(dict):
    """
    Box container.
    Allows access to attributes by either class dot notation or item reference

    All valid:
        - box.spam.eggs
        - box['spam']['eggs']
        - box['spam'].eggs
    """

    _protected_keys = dir({}) + ['to_dict', 'tree_view']

    def __init__(self, *args, **kwargs):
        if len(args) == 1:
            if isinstance(args[0], basestring):
                raise ValueError("Cannot extrapolate Box from string")
            if isinstance(args[0], Mapping):
                _recursive_create(self, args[0].items())
            elif isinstance(args[0], Iterable):
                _recursive_create(self, args[0])
            else:
                raise ValueError("First argument must be mapping or iterable")
        elif args:
            raise TypeError("Box expected at most 1 argument, "
                            "got {0}".format(len(args)))
        _recursive_create(self, kwargs.items())

    def __contains__(self, item):
        try:
            return dict.__contains__(self, item) or hasattr(self, item)
        except Exception:
            return False

    def __getattr__(self, item):
        try:
            return object.__getattribute__(self, item)
        except AttributeError:
            try:
                return self[item]
            except KeyError:
                raise AttributeError(item)

    def __setattr__(self, key, value):
        if key in self._protected_keys:
            raise AttributeError("Key name '{0}' is protected".format(key))
        if isinstance(value, dict):
            value = self.__class__(**value)
        try:
            object.__getattribute__(self, key)
        except AttributeError:
            try:
                self[key] = value
            except Exception:
                raise AttributeError(key)
        else:
            object.__setattr__(self, key, value)

    def __delattr__(self, item):
        if item in self._protected_keys:
            raise AttributeError("Key name '{0}' is protected".format(item))
        try:
            object.__getattribute__(self, item)
        except AttributeError:
            try:
                del self[item]
            except KeyError:
                raise AttributeError(item)
        else:
            object.__delattr__(self, item)

    def __repr__(self):
        return "<Box: {0}>".format(str(self.to_dict()))

    def __str__(self):
        return str(self.to_dict())

    def __call__(self, *args, **kwargs):
        return tuple(self.values())

    def to_dict(self, in_dict=None):
        """
        Turn the Box and sub Boxs back into a native
        python dictionary.

        :param in_dict: Do not use, for self recursion
        :return: python dictionary of this Box
        """
        in_dict = in_dict if in_dict else self
        out_dict = dict()
        for k, v in in_dict.items():
            if isinstance(v, Box):
                v = v.to_dict()
            out_dict[k] = v
        return out_dict

    def tree_view(self, sep="    "):
        base = self.to_dict()
        return tree_view(base, sep=sep)


def tree_view(dictionary, level=0, sep="|  "):
    """
    View a dictionary as a tree.
    """
    return "".join(["{0}{1}\n{2}".format(sep * level, k,
                   tree_view(v, level + 1, sep=sep) if isinstance(v, dict)
                   else "") for k, v in dictionary.items()])


class ConfigBox(Box):
    """
    Modified box object to add object transforms.

    Allows for build in transforms like:

    cns = ConfigBox(my_bool='yes', my_int='5', my_list='5,4,3,3,2')

    cns.bool('my_bool') # True
    cns.int('my_int') # 5
    cns.list('my_list', mod=lambda x: int(x)) # [5, 4, 3, 3, 2]

    """

    _protected_keys = dir({}) + ['to_dict', 'tree_view',
                                 'bool', 'int', 'float', 'list', 'getboolean',
                                 'getfloat', 'getint']

    def __getattr__(self, item):
        """Config file keys are stored in lower case, be a little more
        loosey goosey"""
        try:
            return super(ConfigBox, self).__getattr__(item)
        except AttributeError:
            return super(ConfigBox, self).__getattr__(item.lower())

    def bool(self, item, default=None):
        """ Return value of key as a boolean

        :param item: key of value to transform
        :param default: value to return if item does not exist
        :return: approximated bool of value
        """
        try:
            item = self.__getattr__(item)
        except AttributeError as err:
            if default is not None:
                return default
            raise err

        if isinstance(item, (bool, int)):
            return bool(item)

        if (isinstance(item, str) and
           item.lower() in ('n', 'no', 'false', 'f', '0')):
            return False

        return True if item else False

    def int(self, item, default=None):
        """ Return value of key as an int

        :param item: key of value to transform
        :param default: value to return if item does not exist
        :return: int of value
        """
        try:
            item = self.__getattr__(item)
        except AttributeError as err:
            if default is not None:
                return default
            raise err
        return int(item)

    def float(self, item, default=None):
        """ Return value of key as a float

        :param item: key of value to transform
        :param default: value to return if item does not exist
        :return: float of value
        """
        try:
            item = self.__getattr__(item)
        except AttributeError as err:
            if default is not None:
                return default
            raise err
        return float(item)

    def list(self, item, default=None, spliter=",", strip=True, mod=None):
        """ Return value of key as a list

        :param item: key of value to transform
        :param mod: function to map against list
        :param default: value to return if item does not exist
        :param spliter: character to split str on
        :param strip: clean the list with the `strip`
        :return: list of items
        """
        try:
            item = self.__getattr__(item)
        except AttributeError as err:
            if default is not None:
                return default
            raise err
        if strip:
            item = item.lstrip("[").rstrip("]")
        out = [x.strip() if strip else x for x in item.split(spliter)]
        if mod:
            return list(map(mod, out))
        return out

    # loose configparser compatibility

    def getboolean(self, item, default=None):
        return self.bool(item, default)

    def getint(self, item, default=None):
        return self.int(item, default)

    def getfloat(self, item, default=None):
        return self.float(item, default)

    def __repr__(self):
        return "<ConfigBox: {0}>".format(str(self.to_dict()))
