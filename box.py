#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright (c) 2017 - Chris Griffith - MIT License
"""
Improved dictionary management. Inspired by
javascript style referencing, as it's one of the few things they got right.
"""
import string
import sys
import json
from uuid import uuid4
import re

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
    try:
        import ruamel.yaml as yaml
        yaml_support = True
    except ImportError:
        yaml = None

if sys.version_info >= (3, 0):
    basestring = str
else:
    from io import open

__all__ = ['Box', 'ConfigBox', 'LightBox', 'BoxList', 'PropertyBox',
           'BoxError']
__author__ = 'Chris Griffith'
__version__ = '3.0.0'

unallowed_attribs = ('if', 'elif', 'else', 'for', 'from', 'as', 'import',
                     'in', 'not', 'is', 'def', 'class', 'return', 'yield',
                     'except', 'while', 'raise')

box_params = ('default_box', 'default_box_attr', 'conversion_box',
              'frozen_box', 'camel_killer_box')


class BoxError(Exception):
    """ Non standard dictionary exceptions"""


class LightBox(dict):
    """
    LightBox container.
    Allows access to attributes by either class dot notation or item reference.

    All valid:
        - box.spam.eggs
        - box['spam']['eggs']
        - box['spam'].eggs
    """

    _protected_keys = dir({}) + ['to_dict', 'tree_view', 'to_json', 'to_yaml',
                                 'from_yaml', 'from_json']

    def __init__(self, *args, **kwargs):
        if len(args) == 1:
            if isinstance(args[0], basestring):
                raise ValueError('Cannot extrapolate Box from string')
            if isinstance(args[0], Mapping):
                self.__recursive_create(args[0].items())
            elif isinstance(args[0], Iterable):
                self.__recursive_create(args[0])
            else:
                raise ValueError('First argument must be mapping or iterable')
        elif args:
            raise TypeError('Box expected at most 1 argument, '
                            'got {0}'.format(len(args)))
        self.__recursive_create(kwargs.items())

    def __recursive_create(self, iterable):
        for k, v in iterable:
            if isinstance(v, dict):
                v = LightBox(v)
            self[k] = v
            try:
                setattr(self, k, v)
            except TypeError:
                pass

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
        return '<LightBox: {0}>'.format(str(self.to_dict()))

    def __str__(self):
        return str(self.to_dict())

    def __dir__(self):
        allowed = string.ascii_letters + string.digits + '_'

        out = dir(dict) + ['to_dict', 'to_json']
        # Only show items accessible by dot notation
        for key in self.keys():
            if (' ' not in key and
                    key[0] not in string.digits and
                    key not in unallowed_attribs):
                for letter in key:
                    if letter not in allowed:
                        break
                else:
                    out.append(key)

        if yaml_support:
            out.append('to_yaml')
        return out

    def update(self, item=None, **kwargs):
        if not item:
            item = kwargs
        iter_over = item.items() if hasattr(item, 'items') else item
        for k, v in iter_over:
            if isinstance(v, dict):
                v = self.__class__(v)
                if k in self and isinstance(self[k], dict):
                    self[k].update(v)
                    continue
            if (isinstance(v, list) and self.__class__.__name__ not in
                    ('LightBox', 'ConfigBox')):
                v = BoxList(v)
            self.__setattr__(k, v)

    def setdefault(self, item, default=None):
        if item in self:
            return self[item]

        if isinstance(default, dict):
            default = self.__class__(default)
        if (isinstance(default, list) and self.__class__.__name__ not in
                ('LightBox', 'ConfigBox')):
            default = BoxList(default)
        self[item] = default
        return default

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

    def to_json(self, filename=None, indent=4,
                encoding="utf-8", errors="strict", **json_kwargs):
        """
        Transform the Box object into a JSON string.

        :param filename: If provided will save to file
        :param indent: Automatic formatting by indent size in spaces
        :param encoding: File encoding
        :param errors: How to handle encoding errors 
        :param json_kwargs: additional arguments to pass to json.dump(s)
        :return: string of JSON or return of `json.dump`
        """
        json_dump = json.dumps(self.to_dict(), indent=indent,
                               ensure_ascii=False, **json_kwargs)
        if filename:
            with open(filename, 'w', encoding=encoding, errors=errors) as f:
                f.write(json_dump if sys.version_info >= (3, 0) else
                        json_dump.decode("utf-8"))
        else:
            return json_dump

    @classmethod
    def from_json(cls, json_string=None, filename=None,
                  encoding="utf-8", errors="strict", **kwargs):
        """
        Transform a json object string into a Box object. If the incoming
        json is a list, you must use BoxList.from_json. 
        
        You can pass in 
        
        :param json_string: string to pass to `json.loads`
        :param filename: filename to open and pass to `json.load`
        :param encoding: File encoding
        :param errors: How to handle encoding errors 
        :param kwargs: parameters to pass to `Box()` or `json.loads`
        :return: Box object from json data
        """
        bx_args = {}
        for arg in kwargs.copy():
            if arg in box_params:
                bx_args[arg] = kwargs.pop(arg)

        if filename:
            with open(filename, 'r', encoding=encoding, errors=errors) as f:
                data = json.load(f, **kwargs)
        elif json_string:
            data = json.loads(json_string, **kwargs)
        else:
            raise BoxError('from_json requires a string or filename')
        if not isinstance(data, dict):
            raise BoxError('json data not returned as a dictionary, '
                           'but rather a {0}'.format(type(data).__name__))
        return cls(data, **bx_args)

    if yaml_support:
        def to_yaml(self, filename=None, default_flow_style=False,
                    encoding="utf-8", errors="strict",
                    **yaml_kwargs):
            """
            Transform the Box object into a YAML string.

            :param filename:  If provided will save to file
            :param default_flow_style: False will recursively dump dicts
            :param encoding: File encoding
            :param errors: How to handle encoding errors 
            :param yaml_kwargs: additional arguments to pass to yaml.dump
            :return: string of YAML or return of `yaml.dump`
            """
            if filename:
                with open(filename, 'w',
                          encoding=encoding, errors=errors) as f:
                    yaml.dump(self.to_dict(), stream=f,
                              default_flow_style=default_flow_style,
                              **yaml_kwargs)
            else:
                return yaml.dump(self.to_dict(),
                                 default_flow_style=default_flow_style,
                                 **yaml_kwargs)

        @classmethod
        def from_yaml(cls, yaml_string=None, filename=None,
                      encoding="utf-8", errors="strict",
                      **kwargs):
            """
            Transform a yaml object string into a Box object.
    
            :param yaml_string: string to pass to `yaml.load`
            :param filename: filename to open and pass to `yaml.load`
            :param encoding: File encoding
            :param errors: How to handle encoding errors 
            :param kwargs: parameters to pass to `Box()` or `yaml.load`
            :return: Box object from yaml data
            """
            bx_args = {}
            for arg in kwargs.copy():
                if arg in box_params:
                    bx_args[arg] = kwargs.pop(arg)

            if filename:
                with open(filename, 'r',
                          encoding=encoding, errors=errors) as f:
                    data = yaml.load(f, **kwargs)
            elif yaml_string:
                data = yaml.load(yaml_string, **kwargs)
            else:
                raise BoxError('from_yaml requires a string or filename')
            if not isinstance(data, dict):
                raise BoxError('yaml data not returned as a dictionary'
                               'but rather a {0}'.format(type(data).__name__))
            return cls(data, **bx_args)


