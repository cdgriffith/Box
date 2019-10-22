#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright (c) 2017-2019 - Chris Griffith - MIT License
"""
Improved dictionary access through dot notation with additional tools.
"""
import string
import re
import copy
from keyword import kwlist
import warnings
from collections.abc import Iterable, Mapping, Callable
from typing import Any, Union, Tuple, List

import box
from box.exceptions import BoxError, BoxKeyError, BoxTypeError, BoxValueError
from box.converters import (_to_json, _from_json, _from_toml, _to_toml, _from_yaml, _to_yaml, BOX_PARAMETERS)

__all__ = ['Box']

_first_cap_re = re.compile('(.)([A-Z][a-z]+)')
_all_cap_re = re.compile('([a-z0-9])([A-Z])')
NO_DEFAULT = object()
# a sentinel object for indicating no default, in order to allow users
# to pass `None` as a valid default value


def _safe_attr(attr, camel_killer=False, replacement_char='x'):
    """Convert a key into something that is accessible as an attribute"""
    allowed = string.ascii_letters + string.digits + '_'

    if isinstance(attr, tuple):
        attr = "_".join([str(x) for x in attr])

    attr = attr.decode('utf-8', 'ignore') if isinstance(attr, bytes) else str(attr)

    if camel_killer:
        attr = _camel_killer(attr)

    out = []
    last_safe = 0
    for i, character in enumerate(attr):
        if character in allowed:
            last_safe = i
            out.append(character)
        elif not out:
            continue
        else:
            if last_safe == i - 1:
                out.append('_')

    out = "".join(out)[:last_safe+1]

    try:
        int(out[0])
    except (ValueError, IndexError):
        pass
    else:
        out = f'{replacement_char}{out}'

    if out in kwlist:
        out = f'{replacement_char}{out}'

    return out


def _camel_killer(attr):
    """
    CamelKiller, qu'est-ce que c'est?

    Taken from http://stackoverflow.com/a/1176023/3244542
    """
    attr = str(attr)

    s1 = _first_cap_re.sub(r'\1_\2', attr)
    s2 = _all_cap_re.sub(r'\1_\2', s1)
    return re.sub(' *_+', '_', s2.lower())


def _recursive_tuples(iterable, box_class, recreate_tuples=False, **kwargs):
    out_list = []
    for i in iterable:
        if isinstance(i, dict):
            out_list.append(box_class(i, **kwargs))
        elif isinstance(i, list) or (recreate_tuples and isinstance(i, tuple)):
            out_list.append(_recursive_tuples(i, box_class, recreate_tuples, **kwargs))
        else:
            out_list.append(i)
    return tuple(out_list)


def _conversion_checks(item, keys, box_config, check_only=False, pre_check=False):
    """
    Internal use for checking if a duplicate safe attribute already exists

    :param item: Item to see if a dup exists
    :param keys: Keys to check against
    :param box_config: Easier to pass in than ask for specific items
    :param check_only: Don't bother doing the conversion work
    :param pre_check: Need to add the item to the list of keys to check
    :return: the original unmodified key, if exists and not check_only
    """
    if box_config['box_duplicates'] != 'ignore':
        if pre_check:
            keys = list(keys) + [item]

        key_list = [(k,
                     _safe_attr(k, camel_killer=box_config['camel_killer_box'],
                                replacement_char=box_config['box_safe_prefix']
                                )) for k in keys]
        if len(key_list) > len(set(x[1] for x in key_list)):
            seen, dups = set(), set()
            for x in key_list:
                if x[1] in seen:
                    dups.add(f'{x[0]}({x[1]})')
                seen.add(x[1])
            if box_config['box_duplicates'].startswith('warn'):
                warnings.warn(f'Duplicate conversion attributes exist: {dups}')
            else:
                raise BoxError(f'Duplicate conversion attributes exist: {dups}')
    if check_only:
        return
    # This way will be slower for warnings, as it will have double work
    # But faster for the default 'ignore'
    for k in keys:
        if item == _safe_attr(k, camel_killer=box_config['camel_killer_box'],
                              replacement_char=box_config['box_safe_prefix']):
            return k


