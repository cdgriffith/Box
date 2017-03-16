#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright (c) 2017 - Chris Griffith - MIT License
"""
Improved dictionary management. Inspired by
javascript style referencing, as it's one of the few things they got right.
"""
import sys
import json

try:
    from collections.abc import Mapping, Iterable
except ImportError:
    Mapping = dict
    Iterable = (tuple, list)

yaml_support = False

try:
    import yaml
    yaml_support = True
except ImportError:
    yaml = None

if sys.version_info >= (3, 0):
    basestring = str

__all__ = ['Box', 'ConfigBox', 'LightBox', 'BoxList']
__author__ = "Chris Griffith"
__version__ = "2.0.0"


class LightBox(dict):
    """
    LightBox container.
    Allows access to attributes by either class dot notation or item reference.

    All valid:
        - box.spam.eggs
        - box['spam']['eggs']
        - box['spam'].eggs
    """

    _protected_keys = dir({}) + ['to_dict', 'tree_view', 'to_json', 'to_yaml']

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
        return dict.__contains__(self, item) or hasattr(self, item)

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            return object.__getattribute__(self, item)

    def __setattr__(self, key, value):
        if key in self._protected_keys:
            raise AttributeError("Key name '{0}' is protected".format(key))
        if isinstance(value, dict):
            value = self.__class__(**value)
        try:
            object.__getattribute__(self, key)
        except AttributeError:
            self[key] = value
        else:
            object.__setattr__(self, key, value)

    def __delattr__(self, item):
        if item in self._protected_keys:
            raise AttributeError("Key name '{0}' is protected".format(item))
        try:
            object.__getattribute__(self, item)
        except AttributeError:
            del self[item]

        else:
            object.__delattr__(self, item)

    def __repr__(self):
        return "<LightBox: {0}>".format(str(self.to_dict()))

    def __str__(self):
        return str(self.to_dict())

    def __call__(self, *args, **kwargs):
        return tuple(sorted(self.keys()))

    def to_dict(self, in_dict=None):
        """
        Turn the Box and sub Boxes back into a native
        python dictionary.

        :param in_dict: Do not use, for self recursion
        :return: python dictionary of this Box
        """
        in_dict = in_dict if in_dict else self
        out_dict = dict()
        for k, v in in_dict.items():
            if isinstance(v, LightBox):
                v = v.to_dict()
            out_dict[k] = v
        return out_dict

    def to_json(self, filename=None, indent=4, **json_kwargs):
        """
        Transform the Box object into a JSON string. 
        
        :param filename: If provided will save to file
        :param indent: Automatic formatting by indent size in spaces
        :param json_kwargs: additional arguments to pass to json.dump(s)
        :return: string of JSON or return of `json.dump`
        """
        if filename:
            with open(filename, 'w') as f:
                return json.dump(self.to_dict(), f, indent=indent,
                                 **json_kwargs)
        else:
            return json.dumps(self.to_dict(), indent=indent, **json_kwargs)

    if yaml_support:
        def to_yaml(self, filename=None, default_flow_style=False,
                    **yaml_kwargs):
            """
            Transform the Box object into a YAML string. 
            
            :param filename:  If provided will save to file
            :param default_flow_style: False will recursively dump dicts
            :param yaml_kwargs: additional arguments to pass to yaml.dump
            :return: string of YAML or return of `yaml.dump`
            """
            if filename:
                with open(filename, 'w') as f:
                    return yaml.dump(self.to_dict(), f,
                                     default_flow_style=default_flow_style,
                                     **yaml_kwargs)
            else:
                return yaml.dump(self.to_dict(),
                                 default_flow_style=default_flow_style,
                                 **yaml_kwargs)


def _recursive_create(self, iterable, include_lists=False, box_class=LightBox):
    for k, v in iterable:
        if isinstance(v, dict):
            v = box_class(v)
        if include_lists and isinstance(v, list):
            v = BoxList(v)
        setattr(self, k, v)


class Box(LightBox):
    """
    Same as LightBox, 
    but also goes into lists and makes dicts within into Boxes.

    The lists are turned into BoxLists
    so that they can also intercept incoming items and turn
    them into Boxes.

    """

    def __init__(self, *args, **kwargs):
        if len(args) == 1:
            if isinstance(args[0], basestring):
                raise ValueError("Cannot extrapolate Box from string")
            if isinstance(args[0], Mapping):
                _recursive_create(self, args[0].items(),
                                  include_lists=True, box_class=Box)
            elif isinstance(args[0], Iterable):
                _recursive_create(self, args[0],
                                  include_lists=True, box_class=Box)
            else:
                raise ValueError("First argument must be mapping or iterable")
        elif args:
            raise TypeError("Box expected at most 1 argument, "
                            "got {0}".format(len(args)))
        _recursive_create(self, kwargs.items(),
                          include_lists=True, box_class=Box)

    def __setattr__(self, key, value):

        if key in self._protected_keys:
            raise AttributeError("Key name '{0}' is protected".format(key))
        if isinstance(value, dict):
            value = self.__class__(**value)
        if isinstance(value, list):
            new_list = BoxList()
            for item in value:
                new_list.append(Box(item) if
                                isinstance(item, dict) else item)
            value = new_list

        try:
            object.__getattribute__(self, key)
        except AttributeError:
            self[key] = value
        else:
            object.__setattr__(self, key, value)

    def __repr__(self):
        return "<Box: {0}>".format(str(self.to_dict()))

    def to_dict(self, in_dict=None):
        """
        Turn the Box and sub Boxes back into a native
        python dictionary.

        :param in_dict: Do not use, for self recursion
        :return: python dictionary of this Box
        """
        in_dict = in_dict if in_dict else self
        out_dict = dict()
        for k, v in in_dict.items():
            if isinstance(v, LightBox):
                v = v.to_dict()
            elif isinstance(v, BoxList):
                v = v.to_list()
            out_dict[k] = v
        return out_dict


class BoxList(list):
    """
    Drop in replacement of list, that converts added objects to Box or BoxList
    objects as necessary. 
    """
    __box_class__ = Box

    def __init__(self, iterable=None):
        if iterable:
            for x in iterable:
                self.append(x)

    def append(self, p_object):
        if isinstance(p_object, dict):
            p_object = self.__box_class__(p_object)
        elif isinstance(p_object, list):
            p_object = BoxList(p_object)
        return super(BoxList, self).append(p_object)

    def extend(self, iterable):
        for item in iterable:
            self.append(item)

    def insert(self, index, p_object):
        if isinstance(p_object, dict):
            p_object = self.__box_class__(p_object)
        elif isinstance(p_object, list):
            p_object = BoxList()
        return super(BoxList, self).insert(index, p_object)

    def __repr__(self):
        return "<BoxList: {0}>".format(self.to_list())

    def __str__(self):
        return str(self.to_list())

    def to_list(self):
        new_list = []
        for x in self:
            if isinstance(x, (Box, LightBox)):
                new_list.append(x.to_dict())
            elif isinstance(x, BoxList):
                new_list.append(x.to_list())
            else:
                new_list.append(x)
        return new_list


class ConfigBox(LightBox):
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
