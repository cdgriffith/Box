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

import box
from box.exceptions import BoxError, BoxKeyError
from box.converters import (_to_json, _from_json, _from_toml, _to_toml,
                            _from_yaml, _to_yaml, BOX_PARAMETERS)


__all__ = ['Box']


_first_cap_re = re.compile('(.)([A-Z][a-z]+)')
_all_cap_re = re.compile('([a-z0-9])([A-Z])')


# Helper functions


def _safe_key(key):
    try:
        return str(key)
    except UnicodeEncodeError:
        return key.encode("utf-8", "ignore")


def _safe_attr(attr, camel_killer=False, replacement_char='x'):
    """Convert a key into something that is accessible as an attribute"""
    allowed = string.ascii_letters + string.digits + '_'

    attr = _safe_key(attr)

    if camel_killer:
        attr = _camel_killer(attr)

    attr = attr.replace(' ', '_')

    out = ''
    for character in attr:
        out += character if character in allowed else "_"
    out = out.strip("_")

    try:
        int(out[0])
    except (ValueError, IndexError):
        pass
    else:
        out = '{0}{1}'.format(replacement_char, out)

    if out in kwlist:
        out = '{0}{1}'.format(replacement_char, out)

    return re.sub('_+', '_', out)


def _camel_killer(attr):
    """
    CamelKiller, qu'est-ce que c'est?

    Taken from http://stackoverflow.com/a/1176023/3244542
    """
    try:
        attr = str(attr)
    except UnicodeEncodeError:
        attr = attr.encode("utf-8", "ignore")

    s1 = _first_cap_re.sub(r'\1_\2', attr)
    s2 = _all_cap_re.sub(r'\1_\2', s1)
    return re.sub('_+', '_', s2.casefold() if hasattr(s2, 'casefold') else
    s2.lower())


def _recursive_tuples(iterable, box_class, recreate_tuples=False, **kwargs):
    out_list = []
    for i in iterable:
        if isinstance(i, dict):
            out_list.append(box_class(i, **kwargs))
        elif isinstance(i, list) or (recreate_tuples and isinstance(i, tuple)):
            out_list.append(_recursive_tuples(i, box_class,
                                              recreate_tuples, **kwargs))
        else:
            out_list.append(i)
    return tuple(out_list)