def _get_box_config(heritage):
    return {
        # Internal use only
        '__converted': set(),
        '__box_heritage': heritage,
        '__created': False,
    }


class Box(dict):
    """
    Improved dictionary access through dot notation with additional tools.

    :param default_box: Similar to defaultdict, return a default value
    :param default_box_attr: Specify the default replacement.
        WARNING: If this is not the default 'Box', it will not be recursive
    :param default_box_none_transform: When using default_box, treat keys with none values as absent. True by default
    :param frozen_box: After creation, the box cannot be modified
    :param camel_killer_box: Convert CamelCase to snake_case
    :param conversion_box: Check for near matching keys as attributes
    :param modify_tuples_box: Recreate incoming tuples with dicts into Boxes
    :param box_it_up: Recursively create all Boxes from the start
    :param box_safe_prefix: Conversion box prefix for unsafe attributes
    :param box_duplicates: "ignore", "error" or "warn" when duplicates exists in a conversion_box
    :param box_intact_types: tuple of types to ignore converting
    """

    _protected_keys = dir({}) + ['to_dict', 'to_json', 'to_yaml', 'from_yaml', 'from_json', 'from_toml', 'to_toml']

    def __new__(cls, *args: Any, box_it_up: bool = False, default_box: bool = False, default_box_attr: Any = None,
                default_box_none_transform: bool = True, frozen_box: bool = False, camel_killer_box: bool = False,
                conversion_box: bool = True, modify_tuples_box: bool = False, box_safe_prefix: str = 'x',
                box_duplicates: str = 'ignore', box_intact_types: Union[Tuple, List] = (), **kwargs: Any):
        """
        Due to the way pickling works in python 3, we need to make sure
        the box config is created as early as possible.
        """
        obj = super(Box, cls).__new__(cls, *args, **kwargs)
        obj._box_config = _get_box_config(kwargs.pop('__box_heritage', None))
        obj._box_config.update({
            'default_box': default_box,
            'default_box_attr': default_box_attr or cls.__class__,
            'default_box_none_transform': default_box_none_transform,
            'conversion_box': conversion_box,
            'box_safe_prefix': box_safe_prefix,
            'frozen_box': frozen_box,
            'camel_killer_box': camel_killer_box,
            'modify_tuples_box': modify_tuples_box,
            'box_duplicates': box_duplicates,
            'box_intact_types': tuple(box_intact_types)
        })
        return obj

    def __init__(self, *args: Any, box_it_up: bool = False, default_box: bool = False, default_box_attr: Any = None,
                 default_box_none_transform: bool = True, frozen_box: bool = False, camel_killer_box: bool = False,
                 conversion_box: bool = True, modify_tuples_box: bool = False, box_safe_prefix: str = 'x',
                 box_duplicates: str = 'ignore', box_intact_types: Union[Tuple, List] = (), **kwargs: Any):
        super(Box, self).__init__()
        self._box_config = _get_box_config(kwargs.pop('__box_heritage', None))
        self._box_config.update({
            'default_box': default_box,
            'default_box_attr': default_box_attr or self.__class__,
            'default_box_none_transform': default_box_none_transform,
            'conversion_box': conversion_box,
            'box_safe_prefix': box_safe_prefix,
            'frozen_box': frozen_box,
            'camel_killer_box': camel_killer_box,
            'modify_tuples_box': modify_tuples_box,
            'box_duplicates': box_duplicates,
            'box_intact_types': tuple(box_intact_types)
        })
        if not self._box_config['conversion_box'] and self._box_config['box_duplicates'] != 'ignore':
            raise BoxError('box_duplicates are only for conversion_boxes')
        if len(args) == 1:
            if isinstance(args[0], str):
                raise BoxValueError('Cannot extrapolate Box from string')
            if isinstance(args[0], Mapping):
                for k, v in args[0].items():
                    if v is args[0]:
                        v = self
                    if v is None and self._box_config['default_box'] and self._box_config['default_box_none_transform']:
                        continue
                    self[k] = v
            elif isinstance(args[0], Iterable):
                for k, v in args[0]:
                    self[k] = v
            else:
                raise BoxValueError('First argument must be mapping or iterable')
        elif args:
            raise BoxTypeError(f'Box expected at most 1 argument, got {len(args)}')

        for k, v in kwargs.items():
            if args and isinstance(args[0], Mapping) and v is args[0]:
                v = self
            self[k] = v

        if self._box_config['frozen_box'] or box_it_up or self._box_config['box_duplicates'] != 'ignore':
            self.box_it_up()

        self._box_config['__created'] = True

    def box_it_up(self):
        """
        Perform value lookup for all items in current dictionary,
        generating all sub Box objects, while also running `box_it_up` on
        any of those sub box objects.
        """
        for k in self:
            _conversion_checks(k, self.keys(), self._box_config, check_only=True)
            if self[k] is not self and hasattr(self[k], 'box_it_up'):
                self[k].box_it_up()

    def __add__(self, other: dict):
        new_box = self.copy()
        if not isinstance(other, dict):
            raise BoxTypeError(f'Box can only merge two boxes or a box and a dictionary.')
        new_box.merge_update(other)
        return new_box

    def __hash__(self):
        if self._box_config['frozen_box']:
            hashing = 54321
            for item in self.items():
                hashing ^= hash(item)
            return hashing
        raise BoxTypeError('unhashable type: "Box"')

    def __dir__(self):
        allowed = string.ascii_letters + string.digits + '_'
        kill_camel = self._box_config['camel_killer_box']
        items = set(self._protected_keys)
        # Only show items accessible by dot notation
        for key in self.keys():
            key = str(key)
            if ' ' not in key and key[0] not in string.digits and key not in kwlist:
                for letter in key:
                    if letter not in allowed:
                        break
                else:
                    items.add(key)

        for key in self.keys():
            if key not in items:
                if self._box_config['conversion_box']:
                    key = _safe_attr(key, camel_killer=kill_camel, replacement_char=self._box_config['box_safe_prefix'])
                    if key:
                        items.add(key)
            if kill_camel:
                snake_key = _camel_killer(key)
                if snake_key:
                    items.remove(key)
                    items.add(snake_key)

        return list(items)

    def get(self, key, default=NO_DEFAULT):
        if key not in self:
            if (default is NO_DEFAULT and
                    self._box_config['default_box'] and
                    self._box_config['default_box_none_transform']):
                return self.__get_default(key)
            if isinstance(default, dict) and not isinstance(default, Box):
                return Box(default)
            if isinstance(default, list) and not isinstance(default, box.BoxList):
                return box.BoxList(default)
            return default
        return self[key]

    def copy(self):
        return Box(super(Box, self).copy())

    def __copy__(self):
        return Box(super(Box, self).copy())

    def __deepcopy__(self, memodict=None):
        out = self.__class__(**self.__box_config())
        memodict = memodict or {}
        memodict[id(self)] = out
        for k, v in self.items():
            out[copy.deepcopy(k, memodict)] = copy.deepcopy(v, memodict)
        return out

    def __setstate__(self, state):
        self._box_config = state['_box_config']
        self.__dict__.update(state)

    def __getitem__(self, item, _ignore_default=False):
        try:
            value = super(Box, self).__getitem__(item)
        except KeyError as err:
            if item == '_box_config':
                raise BoxKeyError('_box_config should only exist as an attribute and is never defaulted') from None
            if '.' in item:
                first_item, children = item.split('.', 1)
                if first_item in self.keys() and isinstance(self[first_item], dict):
                    return self.__convert_and_store(item, super(Box, self).__getitem__(first_item))[children]

            if self._box_config['default_box'] and not _ignore_default:
                return self.__get_default(item)
            raise BoxKeyError(str(err)) from None
        else:
            return self.__convert_and_store(item, value)

    def keys(self):
        return super(Box, self).keys()

    def values(self):
        return [self[x] for x in self.keys()]

    def items(self):
        return [(x, self[x]) for x in self.keys()]

    def __get_default(self, item):
        default_value = self._box_config['default_box_attr']
        if default_value is self.__class__:
            return self.__class__(__box_heritage=(self, item), **self.__box_config())
        elif isinstance(default_value, Callable):
            return default_value()
        elif hasattr(default_value, 'copy'):
            return default_value.copy()
        return default_value

    def __box_config(self):
        out = {}
        for k, v in self._box_config.copy().items():
            if not k.startswith('__'):
                out[k] = v
        return out

    def __convert_and_store(self, item, value, force_conversion=False):
        # If the value has already been converted or should not be converted, return it as-is
        if ((item in self._box_config['__converted'] and not force_conversion) or
                (self._box_config['box_intact_types'] and isinstance(value, self._box_config['box_intact_types']))):
            return value
        # This is the magic sauce that makes sub dictionaries into new box objects
        if isinstance(value, dict) and not isinstance(value, Box):
            value = self.__class__(value, __box_heritage=(self, item), **self.__box_config())
            self[item] = value
        elif isinstance(value, list) and not isinstance(value, box.BoxList):
            if self._box_config['frozen_box']:
                value = _recursive_tuples(value,
                                          self.__class__,
                                          recreate_tuples=self._box_config['modify_tuples_box'],
                                          __box_heritage=(self, item),
                                          **self.__box_config())
            else:
                value = box.BoxList(value, __box_heritage=(self, item), box_class=self.__class__, **self.__box_config())
            self[item] = value
        elif self._box_config['modify_tuples_box'] and isinstance(value, tuple):
            value = _recursive_tuples(value, self.__class__, recreate_tuples=True, __box_heritage=(self, item),
                                      **self.__box_config())
            self[item] = value
        self._box_config['__converted'].add(item)
        return value

    def __create_lineage(self):
        if self._box_config['__box_heritage'] and self._box_config['__created']:
            past, item = self._box_config['__box_heritage']
            if not past[item]:
                past[item] = self
            self._box_config['__box_heritage'] = None

    def __getattr__(self, item):
        try:
            try:
                value = self.__getitem__(item, _ignore_default=True)
            except KeyError:
                value = object.__getattribute__(self, item)
        except AttributeError as err:
            if item == '__getstate__':
                raise BoxKeyError(item) from None
            if item == '_box_config':
                raise BoxError('_box_config key must exist') from None
            kill_camel = self._box_config['camel_killer_box']
            if self._box_config['conversion_box'] and item:
                k = _conversion_checks(item, self.keys(), self._box_config)
                if k:
                    return self.__getitem__(k)
            if kill_camel:
                for k in self.keys():
                    if item == _camel_killer(k):
                        return self.__getitem__(k)
            if self._box_config['default_box']:
                return self.__get_default(item)
            raise BoxKeyError(str(err)) from None
        else:
            if item == '_box_config':
                return value
            return self.__convert_and_store(item, value)

    def __setitem__(self, key, value):
        if key != '_box_config' and self._box_config['__created'] and self._box_config['frozen_box']:
            raise BoxError('Box is frozen')
        if self._box_config['conversion_box']:
            _conversion_checks(key, self.keys(), self._box_config,
                               check_only=True, pre_check=True)
        super(Box, self).__setitem__(key, value)
        self.__create_lineage()

    def __setattr__(self, key, value):
        if key != '_box_config' and self._box_config['frozen_box'] and self._box_config['__created']:
            raise BoxError('Box is frozen')
        if key in self._protected_keys:
            raise BoxKeyError(f'Key name "{key}" is protected')
        if key == '_box_config':
            return object.__setattr__(self, key, value)
        if key not in self.keys() and (self._box_config['conversion_box'] or self._box_config['camel_killer_box']):
            if self._box_config['conversion_box']:
                k = _conversion_checks(key, self.keys(), self._box_config)
                self[key if not k else k] = value
            elif self._box_config['camel_killer_box']:
                for each_key in self:
                    if key == _camel_killer(each_key):
                        self[each_key] = value
                        break
        else:
            self[key] = value
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
        if item in self._protected_keys:
            raise BoxKeyError(f'Key name "{item}" is protected')
        del self[item]

    def pop(self, key, *args):
        if args:
            if len(args) != 1:
                raise BoxError('pop() takes only one optional'
                               ' argument "default"')
            try:
                item = self[key]
            except KeyError:
                return args[0]
            else:
                del self[key]
                if isinstance(item, Box):
                    item._box_config['__box_heritage'] = ()
                return item
        try:
            item = self[key]
        except KeyError:
            raise BoxKeyError('{0}'.format(key)) from None
        else:
            del self[key]
            if isinstance(item, Box):
                item._box_config['__box_heritage'] = ()
            return item

    def clear(self):
        super(Box, self).clear()

    def popitem(self):
        try:
            key = next(self.__iter__())
        except StopIteration:
            raise BoxKeyError('Empty box') from None
        return key, self.pop(key)

    def __repr__(self):
        return f'<Box: {self.to_dict()}>'

    def __str__(self):
        return str(self.to_dict())

    def __iter__(self):
        for key in self.keys():
            yield key

    def __reversed__(self):
        for key in reversed(list(self.keys())):
            yield key

    def to_dict(self):
        """
        Turn the Box and sub Boxes back into a native
        python dictionary.

        :return: python dictionary of this Box
        """
        out_dict = dict(self)
        for k, v in out_dict.items():
            if v is self:
                out_dict[k] = out_dict
            elif hasattr(v, 'to_dict'):
                out_dict[k] = v.to_dict()
            elif hasattr(v, 'to_list'):
                out_dict[k] = v.to_list()
        return out_dict

    def update(self, __m=None, **kwargs):
        if __m:
            if hasattr(__m, 'keys'):
                for k in __m:
                    self[k] = self.__convert_and_store(k, __m[k], force_conversion=True)
            else:
                for k, v in __m:
                    self[k] = self.__convert_and_store(k, v, force_conversion=True)
        for k in kwargs:
            self[k] = self.__convert_and_store(k, kwargs[k], force_conversion=True)

    def merge_update(self, __m=None, **kwargs):
        def convert_and_set(k, v):
            intact_type = (self._box_config['box_intact_types'] and isinstance(v, self._box_config['box_intact_types']))
            if isinstance(v, dict) and not intact_type:
                # Box objects must be created in case they are already
                # in the `converted` box_config set
                v = self.__class__(v, **self.__box_config())
                if k in self and isinstance(self[k], dict):
                    self[k].update(v)
                    return
            if isinstance(v, list) and not intact_type:
                v = box.BoxList(v, **self.__box_config())
            try:
                self.__setattr__(k, v)
            except (AttributeError, TypeError):
                self.__setitem__(k, v)

        if __m:
            if hasattr(__m, 'keys'):
                for key in __m:
                    convert_and_set(key, __m[key])
            else:
                for key, value in __m:
                    convert_and_set(key, value)
        for key in kwargs:
            convert_and_set(key, kwargs[key])

    def setdefault(self, item, default=None):
        if item in self:
            return self[item]

        if isinstance(default, dict):
            default = self.__class__(default, **self.__box_config())
        if isinstance(default, list):
            default = box.BoxList(default, box_class=self.__class__, **self.__box_config())
        self[item] = default
        return default

    def to_json(self, filename=None, encoding='utf-8', errors='strict', **json_kwargs):
        """
        Transform the Box object into a JSON string.

        :param filename: If provided will save to file
        :param encoding: File encoding
        :param errors: How to handle encoding errors
        :param json_kwargs: additional arguments to pass to json.dump(s)
        :return: string of JSON (if no filename provided)
        """
        return _to_json(self.to_dict(), filename=filename, encoding=encoding, errors=errors, **json_kwargs)

    @classmethod
    def from_json(cls, json_string=None, filename=None, encoding='utf-8', errors='strict', **kwargs):
        """
        Transform a json object string into a Box object. If the incoming
        json is a list, you must use BoxList.from_json.

        :param json_string: string to pass to `json.loads`
        :param filename: filename to open and pass to `json.load`
        :param encoding: File encoding
        :param errors: How to handle encoding errors
        :param kwargs: parameters to pass to `Box()` or `json.loads`
        :return: Box object from json data
        """
        box_args = {}
        for arg in kwargs.copy():
            if arg in BOX_PARAMETERS:
                box_args[arg] = kwargs.pop(arg)

        data = _from_json(json_string, filename=filename, encoding=encoding, errors=errors, **kwargs)

        if not isinstance(data, dict):
            raise BoxError(f'json data not returned as a dictionary, but rather a {type(data).__name__}')
        return cls(data, **box_args)

    def to_yaml(self, filename=None, default_flow_style=False, encoding='utf-8', errors='strict', **yaml_kwargs):
        """
        Transform the Box object into a YAML string.

        :param filename:  If provided will save to file
        :param default_flow_style: False will recursively dump dicts
        :param encoding: File encoding
        :param errors: How to handle encoding errors
        :param yaml_kwargs: additional arguments to pass to yaml.dump
        :return: string of YAML (if no filename provided)
        """
        return _to_yaml(self.to_dict(), filename=filename, default_flow_style=default_flow_style,
                        encoding=encoding, errors=errors, **yaml_kwargs)

    @classmethod
    def from_yaml(cls, yaml_string=None, filename=None, encoding='utf-8', errors='strict', **kwargs):
        """
        Transform a yaml object string into a Box object. By default will use SafeLoader.

        :param yaml_string: string to pass to `yaml.load`
        :param filename: filename to open and pass to `yaml.load`
        :param encoding: File encoding
        :param errors: How to handle encoding errors
        :param kwargs: parameters to pass to `Box()` or `yaml.load`
        :return: Box object from yaml data
        """
        box_args = {}
        for arg in kwargs.copy():
            if arg in BOX_PARAMETERS:
                box_args[arg] = kwargs.pop(arg)

        data = _from_yaml(yaml_string=yaml_string, filename=filename, encoding=encoding, errors=errors, **kwargs)
        if not isinstance(data, dict):
            raise BoxError(f'yaml data not returned as a dictionary but rather a {type(data).__name__}')
        return cls(data, **box_args)

    def to_toml(self, filename: str = None, encoding: str = 'utf-8', errors: str = 'strict'):
        """
        Transform the Box object into a toml string.

        :param filename: File to write toml object too
        :param encoding: File encoding
        :param errors: How to handle encoding errors
        :return: string of TOML (if no filename provided)
        """
        return _to_toml(self.to_dict(), filename=filename, encoding=encoding, errors=errors)

    @classmethod
    def from_toml(cls, toml_string: str = None, filename: str = None,
                  encoding: str = 'utf-8', errors: str = 'strict', **kwargs):
        """
        Transforms a toml string or file into a Box object

        :param toml_string: string to pass to `toml.load`
        :param filename: filename to open and pass to `toml.load`
        :param encoding: File encoding
        :param errors: How to handle encoding errors
        :param kwargs: parameters to pass to `Box()`
        :return:
        """
        box_args = {}
        for arg in kwargs.copy():
            if arg in BOX_PARAMETERS:
                box_args[arg] = kwargs.pop(arg)

        data = _from_toml(toml_string=toml_string, filename=filename, encoding=encoding, errors=errors)
        if not isinstance(data, dict):
            raise BoxError(f'toml data not returned as a dictionary but rather a {type(data).__name__}')
        return cls(data, **box_args)