def _safe_attr(attr, camel_killer=False):
    """Convert a key into something that is accessible as an attribute"""
    allowed = string.ascii_letters + string.digits + '_'

    attr = str(attr)
    if camel_killer:
        attr = _camel_killer(attr)

    attr = attr.casefold() if hasattr(attr, 'casefold') else attr.lower()
    attr = attr.replace(' ', '_')

    out = ''
    for character in attr:
        if character in allowed:
            out += character

    try:
        int(out[0])
    except (ValueError, IndexError):
        pass
    else:
        out = 'x{0}'.format(out)

    if out in unallowed_attribs:
        out = 'x{0}'.format(out)

    return out

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def _camel_killer(attr):
    """
    CamelKiller, qu'est-ce que c'est?
    
    Taken from http://stackoverflow.com/a/1176023/3244542
    """
    s1 = first_cap_re.sub(r'\1_\2', str(attr))
    s2 = all_cap_re.sub(r'\1_\2', s1)
    return s2.casefold() if hasattr(s2, 'casefold') else s2.lower()


def _recursive_tuples(iterable, box_class, recreate_tuples=False, **kwargs):
    out_list = []
    for i in iterable:
        if isinstance(i, dict):
            out_list.append(box_class(i, **kwargs))
        elif isinstance(i, list) or (recreate_tuples and isinstance(i, tuple)):
            out_list.extend(_recursive_tuples(i, box_class,
                                                 recreate_tuples, **kwargs))
    return tuple(out_list)


