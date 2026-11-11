#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2017-2026 - Chris Griffith - MIT License
from __future__ import annotations

import copy
import copyreg
import operator
import re
from collections.abc import Iterable
from os import PathLike
from typing import Any

import box
from box import comments as _comments
from box.converters import (
    BOX_PARAMETERS,
    _from_csv,
    _from_json,
    _from_msgpack,
    _from_toml,
    _from_toon,
    _from_yaml_with_comments,
    _to_csv,
    _to_json,
    _to_msgpack,
    _to_toml,
    _to_toon,
    msgpack_available,
    toml_read_library,
    toon_available,
    yaml_available,
)
from box.exceptions import BoxError, BoxKeyError, BoxTypeError

_list_pos_re = re.compile(r"\[(\d+)\]")
_comment_index_re = re.compile(r"\[(-?\d+)\]")  # the comment API also takes negative indexes


def _frozen_box_list_method(*args, **kwargs):
    raise BoxError("BoxList is frozen")


class BoxList(list):
    """
    Drop in replacement of list, that converts added objects to Box or BoxList
    objects as necessary.
    """

    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls, *args, **kwargs)
        # This is required for pickling to work correctly
        obj.box_options = {"box_class": box.Box}
        obj.box_options.update(kwargs)
        obj.box_org_ref = None
        return obj

    def __init__(self, iterable: Iterable | None = None, box_class: type[box.Box] = box.Box, **box_options):
        self.box_options = box_options
        self.box_options["box_class"] = box_class
        self.box_org_ref = iterable
        # 2026-10-10: Iteration does not require a truth value.
        if iterable is not None:
            for x in iterable:
                self.append(x)
            if isinstance(iterable, BoxList) and iterable is not self:
                iterable._comment_copy_to(self)
        self.box_org_ref = None
        if box_options.get("frozen_box"):
            for method in ["append", "clear", "extend", "insert", "pop", "remove", "reverse", "sort"]:
                self.__setattr__(method, _frozen_box_list_method)

    def __getitem__(self, item, _ignore_default=False):
        if self.box_options.get("box_dots") and isinstance(item, str) and item.startswith("["):
            list_pos = _list_pos_re.search(item)
            if list_pos is None:
                raise BoxTypeError(f"Invalid list index: {item!r}")
            value = super().__getitem__(int(list_pos.groups()[0]))
            if len(list_pos.group()) == len(item):
                return value
            children = item[len(list_pos.group()) :].lstrip(".")
            if _ignore_default and isinstance(value, (box.Box, BoxList)):
                return value.__getitem__(children, _ignore_default=True)
            return value.__getitem__(children)
        if isinstance(item, tuple):
            result = self
            for idx in item:
                if isinstance(result, list):
                    result = result[idx]
                else:
                    raise BoxTypeError(f"Cannot numpy-style indexing on {type(result).__name__}.")
            return result
        return super().__getitem__(item)

    def __delitem__(self, key):
        if self.box_options.get("frozen_box"):
            raise BoxError("BoxList is frozen")
        if self.box_options.get("box_dots") and isinstance(key, str) and key.startswith("["):
            list_pos = _list_pos_re.search(key)
            if list_pos is None:
                raise BoxTypeError(f"Invalid list index: {key!r}")
            pos = int(list_pos.groups()[0])
            if len(list_pos.group()) == len(key):
                return self.__delitem__(pos)
            if hasattr(self[pos], "__delitem__"):
                return self[pos].__delitem__(key[len(list_pos.group()) :].lstrip("."))  # type: ignore
        if not isinstance(key, slice) and hasattr(type(key), "__index__"):
            key = operator.index(key)
        length = len(self)
        super().__delitem__(key)
        self._comment_after_delete(key, length)

    def __setitem__(self, key, value):
        if self.box_options.get("frozen_box"):
            raise BoxError("BoxList is frozen")
        if self.box_options.get("box_dots") and isinstance(key, str) and key.startswith("["):
            list_pos = _list_pos_re.search(key)
            if list_pos is None:
                raise BoxTypeError(f"Invalid list index: {key!r}")
            pos = int(list_pos.groups()[0])
            if pos >= len(self) and self.box_options.get("default_box"):
                self.extend([None] * (pos - len(self) + 1))
            if len(list_pos.group()) == len(key):
                return super().__setitem__(pos, self._convert(value))
            children = key[len(list_pos.group()) :].lstrip(".")
            if self.box_options.get("default_box"):
                # Only replace the element at ``pos`` with a fresh container when it is
                # not already the right one; otherwise a second dotted write into an
                # existing element (e.g. ``a[0].y`` after ``a[0].x``) would discard the
                # data already stored there. Mirrors the guard in Box.__setitem__.
                current = super().__getitem__(pos)
                if children.startswith("["):
                    if not isinstance(current, box.BoxList):
                        super().__setitem__(pos, box.BoxList(**self.box_options))
                elif not isinstance(current, box.Box):
                    super().__setitem__(pos, self.box_options.get("box_class")(**self.box_options))
            return super().__getitem__(pos).__setitem__(children, value)
        if isinstance(key, slice):

            def converted_items():
                for item in value:
                    yield self._convert(item)

            # Let list validate the slice before consuming replacement values.
            super().__setitem__(key, converted_items())
            self.__dict__.pop("_box_comments", None)  # items moved, their comments can't follow
            return
        super().__setitem__(key, self._convert(value))

    def __add__(self, other):
        if not isinstance(other, list):
            raise BoxTypeError("BoxList can only be added to another list.")
        return box.BoxList(list(self) + list(other), **self.box_options)

    def __mul__(self, count):
        try:
            count = operator.index(count)
        except TypeError:
            raise BoxTypeError("BoxList can only be multiplied by an integer.") from None
        return box.BoxList(list(self) * count, **self.box_options)

    __rmul__ = __mul__

    def __iadd__(self, value):  # type: ignore[misc]  # list accepts any iterable for +=, not only lists
        if self.box_options.get("frozen_box"):
            raise BoxError("BoxList is frozen")
        self.extend(value)
        return self

    def __imul__(self, value):  # type: ignore[misc]
        if self.box_options.get("frozen_box"):
            raise BoxError("BoxList is frozen")
        result = super().__imul__(value)
        if len(self) == 0:
            self.__dict__.pop("_box_comments", None)
        return result

    def _is_intact_type(self, obj):
        if self.box_options.get("box_intact_types") and isinstance(obj, self.box_options["box_intact_types"]):
            return True
        return False

    def _convert(self, p_object):
        if isinstance(p_object, dict) and not self._is_intact_type(p_object):
            p_object = self.box_options["box_class"](p_object, **self.box_options)
        elif isinstance(p_object, box.Box):
            p_object._box_config.update(self.box_options)
        if isinstance(p_object, list) and not self._is_intact_type(p_object):
            p_object = (
                self
                if p_object is self or p_object is self.box_org_ref
                else self.__class__(p_object, **self.box_options)
            )
        elif isinstance(p_object, BoxList):
            p_object.box_options.update(self.box_options)
        return p_object

    def append(self, p_object):
        super().append(self._convert(p_object))

    def extend(self, iterable):
        if iterable is self:
            iterable = list(self)
        for item in iterable:
            self.append(item)

    def insert(self, index, p_object):
        index = operator.index(index)
        length = len(self)
        super().insert(index, self._convert(p_object))
        if self.__dict__.get("_box_comments"):
            at = min(max(index + length, 0) if index < 0 else index, length)
            self._comment_reindex(lambda k: k + 1 if k >= at else k)

    def pop(self, index=-1):
        index = operator.index(index)
        length = len(self)
        value = super().pop(index)
        self._comment_after_delete(index, length)
        return value

    def remove(self, value):
        self.pop(self.index(value))

    def clear(self):
        super().clear()
        self.__dict__.pop("_box_comments", None)

    def reverse(self):
        super().reverse()
        last = len(self) - 1
        self._comment_reindex(lambda k: last - k)

    def sort(self, *, key=None, reverse=False):
        if not self.__dict__.get("_box_comments"):
            return super().sort(key=key, reverse=reverse)
        # Work out where every item goes (same stable order as list.sort) so comments follow them
        sort_key = (lambda x: x) if key is None else key
        order = sorted(range(len(self)), key=lambda i: sort_key(list.__getitem__(self, i)), reverse=reverse)
        new_position = {old: new for new, old in enumerate(order)}
        super().__setitem__(slice(None), [list.__getitem__(self, i) for i in order])
        self._comment_reindex(new_position.get)

    # ---- Comments (#184), by item index ----

    def _comment_store(self, create: bool = True) -> Any:
        store = self.__dict__.get("_box_comments")
        if store is None and create:
            store = self.__dict__["_box_comments"] = {}
        return store

    def _comment_document(self, create: bool = True) -> Any:
        document = self.__dict__.get("_box_comments_document")
        if document is None and create:
            document = self.__dict__["_box_comments_document"] = {}
        return document

    def _comment_check_frozen(self):
        if self.box_options.get("frozen_box"):
            raise BoxError("BoxList is frozen")

    def _comment_reindex(self, mapping):
        store = self.__dict__.get("_box_comments")
        if store:
            moved = {}
            for index, comment in store.items():
                new_index = mapping(index)
                if new_index is not None:
                    moved[new_index] = comment
            self.__dict__["_box_comments"] = moved

    def _comment_after_delete(self, key, length):
        if not self.__dict__.get("_box_comments"):
            return
        if isinstance(key, slice):
            self.__dict__.pop("_box_comments", None)
            return
        gone = key + length if key < 0 else key
        self._comment_reindex(lambda k: None if k == gone else (k - 1 if k > gone else k))

    def _comment_owner(self, key):
        """(container, index) that holds the comment for `key`, following box_dots paths."""
        if key is None:
            return self, None
        if isinstance(key, int) and not isinstance(key, bool):
            index = key + len(self) if key < 0 else key
            if 0 <= index < len(self):
                return self, index
        elif isinstance(key, str) and key.startswith("["):
            list_pos = _comment_index_re.match(key)
            if list_pos is not None:
                index = int(list_pos.groups()[0])
                index = index + len(self) if index < 0 else index
                rest = key[len(list_pos.group()) :].lstrip(".")
                if 0 <= index < len(self):
                    if not rest:
                        return self, index
                    child = list.__getitem__(self, index)
                    if hasattr(child, "_comment_owner"):
                        return child._comment_owner(rest)
        raise BoxKeyError(f"{key!r} is not in the BoxList, comments can only be attached to existing items")

    def _comment_copy_to(self, other):
        store = self.__dict__.get("_box_comments")
        if store:
            other._comment_store().update({k: copy.deepcopy(v) for k, v in store.items() if k < len(other)})
        document = self.__dict__.get("_box_comments_document")
        if document:
            other._comment_document().update(copy.deepcopy(document))

    # ---- Comments (#184): kept outside the data, written by to_yaml with ruamel.yaml ----

    def get_comment(self, key: Any = None) -> dict | None:
        """
        Return the comments of `key` as ``{"before": text, "eol": text}`` (a position without a comment
        is left out), or None. ``key=None`` returns the document comments ``{"start": ..., "end": ...}``.
        With box_dots, `key` can be a dotted path.
        """
        return _comments.get_comment(self, key)

    def set_comment(self, key: Any, text: Any, position: str | None = None) -> None:
        """
        Attach a comment to an existing key. `position` is "eol" (default, on the key's line) or
        "before" (lines above the key, may contain newlines). ``key=None`` sets a document comment,
        position "start" (default) or "end". An empty `text` removes the comment at that position.
        """
        _comments.set_comment(self, key, text, position)

    def del_comment(self, key: Any = None) -> None:
        """Remove every comment of `key` (``None``: the document comments)."""
        _comments.del_comment(self, key)

    def _dotted_helper(self) -> list[str]:
        keys = []
        for idx, item in enumerate(self):
            added = False
            if isinstance(item, box.Box):
                for key in item.keys(dotted=True):
                    keys.append(f"[{idx}].{key}")
                    added = True
            elif isinstance(item, BoxList):
                for key in item._dotted_helper():
                    keys.append(f"[{idx}]{key}")
                    added = True
            if not added:
                keys.append(f"[{idx}]")
        return keys

    def __repr__(self):
        return f"{self.__class__.__name__}({self.to_list()})"

    def __str__(self):
        return str(self.to_list())

    def __copy__(self):
        out = self.__class__((x for x in self), **self.box_options)
        self._comment_copy_to(out)
        return out

    def __deepcopy__(self, memo=None):
        out = self.__class__(**{**self.box_options, "frozen_box": False})
        memo = memo or {}
        memo[id(self)] = out
        items = [copy.deepcopy(k, memo=memo) for k in self]
        # Filling through __init__ applies the options (frozen included) to the copied items
        out.__init__(items, **self.box_options)
        self._comment_copy_to(out)
        return out

    def __reduce_ex__(self, protocol):
        # The default list pickling appends the items before restoring box_options, which
        # re-created every item with default options. Keep the items in the state instead,
        # so __setstate__ restores the options first. Self references still work because
        # pickle memoizes the new list before the state is saved.
        state = {"box_options": self.box_options, "items": list(self)}
        for name in ("_box_comments", "_box_comments_document"):
            if self.__dict__.get(name):
                state[name] = self.__dict__[name]
        return copyreg.__newobj__, (self.__class__,), state

    def __setstate__(self, state):
        if "items" not in state:
            # Pickled by Box 7 or earlier: the items were already appended
            self.__dict__.update(state)
            return
        self.__init__(state["items"], **state["box_options"])
        for name in ("_box_comments", "_box_comments_document"):
            if name in state:
                self.__dict__[name] = state[name]

    def __hash__(self) -> int:  # type: ignore[override]
        if self.box_options.get("frozen_box"):
            hashing = 98765
            hashing ^= hash(tuple(self))
            return hashing
        raise BoxTypeError("unhashable type: 'BoxList'")

    def to_list(self) -> list:
        new_list: list[Any] = []
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

    def to_json(
        self,
        filename: str | PathLike | None = None,
        encoding: str = "utf-8",
        errors: str = "strict",
        multiline: bool = False,
        **json_kwargs,
    ):
        """
        Transform the BoxList object into a JSON string.

        :param filename: If provided will save to file
        :param encoding: File encoding
        :param errors: How to handle encoding errors
        :param multiline: Put each item in list onto its own line, in a string or file
        :param json_kwargs: additional arguments to pass to json.dump(s)
        :return: string of JSON or return of `json.dump`
        """
        if multiline:
            lines = [_to_json(item, filename=None, encoding=encoding, errors=errors, **json_kwargs) for item in self]
            text = "\n".join(lines)
            if filename:
                with open(filename, "w", encoding=encoding, errors=errors) as f:
                    f.write(text)
            else:
                return text
        else:
            return _to_json(self.to_list(), filename=filename, encoding=encoding, errors=errors, **json_kwargs)

    @classmethod
    def from_json(
        cls,
        json_string: str | None = None,
        filename: str | PathLike | None = None,
        encoding: str = "utf-8",
        errors: str = "strict",
        multiline: bool = False,
        **kwargs,
    ):
        """
        Transform a json object string into a BoxList object. If the incoming
        json is a dict, you must use Box.from_json.

        :param json_string: string to pass to `json.loads`
        :param filename: filename to open and pass to `json.load`
        :param encoding: File encoding
        :param errors: How to handle encoding errors
        :param multiline: One object per line, in a string or file
        :param kwargs: parameters to pass to `Box()` or `json.loads`
        :return: BoxList object from json data
        """
        box_args = {}
        for arg in list(kwargs.keys()):
            if arg in BOX_PARAMETERS:
                box_args[arg] = kwargs.pop(arg)

        data = _from_json(
            json_string, filename=filename, encoding=encoding, errors=errors, multiline=multiline, **kwargs
        )

        if not isinstance(data, list):
            raise BoxError(f"json data not returned as a list, but rather a {type(data).__name__}")
        return cls(data, **box_args)

    if yaml_available:

        def to_yaml(
            self,
            filename: str | PathLike | None = None,
            default_flow_style: bool = False,
            encoding: str = "utf-8",
            errors: str = "strict",
            width: int = 120,
            **yaml_kwargs,
        ):
            """
            Transform the BoxList object into a YAML string.

            :param filename:  If provided will save to file
            :param default_flow_style: False will recursively dump dicts
            :param encoding: File encoding
            :param errors: How to handle encoding errors
            :param width: Line width for YAML output
            :param sort_keys: True sorts keys alphabetically, the default False keeps insertion order
            :param yaml_kwargs: additional arguments to pass to yaml.dump
            :return: string of YAML or return of `yaml.dump`
            """
            return _comments.dump_yaml(
                self,
                self.to_list(),
                filename=filename,
                default_flow_style=default_flow_style,
                encoding=encoding,
                errors=errors,
                width=width,
                **yaml_kwargs,
            )

        @classmethod
        def from_yaml(
            cls,
            yaml_string: str | None = None,
            filename: str | PathLike | None = None,
            encoding: str = "utf-8",
            errors: str = "strict",
            **kwargs,
        ):
            """
            Transform a yaml object string into a BoxList object.

            :param yaml_string: string to pass to `yaml.load`
            :param filename: filename to open and pass to `yaml.load`
            :param encoding: File encoding
            :param errors: How to handle encoding errors
            :param kwargs: parameters to pass to `BoxList()` or `yaml.load`
            :return: BoxList object from yaml data
            """
            box_args = {}
            for arg in list(kwargs.keys()):
                if arg in BOX_PARAMETERS:
                    box_args[arg] = kwargs.pop(arg)

            data, comments = _from_yaml_with_comments(
                yaml_string=yaml_string, filename=filename, encoding=encoding, errors=errors, **kwargs
            )
            if not data:
                result = cls(**box_args)
            elif not isinstance(data, list):
                raise BoxError(f"yaml data not returned as a list but rather a {type(data).__name__}")
            else:
                result = cls(data, **box_args)
            _comments.apply_comments(result, comments)
            return result

    else:

        def to_yaml(
            self,
            filename: str | PathLike | None = None,
            default_flow_style: bool = False,
            encoding: str = "utf-8",
            errors: str = "strict",
            width: int = 120,
            **yaml_kwargs,
        ):
            raise BoxError('yaml is unavailable on this system, please install the "ruamel.yaml" or "PyYAML" package')

        @classmethod
        def from_yaml(
            cls,
            yaml_string: str | None = None,
            filename: str | PathLike | None = None,
            encoding: str = "utf-8",
            errors: str = "strict",
            **kwargs,
        ):
            raise BoxError('yaml is unavailable on this system, please install the "ruamel.yaml" or "PyYAML" package')

    if toml_read_library is not None:

        def to_toml(
            self,
            filename: str | PathLike | None = None,
            key_name: str = "toml",
            encoding: str = "utf-8",
            errors: str = "strict",
        ):
            """
            Transform the BoxList object into a toml string.

            :param filename: File to write toml object too
            :param key_name: Specify the name of the key to store the string under
                (cannot directly convert to toml)
            :param encoding: File encoding
            :param errors: How to handle encoding errors
            :return: string of TOML (if no filename provided)
            """
            return _to_toml({key_name: self.to_list()}, filename=filename, encoding=encoding, errors=errors)

    else:

        def to_toml(
            self,
            filename: str | PathLike | None = None,
            key_name: str = "toml",
            encoding: str = "utf-8",
            errors: str = "strict",
        ):
            raise BoxError('toml is unavailable on this system, please install the "tomli-w" package')

    if toml_read_library is not None:

        @classmethod
        def from_toml(
            cls,
            toml_string: str | None = None,
            filename: str | PathLike | None = None,
            key_name: str = "toml",
            encoding: str = "utf-8",
            errors: str = "strict",
            **kwargs,
        ):
            """
            Transforms a toml string or file into a BoxList object

            :param toml_string: string to pass to `toml.load`
            :param filename: filename to open and pass to `toml.load`
            :param key_name: Specify the name of the key to pull the list from
                (cannot directly convert from toml)
            :param encoding: File encoding
            :param errors: How to handle encoding errors
            :param kwargs: parameters to pass to `Box()`
            :return:
            """
            box_args = {}
            for arg in list(kwargs.keys()):
                if arg in BOX_PARAMETERS:
                    box_args[arg] = kwargs.pop(arg)

            data = _from_toml(toml_string=toml_string, filename=filename, encoding=encoding, errors=errors)
            if key_name not in data:
                raise BoxError(f"{key_name} was not found.")
            return cls(data[key_name], **box_args)

    else:

        @classmethod
        def from_toml(
            cls,
            toml_string: str | None = None,
            filename: str | PathLike | None = None,
            key_name: str = "toml",
            encoding: str = "utf-8",
            errors: str = "strict",
            **kwargs,
        ):
            raise BoxError('toml is unavailable on this system, please install the "toml" package')

    if msgpack_available:

        def to_msgpack(self, filename: str | PathLike | None = None, **kwargs):
            """
            Transform the BoxList object into a toml string.

            :param filename: File to write toml object too
            :return: string of TOML (if no filename provided)
            """
            return _to_msgpack(self.to_list(), filename=filename, **kwargs)

        @classmethod
        def from_msgpack(cls, msgpack_bytes: bytes | None = None, filename: str | PathLike | None = None, **kwargs):
            """
            Transforms a toml string or file into a BoxList object

            :param msgpack_bytes: string to pass to `msgpack.packb`
            :param filename: filename to open and pass to `msgpack.pack`
            :param kwargs: parameters to pass to `Box()`
            :return:
            """
            box_args = {}
            for arg in list(kwargs.keys()):
                if arg in BOX_PARAMETERS:
                    box_args[arg] = kwargs.pop(arg)

            data = _from_msgpack(msgpack_bytes=msgpack_bytes, filename=filename, **kwargs)
            if not isinstance(data, list):
                raise BoxError(f"msgpack data not returned as a list but rather a {type(data).__name__}")
            return cls(data, **box_args)

    else:

        def to_msgpack(self, filename: str | PathLike | None = None, **kwargs):
            raise BoxError('msgpack is unavailable on this system, please install the "msgpack" package')

        @classmethod
        def from_msgpack(
            cls,
            msgpack_bytes: bytes | None = None,
            filename: str | PathLike | None = None,
            encoding: str = "utf-8",
            errors: str = "strict",
            **kwargs,
        ):
            raise BoxError('msgpack is unavailable on this system, please install the "msgpack" package')

    if toon_available:

        def to_toon(
            self, filename: str | PathLike | None = None, encoding: str = "utf-8", errors: str = "strict", **kwargs
        ):
            """
            Transform the BoxList object into a TOON string.

            :param filename: File to write TOON object too
            :param encoding: File encoding
            :param errors: How to handle encoding errors
            :param kwargs: parameters to pass to `toon_format.encode`
            :return: string of TOON (if no filename provided)
            """
            return _to_toon(self.to_list(), filename=filename, encoding=encoding, errors=errors, **kwargs)

        @classmethod
        def from_toon(
            cls,
            toon_string: str | None = None,
            filename: str | PathLike | None = None,
            encoding: str = "utf-8",
            errors: str = "strict",
            **kwargs,
        ):
            """
            Transforms a TOON string or file into a BoxList object

            :param toon_string: string to pass to `toon_format.decode`
            :param filename: filename to open and pass to `toon_format.decode`
            :param encoding: File encoding
            :param errors: How to handle encoding errors
            :param kwargs: parameters to pass to `BoxList()`
            :return: BoxList object
            """
            box_args = {}
            for arg in list(kwargs.keys()):
                if arg in BOX_PARAMETERS:
                    box_args[arg] = kwargs.pop(arg)

            data = _from_toon(toon_string=toon_string, filename=filename, encoding=encoding, errors=errors, **kwargs)
            if not isinstance(data, list):
                raise BoxError(f"toon data not returned as a list but rather a {type(data).__name__}")
            return cls(data, **box_args)

    else:

        def to_toon(
            self, filename: str | PathLike | None = None, encoding: str = "utf-8", errors: str = "strict", **kwargs
        ):
            raise BoxError('toon is unavailable on this system, please install the "toon_format" package')

        @classmethod
        def from_toon(
            cls,
            toon_string: str | None = None,
            filename: str | PathLike | None = None,
            encoding: str = "utf-8",
            errors: str = "strict",
            **kwargs,
        ):
            raise BoxError('toon is unavailable on this system, please install the "toon_format" package')

    def to_csv(self, filename: str | PathLike | None = None, encoding: str = "utf-8", errors: str = "strict"):
        return _to_csv(self, filename=filename, encoding=encoding, errors=errors)

    @classmethod
    def from_csv(
        cls,
        csv_string: str | None = None,
        filename: str | PathLike | None = None,
        encoding: str = "utf-8",
        errors: str = "strict",
    ):
        return cls(_from_csv(csv_string=csv_string, filename=filename, encoding=encoding, errors=errors))
