#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import copy

from box.converters import (_to_yaml, _from_yaml, _to_json, _from_json,
                            BOX_PARAMETERS)
from box.exceptions import  BoxError
import box


class BoxList(list):
    """
    Drop in replacement of list, that converts added objects to Box or BoxList
    objects as necessary.
    """

    def __init__(self, iterable=None, box_class=box.Box, **box_options):
        self.box_class = box_class
        self.box_options = box_options
        self.box_org_ref = self.box_org_ref = id(iterable) if iterable else 0
        if iterable:
            for x in iterable:
                self.append(x)
        if box_options.get('frozen_box'):
            def frozen(*args, **kwargs):
                raise BoxError('BoxList is frozen')

            for method in ['append', 'extend', 'insert', 'pop',
                           'remove', 'reverse', 'sort']:
                self.__setattr__(method, frozen)

    def __delitem__(self, key):
        if self.box_options.get('frozen_box'):
            raise BoxError('BoxList is frozen')
        super(BoxList, self).__delitem__(key)

    def __setitem__(self, key, value):
        if self.box_options.get('frozen_box'):
            raise BoxError('BoxList is frozen')
        super(BoxList, self).__setitem__(key, value)

    def append(self, p_object):
        if isinstance(p_object, dict):
            try:
                p_object = self.box_class(p_object, **self.box_options)
            except AttributeError as err:
                if 'box_class' in self.__dict__:
                    raise err
        elif isinstance(p_object, list):
            try:
                p_object = (self if id(p_object) == self.box_org_ref else
                            BoxList(p_object))
            except AttributeError as err:
                if 'box_org_ref' in self.__dict__:
                    raise err
        super(BoxList, self).append(p_object)

    def extend(self, iterable):
        for item in iterable:
            self.append(item)

    def insert(self, index, p_object):
        if isinstance(p_object, dict):
            p_object = self.box_class(p_object, **self.box_options)
        elif isinstance(p_object, list):
            p_object = (self if id(p_object) == self.box_org_ref else
                        BoxList(p_object))
        super(BoxList, self).insert(index, p_object)

    def __repr__(self):
        return "<BoxList: {0}>".format(self.to_list())

    def __str__(self):
        return str(self.to_list())

    def __copy__(self):
        return BoxList((x for x in self),
                       self.box_class,
                       **self.box_options)

    def __deepcopy__(self, memodict=None):
        out = self.__class__()
        memodict = memodict or {}
        memodict[id(self)] = out
        for k in self:
            out.append(copy.deepcopy(k))
        return out

    def __hash__(self):
        if self.box_options.get('frozen_box'):
            hashing = 98765
            hashing ^= hash(tuple(self))
            return hashing
        raise TypeError("unhashable type: 'BoxList'")

    def to_list(self):
        new_list = []
        for x in self:
            if x is self:
                new_list.append(new_list)
            elif isinstance(x, box.Box):
                new_list.append(x.to_dict())
            elif isinstance(x, BoxList):
                new_list.append(x.to_list())
            else:
                new_list.append(x)
        return new_list

    def to_json(self, filename=None,
                encoding="utf-8", errors="strict",
                multiline=False, **json_kwargs):
        """
        Transform the BoxList object into a JSON string.

        :param filename: If provided will save to file
        :param encoding: File encoding
        :param errors: How to handle encoding errors
        :param multiline: Put each item in list onto it's own line
        :param json_kwargs: additional arguments to pass to json.dump(s)
        :return: string of JSON or return of `json.dump`
        """
        if filename and multiline:
            lines = [_to_json(item, filename=False, encoding=encoding,
                              errors=errors, **json_kwargs) for item in self]
            with open(filename, 'w', encoding=encoding, errors=errors) as f:
                f.write("\n".join(lines))
        else:
            return _to_json(self.to_list(), filename=filename,
                            encoding=encoding, errors=errors, **json_kwargs)

    @classmethod
    def from_json(cls, json_string=None, filename=None, encoding="utf-8",
                  errors="strict", multiline=False, **kwargs):
        """
        Transform a json object string into a BoxList object. If the incoming
        json is a dict, you must use Box.from_json.

        :param json_string: string to pass to `json.loads`
        :param filename: filename to open and pass to `json.load`
        :param encoding: File encoding
        :param errors: How to handle encoding errors
        :param multiline: One object per line
        :param kwargs: parameters to pass to `Box()` or `json.loads`
        :return: BoxList object from json data
        """
        bx_args = {}
        for arg in list(kwargs.keys()):
            if arg in BOX_PARAMETERS:
                bx_args[arg] = kwargs.pop(arg)

        data = _from_json(json_string, filename=filename, encoding=encoding,
                          errors=errors, multiline=multiline, **kwargs)

        if not isinstance(data, list):
            raise BoxError('json data not returned as a list, '
                           'but rather a {0}'.format(type(data).__name__))
        return cls(data, **bx_args)

    def to_yaml(self, filename=None, default_flow_style=False,
                encoding="utf-8", errors="strict",
                **yaml_kwargs):
        """
        Transform the BoxList object into a YAML string.

        :param filename:  If provided will save to file
        :param default_flow_style: False will recursively dump dicts
        :param encoding: File encoding
        :param errors: How to handle encoding errors
        :param yaml_kwargs: additional arguments to pass to yaml.dump
        :return: string of YAML or return of `yaml.dump`
        """
        return _to_yaml(self.to_list(), filename=filename,
                        default_flow_style=default_flow_style,
                        encoding=encoding, errors=errors, **yaml_kwargs)

    @classmethod
    def from_yaml(cls, yaml_string=None, filename=None,
                  encoding="utf-8", errors="strict",
                  **kwargs):
        """
        Transform a yaml object string into a BoxList object.

        :param yaml_string: string to pass to `yaml.load`
        :param filename: filename to open and pass to `yaml.load`
        :param encoding: File encoding
        :param errors: How to handle encoding errors
        :param kwargs: parameters to pass to `BoxList()` or `yaml.load`
        :return: BoxList object from yaml data
        """
        bx_args = {}
        for arg in list(kwargs.keys()):
            if arg in BOX_PARAMETERS:
                bx_args[arg] = kwargs.pop(arg)

        data = _from_yaml(yaml_string=yaml_string, filename=filename,
                          encoding=encoding, errors=errors, **kwargs)
        if not isinstance(data, list):
            raise BoxError('yaml data not returned as a list'
                           'but rather a {0}'.format(type(data).__name__))
        return cls(data, **bx_args)

    def box_it_up(self):
        for v in self:
            if hasattr(v, 'box_it_up') and v is not self:
                v.box_it_up()