class Box(LightBox):
    """
    Same as LightBox,
    but also goes into lists and makes dicts within into Boxes.

    The lists are turned into BoxLists
    so that they can also intercept incoming items and turn
    them into Boxes.
    
    :param default_box: Similar to defaultdict, return a default value
    :param default_box_attr: Specify the default replacement. 
        WARNING: If this is not the default 'Box', it will not be recursive
    :param frozen_box: After creation, the box cannot be modified
    :param camel_killer_box: Convert CamelCase to snake_case
    :param conversion_box: Check for near matching keys as attributes
    :param modify_tuples_box: Recreate incoming tuples with dicts into Boxes
    """

    def __init__(self, *args, **kwargs):
        self._box_config = {
            'converted': set(),
            '__box_heritage': kwargs.pop('__box_heritage', None),
            'default_box': kwargs.pop('default_box', False),
            'default_box_attr': kwargs.pop('default_box_attr', self.__class__),
            'conversion_box': kwargs.pop('conversion_box', False),
            'frozen_box': kwargs.pop('frozen_box', False),
            'hash': None,
            'created': False,
            'camel_killer_box': kwargs.pop('camel_killer_box', False),
            'modify_tuples_box': kwargs.pop('modify_tuples_box', False)
            }
        if len(args) == 1:
            if isinstance(args[0], basestring):
                raise ValueError('Cannot extrapolate Box from string')
            if isinstance(args[0], Mapping):
                for k, v in args[0].items():
                    self[k] = v
                    if k == "_box_config":
                        continue
                    try:
                        setattr(self, k, v)
                    except (TypeError, AttributeError):
                        pass
            elif isinstance(args[0], Iterable):
                for k, v in args[0]:
                    self[k] = v
                    if k == "_box_config":
                        continue
                    try:
                        setattr(self, k, v)
                    except (TypeError, AttributeError):
                        pass
            else:
                raise ValueError('First argument must be mapping or iterable')
        elif args:
            raise TypeError('Box expected at most 1 argument, '
                            'got {0}'.format(len(args)))

        box_it = kwargs.pop('box_it_up', False)
        for k, v in kwargs.items():
            self.__setitem__(k, v)

        if self._box_config['frozen_box'] or box_it:
            self.box_it_up()

        self._box_config['created'] = True

    def box_it_up(self):
        for k in self:
            if hasattr(self[k], '_box_it_up'):
                self[k].box_it_up()

    def __hash__(self):
        if self._box_config['frozen_box']:
            if not self._box_config['hash']:
                hashing = hash(uuid4().hex)
                for item in self.items():
                    hashing ^= hash(item)
                self._box_config['hash'] = hashing
            return self._box_config['hash']
        raise TypeError("unhashable type: 'Box'")

    def __dir__(self):
        items = set(super(Box, self).__dir__())
        kill_camel = self._box_config['camel_killer_box']
        for key in self.keys():
            if key not in items:
                if self._box_config['conversion_box']:
                    key = _safe_attr(key, camel_killer=kill_camel)
                    if key:
                        items.add(key)
                elif kill_camel:
                    key = _camel_killer(key)
                    if key:
                        items.add(key)
        return list(items)

    def __getitem__(self, item):
        try:
            value = super(Box, self).__getitem__(item)
        except KeyError:
            try:
                value = object.__getattribute__(self, item)
            except AttributeError as err:
                if item == '_box_config':
                    raise BoxError('_box_config key must exist')
                kill_camel = self._box_config.get('camel_killer_box', False)
                if self._box_config.get('conversion_box', False) and item:
                    for k in self.keys():
                        if item == _safe_attr(k, camel_killer=kill_camel):
                            return self.__getitem__(k)
                if kill_camel:
                    for k in self.keys():
                        if item == _camel_killer(k):
                            return self.__getitem__(k)
                default_value = self._box_config['default_box_attr']
                if self._box_config['default_box']:
                    if isinstance(default_value, type):
                        if default_value.__name__ == 'Box':
                            return self.__class__(__box_heritage=(self, item),
                                                  **self.__box_config())
                        return default_value()
                    elif hasattr(default_value, 'copy'):
                        return default_value.copy()
                    return default_value
                raise err
            else:
                return self.__convert_and_store(item, value)
        else:
            if item == '_box_config':
                return value
            return self.__convert_and_store(item, value)

    def __box_config(self):
        config = self._box_config.copy()
        del config['__box_heritage']
        del config['converted']
        del config['hash']
        del config['created']
        return config

    def __convert_and_store(self, item, value):
        if item in self._box_config['converted']:
            return value
        if isinstance(value, dict) and not isinstance(value, Box):
            value = self.__class__(value, __box_heritage=(self, item),
                                   **self.__box_config())
            self.__setattr__(item, value)
        elif isinstance(value, list):
            if self._box_config['frozen_box']:
                value = _recursive_tuples(value, self.__class__,
                                          recreate_tuples=self._box_config[
                                              'modify_tuples_box'],
                                          __box_heritage=(self, item),
                                          **self.__box_config())
            else:
                value = BoxList(value, __box_heritage=(self, item),
                                box_class=self.__class__,
                                **self.__box_config())

            self.__setattr__(item, value)
        elif (self._box_config['modify_tuples_box'] and
                isinstance(value, tuple)):
            value = _recursive_tuples(value, self.__class__,
                                      recreate_tuples=True,
                                      __box_heritage=(self, item),
                                      **self.__box_config())
            self.__setattr__(item, value)
        self._box_config['converted'].add(item)
        return value

    def __create_lineage(self):
        if self._box_config['__box_heritage']:
            past, item = self._box_config['__box_heritage']
            past[item] = self
            self._box_config['__box_heritage'] = None

    def __getattr__(self, item):
        return self.__getitem__(item)

    def __setitem__(self, key, value):
        if (key != '_box_config' and self._box_config['created'] and
                self._box_config['frozen_box']):
            raise BoxError('Box is frozen')
        super(Box, self).__setitem__(key, value)
        self.__create_lineage()

    def __setattr__(self, key, value):
        if (key != '_box_config' and self._box_config['frozen_box'] and
                self._box_config['created']):
            raise BoxError('Box is frozen')
        if key in self._protected_keys:
            raise AttributeError("Key name '{0}' is protected".format(key))
        if key == '_box_config':
            return object.__setattr__(self, key, value)
        try:
            object.__getattribute__(self, key)
        except AttributeError:
            self[key] = value
        else:
            object.__setattr__(self, key, value)
        self.__create_lineage()

    def __delitem__(self, key):
        if self._box_config['frozen_box']:
            raise BoxError('Box is frozen')
        super(Box, self).__delitem__(key)

    def __delattr__(self, item):
        if self._box_config['frozen_box']:
            raise BoxError('Box is frozen')
        if item == '_box_config':
            raise BoxError('"_box_config" is protected')
        super(Box, self).__delattr__(item)

    def __repr__(self):
        return '<Box: {0}>'.format(str(self.to_dict()))

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

    def __init__(self, iterable=None, box_class=Box, **box_options):
        self.box_class = box_class
        self.box_options = box_options
        if iterable:
            for x in iterable:
                self.append(x)

    def append(self, p_object):
        if isinstance(p_object, dict):
            p_object = self.box_class(p_object, **self.box_options)
        elif isinstance(p_object, list):
            p_object = BoxList(p_object)
        return super(BoxList, self).append(p_object)

    def extend(self, iterable):
        for item in iterable:
            self.append(item)

    def insert(self, index, p_object):
        if isinstance(p_object, dict):
            p_object = self.box_class(p_object, **self.box_options)
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

    def from_json(self):
        pass

    def from_yaml(self):
        pass

    def box_it_up(self):
        for v in self:
            if hasattr(v, '_box_it_up'):
                v.box_it_up()