def _conversion_checks(item, keys, box_config, check_only=False,
                       pre_check=False):
    """
    Internal use for checking if a duplicate safe attribute already exists

    :param item: Item to see if a dup exists
    :param keys: Keys to check against
    :param box_config: Easier to pass in than ask for specfic items
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
            seen = set()
            dups = set()
            for x in key_list:
                if x[1] in seen:
                    dups.add("{0}({1})".format(x[0], x[1]))
                seen.add(x[1])
            if box_config['box_duplicates'].startswith("warn"):
                warnings.warn('Duplicate conversion attributes exist: '
                              '{0}'.format(dups))
            else:
                raise BoxError('Duplicate conversion attributes exist: '
                               '{0}'.format(dups))
    if check_only:
        return
    # This way will be slower for warnings, as it will have double work
    # But faster for the default 'ignore'
    for k in keys:
        if item == _safe_attr(k, camel_killer=box_config['camel_killer_box'],
                              replacement_char=box_config['box_safe_prefix']):
            return k


def _get_box_config(cls, kwargs):
    return {
        # Internal use only
        '__converted': set(),
        '__box_heritage': kwargs.pop('__box_heritage', None),
        '__created': False,
        '__ordered_box_values': [],
        # Can be changed by user after box creation
        'default_box': kwargs.pop('default_box', False),
        'default_box_attr': kwargs.pop('default_box_attr', cls),
        'conversion_box': kwargs.pop('conversion_box', True),
        'box_safe_prefix': kwargs.pop('box_safe_prefix', 'x'),
        'frozen_box': kwargs.pop('frozen_box', False),
        'camel_killer_box': kwargs.pop('camel_killer_box', False),
        'modify_tuples_box': kwargs.pop('modify_tuples_box', False),
        'box_duplicates': kwargs.pop('box_duplicates', 'ignore'),
        'ordered_box': kwargs.pop('ordered_box', False)
    }


class Box(dict):
    """
    Improved dictionary access through dot notation with additional tools.

    :param default_box: Similar to defaultdict, return a default value
    :param default_box_attr: Specify the default replacement.
        WARNING: If this is not the default 'Box', it will not be recursive
    :param frozen_box: After creation, the box cannot be modified
    :param camel_killer_box: Convert CamelCase to snake_case
    :param conversion_box: Check for near matching keys as attributes
    :param modify_tuples_box: Recreate incoming tuples with dicts into Boxes
    :param box_it_up: Recursively create all Boxes from the start
    :param box_safe_prefix: Conversion box prefix for unsafe attributes
    :param box_duplicates: "ignore", "error" or "warn" when duplicates exists
        in a conversion_box
    :param ordered_box: Preserve the order of keys entered into the box
    """

    _protected_keys = dir({}) + ['to_dict', 'tree_view', 'to_json', 'to_yaml',
                                 'from_yaml', 'from_json']

    def __new__(cls, *args, **kwargs):
        """
        Due to the way pickling works in python 3, we need to make sure
        the box config is created as early as possible.
        """
        obj = super(Box, cls).__new__(cls, *args, **kwargs)
        obj._box_config = _get_box_config(cls, kwargs)
        return obj

    def __init__(self, *args, **kwargs):
        self._box_config = _get_box_config(self.__class__, kwargs)
        if self._box_config['ordered_box']:
            self._box_config['__ordered_box_values'] = []
        if (not self._box_config['conversion_box'] and
                self._box_config['box_duplicates'] != "ignore"):
            raise BoxError('box_duplicates are only for conversion_boxes')
        if len(args) == 1:
            if isinstance(args[0], str):
                raise ValueError('Cannot extrapolate Box from string')
            if isinstance(args[0], Mapping):
                for k, v in args[0].items():
                    if v is args[0]:
                        v = self
                    self[k] = v
                    self.__add_ordered(k)
            elif isinstance(args[0], Iterable):
                for k, v in args[0]:
                    self[k] = v
                    self.__add_ordered(k)

            else:
                raise ValueError('First argument must be mapping or iterable')
        elif args:
            raise TypeError('Box expected at most 1 argument, '
                            'got {0}'.format(len(args)))

        box_it = kwargs.pop('box_it_up', False)
        for k, v in kwargs.items():
            if args and isinstance(args[0], Mapping) and v is args[0]:
                v = self
            self[k] = v
            self.__add_ordered(k)

        if (self._box_config['frozen_box'] or box_it or
                self._box_config['box_duplicates'] != 'ignore'):
            self.box_it_up()

        self._box_config['__created'] = True

    def __add_ordered(self, key):
        if (self._box_config['ordered_box'] and
                key not in self._box_config['__ordered_box_values']):
            self._box_config['__ordered_box_values'].append(key)

    def box_it_up(self):
        """
        Perform value lookup for all items in current dictionary,
        generating all sub Box objects, while also running `box_it_up` on
        any of those sub box objects.
        """
        for k in self:
            _conversion_checks(k, self.keys(), self._box_config,
                               check_only=True)
            if self[k] is not self and hasattr(self[k], 'box_it_up'):
                self[k].box_it_up()

    def __hash__(self):
        if self._box_config['frozen_box']:
            hashing = 54321
            for item in self.items():
                hashing ^= hash(item)
            return hashing
        raise TypeError("unhashable type: 'Box'")

    def __dir__(self):
        allowed = string.ascii_letters + string.digits + '_'
        kill_camel = self._box_config['camel_killer_box']
        items = set(self._protected_keys)
        # Only show items accessible by dot notation
        for key in self.keys():
            key = _safe_key(key)
            if (' ' not in key and key[0] not in string.digits and
                    key not in kwlist):
                for letter in key:
                    if letter not in allowed:
                        break
                else:
                    items.add(key)

        for key in self.keys():
            key = _safe_key(key)
            if key not in items:
                if self._box_config['conversion_box']:
                    key = _safe_attr(key, camel_killer=kill_camel,
                                     replacement_char=self._box_config[
                                         'box_safe_prefix'])
                    if key:
                        items.add(key)
            if kill_camel:
                snake_key = _camel_killer(key)
                if snake_key:
                    items.remove(key)
                    items.add(snake_key)

        return list(items)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            if isinstance(default, dict) and not isinstance(default, Box):
                return Box(default)
            if isinstance(default, list) \
                    and not isinstance(default, box.BoxList):
                return box.BoxList(default)
            return default

    def copy(self):
        return self.__class__(super(self.__class__, self).copy())

    def __copy__(self):
        return self.__class__(super(self.__class__, self).copy())

    def __deepcopy__(self, memodict=None):
        out = self.__class__()
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
                raise BoxKeyError('_box_config should only exist as an '
                                  'attribute and is never defaulted')
            if self._box_config['default_box'] and not _ignore_default:
                return self.__get_default(item)
            raise BoxKeyError(str(err))
        else:
            return self.__convert_and_store(item, value)

    def keys(self):
        if self._box_config['ordered_box']:
            return self._box_config['__ordered_box_values']
        return super(Box, self).keys()

    def values(self):
        return [self[x] for x in self.keys()]

    def items(self):
        return [(x, self[x]) for x in self.keys()]

    def __get_default(self, item):
        default_value = self._box_config['default_box_attr']
        if default_value is self.__class__:
            return self.__class__(__box_heritage=(self, item),
                                  **self.__box_config())
        elif isinstance(default_value, Callable):
            return default_value()
        elif hasattr(default_value, 'copy'):
            return default_value.copy()
        return default_value

    def __box_config(self):
        out = {}
        for k, v in self._box_config.copy().items():
            if not k.startswith("__"):
                out[k] = v
        return out

    def __convert_and_store(self, item, value):
        if item in self._box_config['__converted']:
            return value
        if isinstance(value, dict) and not isinstance(value, Box):
            value = self.__class__(value, __box_heritage=(self, item),
                                   **self.__box_config())
            self[item] = value
        elif isinstance(value, list) \
                and not isinstance(value, box.BoxList):
            if self._box_config['frozen_box']:
                value = _recursive_tuples(value, self.__class__,
                                          recreate_tuples=self._box_config[
                                              'modify_tuples_box'],
                                          __box_heritage=(self, item),
                                          **self.__box_config())
            else:
                value = box.BoxList(value, __box_heritage=(self, item),
                                         box_class=self.__class__,
                                         **self.__box_config())
            self[item] = value
        elif (self._box_config['modify_tuples_box'] and
              isinstance(value, tuple)):
            value = _recursive_tuples(value, self.__class__,
                                      recreate_tuples=True,
                                      __box_heritage=(self, item),
                                      **self.__box_config())
            self[item] = value
        self._box_config['__converted'].add(item)
        return value

    def __create_lineage(self):
        if (self._box_config['__box_heritage'] and
                self._box_config['__created']):
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
            if item == "__getstate__":
                raise AttributeError(item)
            if item == '_box_config':
                raise BoxError('_box_config key must exist')
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
            raise BoxKeyError(str(err))
        else:
            if item == '_box_config':
                return value
            return self.__convert_and_store(item, value)

    def __setitem__(self, key, value):
        if (key != '_box_config' and self._box_config['__created'] and
                self._box_config['frozen_box']):
            raise BoxError('Box is frozen')
        if self._box_config['conversion_box']:
            _conversion_checks(key, self.keys(), self._box_config,
                               check_only=True, pre_check=True)
        super(Box, self).__setitem__(key, value)
        self.__add_ordered(key)
        self.__create_lineage()

    def __setattr__(self, key, value):
        if (key != '_box_config' and self._box_config['frozen_box'] and
                self._box_config['__created']):
            raise BoxError('Box is frozen')
        if key in self._protected_keys:
            raise AttributeError("Key name '{0}' is protected".format(key))
        if key == '_box_config':
            return object.__setattr__(self, key, value)
        try:
            object.__getattribute__(self, key)
        except (AttributeError, UnicodeEncodeError):
            if (key not in self.keys() and
                    (self._box_config['conversion_box'] or
                     self._box_config['camel_killer_box'])):
                if self._box_config['conversion_box']:
                    k = _conversion_checks(key, self.keys(),
                                           self._box_config)
                    self[key if not k else k] = value
                elif self._box_config['camel_killer_box']:
                    for each_key in self:
                        if key == _camel_killer(each_key):
                            self[each_key] = value
                            break
            else:
                self[key] = value
        else:
            object.__setattr__(self, key, value)
        self.__add_ordered(key)
        self.__create_lineage()

    def __delitem__(self, key):
        if self._box_config['frozen_box']:
            raise BoxError('Box is frozen')
        super(Box, self).__delitem__(key)
        if (self._box_config['ordered_box'] and
                key in self._box_config['__ordered_box_values']):
            self._box_config['__ordered_box_values'].remove(key)

    def __delattr__(self, item):
        if self._box_config['frozen_box']:
            raise BoxError('Box is frozen')
        if item == '_box_config':
            raise BoxError('"_box_config" is protected')
        if item in self._protected_keys:
            raise AttributeError("Key name '{0}' is protected".format(item))
        try:
            object.__getattribute__(self, item)
        except AttributeError:
            del self[item]
        else:
            object.__delattr__(self, item)
        if (self._box_config['ordered_box'] and
                item in self._box_config['__ordered_box_values']):
            self._box_config['__ordered_box_values'].remove(item)

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
                return item
        try:
            item = self[key]
        except KeyError:
            raise BoxKeyError('{0}'.format(key))
        else:
            del self[key]
            return item

    def clear(self):
        self._box_config['__ordered_box_values'] = []
        super(Box, self).clear()

    def popitem(self):
        try:
            key = next(self.__iter__())
        except StopIteration:
            raise BoxKeyError('Empty box')
        return key, self.pop(key)

    def __repr__(self):
        return '<Box: {0}>'.format(str(self.to_dict()))

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

    def update(self, item=None, **kwargs):
        if not item:
            item = kwargs
        iter_over = item.items() if hasattr(item, 'items') else item
        for k, v in iter_over:
            if isinstance(v, dict):
                # Box objects must be created in case they are already
                # in the `converted` box_config set
                v = self.__class__(v)
                if k in self and isinstance(self[k], dict):
                    self[k].update(v)
                    continue
            if isinstance(v, list):
                v = box.BoxList(v)
            try:
                self.__setattr__(k, v)
            except (AttributeError, TypeError):
                self.__setitem__(k, v)

    def setdefault(self, item, default=None):
        if item in self:
            return self[item]

        if isinstance(default, dict):
            default = self.__class__(default)
        if isinstance(default, list):
            default = box.BoxList(default)
        self[item] = default
        return default

    def to_json(self, filename=None,
                encoding="utf-8", errors="strict", **json_kwargs):
        """
        Transform the Box object into a JSON string.

        :param filename: If provided will save to file
        :param encoding: File encoding
        :param errors: How to handle encoding errors
        :param json_kwargs: additional arguments to pass to json.dump(s)
        :return: string of JSON or return of `json.dump`
        """
        return _to_json(self.to_dict(), filename=filename,
                        encoding=encoding, errors=errors, **json_kwargs)

    @classmethod
    def from_json(cls, json_string=None, filename=None,
                  encoding="utf-8", errors="strict", **kwargs):
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
        bx_args = {}
        for arg in kwargs.copy():
            if arg in BOX_PARAMETERS:
                bx_args[arg] = kwargs.pop(arg)

        data = _from_json(json_string, filename=filename,
                          encoding=encoding, errors=errors, **kwargs)

        if not isinstance(data, dict):
            raise BoxError('json data not returned as a dictionary, '
                           'but rather a {0}'.format(type(data).__name__))
        return cls(data, **bx_args)

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
        return _to_yaml(self.to_dict(), filename=filename,
                        default_flow_style=default_flow_style,
                        encoding=encoding, errors=errors, **yaml_kwargs)

    @classmethod
    def from_yaml(cls, yaml_string=None, filename=None,
                  encoding="utf-8", errors="strict", **kwargs):
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
            if arg in BOX_PARAMETERS:
                bx_args[arg] = kwargs.pop(arg)

        data = _from_yaml(yaml_string=yaml_string, filename=filename,
                          encoding=encoding, errors=errors, **kwargs)
        if not isinstance(data, dict):
            raise BoxError('yaml data not returned as a dictionary'
                           'but rather a {0}'.format(type(data).__name__))
        return cls(data, **bx_args)