class ConfigBox(LightBox):
    """
    Modified box object to add object transforms.

    Allows for build in transforms like:

    cns = ConfigBox(my_bool='yes', my_int='5', my_list='5,4,3,3,2')

    cns.bool('my_bool') # True
    cns.int('my_int') # 5
    cns.list('my_list', mod=lambda x: int(x)) # [5, 4, 3, 3, 2]
    """

    _protected_keys = dir({}) + ['to_dict', 'bool', 'int', 'float',
                                 'list', 'getboolean', 'to_json', 'to_yaml',
                                 'getfloat', 'getint']

    def __getattr__(self, item):
        """Config file keys are stored in lower case, be a little more
        loosey goosey"""
        try:
            return super(ConfigBox, self).__getattr__(item)
        except AttributeError:
            return super(ConfigBox, self).__getattr__(item.lower())

    def __dir__(self):
        return super(ConfigBox, self).__dir__() + ['bool', 'int', 'float',
                                                   'list', 'getboolean',
                                                   'getfloat', 'getint']

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
            item = item.lstrip('[').rstrip(']')
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
        return '<ConfigBox: {0}>'.format(str(self.to_dict()))


class PropertyBox(Box):
    """ Access json and yaml as properties """
    _protected_keys = dir({}) + ['to_dict', 'tree_view', 'to_json', 'to_yaml',
                                 'json', 'yaml', 'from_yaml', 'from_json',
                                 'dict']

    @property
    def dict(self):
        return self.to_dict()

    @property
    def json(self):
        return self.to_json()

    if yaml_support:
        @property
        def yaml(self):
            return self.to_yaml()

    def __repr__(self):
        return '<PropertyBox: {0}>'.format(str(self.to_dict()))
