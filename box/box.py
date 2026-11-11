#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2017-2026 - Chris Griffith - MIT License
"""
Improved dictionary access through dot notation with additional tools.
"""

from __future__ import annotations

import copy
import re
import warnings
from collections.abc import Callable, Generator, Iterable, Mapping
from inspect import signature
from keyword import iskeyword
from os import PathLike
from typing import Any

import box
from box import comments as _comments
from box.converters import (
    BOX_PARAMETERS,
    _from_json,
    _from_msgpack,
    _from_toml,
    _from_toon,
    _from_yaml_with_comments,
    _to_json,
    _to_msgpack,
    _to_toml,
    _to_toon,
    msgpack_available,
    toml_read_library,
    toml_write_library,
    toon_available,
    yaml_available,
)
from box.exceptions import BoxError, BoxKeyError, BoxTypeError, BoxValueError, BoxWarning

__all__ = ["Box"]

_first_cap_re = re.compile("(.)([A-Z][a-z]+)")
_all_cap_re = re.compile("([a-z0-9])([A-Z])")
_list_pos_re = re.compile(r"\[(\d+)\]")

# a sentinel object for indicating no default, in order to allow users
# to pass `None` as a valid default value
NO_DEFAULT = object()
# a sentinel object for indicating when to skip adding a new namespace, allowing `None` keys
NO_NAMESPACE = object()


def _is_ipython():
    try:
        from IPython import get_ipython
    except ImportError:
        ipython = False
    else:
        ipython = True if get_ipython() else False

    return ipython


def _exception_cause(e):
    """
    Unwrap BoxKeyError and BoxValueError errors to their cause.

    Use with `raise ... from _exception_cause(err)` to avoid deeply nested stacktraces, but keep the
    context.
    """
    return e.__cause__ if isinstance(e, (BoxKeyError, BoxValueError)) else e


def _camel_killer(attr):
    """
    CamelKiller, qu'est-ce que c'est?

    Taken from http://stackoverflow.com/a/1176023/3244542
    """
    attr = str(attr)

    s1 = _first_cap_re.sub(r"\1_\2", attr)
    s2 = _all_cap_re.sub(r"\1_\2", s1)
    return re.sub(" *_+", "_", s2.lower())


_tuple_pos_re = re.compile(r"\[(\d+)\]")
_tuple_comment_index_re = re.compile(r"\[(-?\d+)\]")


class _BoxTuple(tuple):
    """
    The tuple ``frozen_box`` stores a list as. Unlike a plain tuple it can carry comments (#184) and
    follows ``box_dots`` list paths such as ``"[0].key"``.
    """

    def __getitem__(self, item, _ignore_default=False):
        if isinstance(item, str) and item.startswith("["):
            list_pos = _tuple_pos_re.match(item)
            if list_pos is None:
                raise BoxTypeError(f"Invalid list index: {item!r}")
            value = tuple.__getitem__(self, int(list_pos.group(1)))
            children = item[list_pos.end() :].lstrip(".")
            if not children:
                return value
            if _ignore_default and isinstance(value, (Box, box.BoxList, _BoxTuple)):
                return value.__getitem__(children, _ignore_default=True)
            return value[children]
        return tuple.__getitem__(self, item)

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
        raise BoxError("Box is frozen")

    def _comment_owner(self, key):
        if key is None:
            return self, None
        if isinstance(key, int) and not isinstance(key, bool):
            index = key + len(self) if key < 0 else key
            if 0 <= index < len(self):
                return self, index
        elif isinstance(key, str) and key.startswith("["):
            list_pos = _tuple_comment_index_re.match(key)
            if list_pos is not None:
                index = int(list_pos.group(1))
                index = index + len(self) if index < 0 else index
                rest = key[list_pos.end() :].lstrip(".")
                if 0 <= index < len(self):
                    if not rest:
                        return self, index
                    child = tuple.__getitem__(self, index)
                    if hasattr(child, "_comment_owner"):
                        return child._comment_owner(rest)
        raise BoxKeyError(f"{key!r} is not in the frozen list, comments can only be attached to existing items")

    def get_comment(self, key: Any = None) -> dict | None:
        """The comments of an item (see ``BoxList.get_comment``), ``None`` for the document comments."""
        return _comments.get_comment(self, key)

    def set_comment(self, key: Any, text: Any, position: str | None = None) -> None:
        _comments.set_comment(self, key, text, position)

    def del_comment(self, key: Any = None) -> None:
        _comments.del_comment(self, key)


def _recursive_tuples(iterable, box_class, recreate_tuples=False, **kwargs):
    out_list = []
    for i in iterable:
        if isinstance(i, dict):
            out_list.append(box_class(i, **kwargs))
        elif isinstance(i, list) or (recreate_tuples and isinstance(i, tuple)):
            out_list.append(_recursive_tuples(i, box_class, recreate_tuples, **kwargs))
        else:
            out_list.append(i)
    out = _BoxTuple(out_list)
    if isinstance(iterable, box.BoxList):
        iterable._comment_copy_to(out)
    return out


def _to_native_tuple(iterable):
    """Convert a tuple's Box/BoxList members back to native types.

    ``frozen_box`` stores lists as tuples of Boxes, so ``to_dict`` needs to
    turn those nested Boxes back into plain dicts to remain serializable.
    """
    out_list = []
    for i in iterable:
        if isinstance(i, Box):
            out_list.append(i.to_dict())
        elif isinstance(i, box.BoxList):
            out_list.append(i.to_list())
        elif isinstance(i, tuple):
            out_list.append(_to_native_tuple(i))
        else:
            out_list.append(i)
    return tuple(out_list)


def _parse_box_dots(bx, item):
    """Split a box_dots key at its first "." or "[". Callers only pass keys that contain one."""
    for idx, char in enumerate(item):
        if char == "[":
            return item[:idx], item[idx:]
        elif char == ".":
            return item[:idx], item[idx + 1 :]
    raise BoxError("Could not split box dots properly")


def _get_dot_paths(bx, current=""):
    """A generator of all the end node keys in a box in box_dots format"""

    def handle_dicts(sub_bx, paths=""):
        for key, value in sub_bx.items():
            yield f"{paths}.{key}" if paths else key
            if isinstance(value, dict):
                yield from handle_dicts(value, f"{paths}.{key}" if paths else key)
            elif isinstance(value, list):
                yield from handle_lists(value, f"{paths}.{key}" if paths else key)

    def handle_lists(bx_list, paths=""):
        for i, value in enumerate(bx_list):
            yield f"{paths}[{i}]"
            if isinstance(value, list):
                yield from handle_lists(value, f"{paths}[{i}]")
            if isinstance(value, dict):
                yield from handle_dicts(value, f"{paths}[{i}]")

    yield from handle_dicts(bx, current)


def _get_box_config():
    return {
        # Internal use only
        "__created": False,
        "__safe_keys": {},
    }


#: Every Box option and its default. Subclasses can change these defaults with ``_box_defaults``.
BOX_OPTION_DEFAULTS: dict[str, Any] = {
    "default_box": False,
    "default_box_attr": NO_DEFAULT,
    "default_box_none_transform": True,
    "default_box_create_on_get": False,
    "frozen_box": False,
    "camel_killer_box": False,
    "camel_killer_box_keep_keys": False,
    "conversion_box": True,
    "modify_tuples_box": False,
    "box_safe_prefix": "x",
    "box_duplicates": "ignore",
    "box_intact_types": (),
    "box_recast": None,
    "box_dots": False,
    "box_dots_exclude": None,
    "box_class": None,
    "box_namespace": (),
}


def _build_box_config(cls, kwargs: dict) -> dict:
    """
    Build the box config for `cls`, removing the Box options from `kwargs` so only data keys remain.

    An option passed explicitly wins, then the class ``_box_defaults``, then ``BOX_OPTION_DEFAULTS``.
    """
    options = {**BOX_OPTION_DEFAULTS, **cls._box_resolved_defaults}
    for name in BOX_OPTION_DEFAULTS:
        if name in kwargs:
            options[name] = kwargs.pop(name)
    config = _get_box_config()
    config.update(options)
    if config["default_box_attr"] is NO_DEFAULT:
        config["default_box_attr"] = cls
    if config["box_class"] is None:
        config["box_class"] = cls
    config["box_intact_types"] = tuple(config["box_intact_types"])
    config["box_dots_exclude"] = re.compile(config["box_dots_exclude"]) if config["box_dots_exclude"] else None
    return config


def _get_property_func(obj, key):
    """
    Try to get property helper functions of given object and property name.

    :param obj: object to be checked for property
    :param key: property name
    :return: a tuple for helper functions(fget, fset, fdel). If no such property, a (None, None, None) returns
    """
    attr = getattr(type(obj), key, None)
    if not isinstance(attr, property):
        return None, None, None
    return attr.fget, attr.fset, attr.fdel


class Box(dict):
    """
    Improved dictionary access through dot notation with additional tools.

    :param default_box: Similar to defaultdict, return a default value
    :param default_box_attr: Specify the default replacement.
        WARNING: If this is not the default 'Box', it will not be recursive
    :param default_box_none_transform: When using default_box, treat keys with none values as absent. True by default
    :param default_box_create_on_get: On lookup of a key that doesn't exist, also store the default value.
        False by default: lookups never change the Box, assigning through a missing key still creates it
    :param frozen_box: After creation, the box cannot be modified
    :param camel_killer_box: Convert CamelCase to snake_case
    :param camel_killer_box_keep_keys: With camel_killer_box, keep the original keys and only add
        snake_case attribute aliases for them (needs conversion_box)
    :param conversion_box: Check for near matching keys as attributes
    :param modify_tuples_box: Recreate incoming tuples with dicts into Boxes
    :param box_safe_prefix: Conversion box prefix for unsafe attributes
    :param box_duplicates: "ignore", "error" or "warn" when duplicates exists in a conversion_box
    :param box_intact_types: tuple of types to ignore converting
    :param box_recast: cast certain keys to a specified type
    :param box_dots: access nested Boxes by period separated keys in string
    :param box_dots_exclude: optional regular expression for dotted keys to exclude
    :param box_class: change what type of class sub-boxes will be created as
    :param box_namespace: the namespace this (possibly nested) Box lives within

    Subclasses may set ``_box_internal_attrs`` to a tuple of attribute names that are stored on
    the instance instead of in the dict data (see ``_box_internal_attrs`` below).
    """

    _box_config: dict[str, Any]

    #: Names that subclasses can list to keep "internal-only" attributes.
    #: Setting or deleting one of these names with attribute access stores it on the
    #: instance (``object.__setattr__``) rather than in the dict data, so it is never
    #: exported, iterated, compared or hashed. See the "Internal Attributes" docs.
    _box_internal_attrs: tuple[str, ...] = ()

    #: Box options this class uses when they are not passed explicitly, for example
    #: ``_box_defaults = {"default_box": True}``. Subclasses inherit and extend them.
    #: See the "Subclassing Box" docs.
    _box_defaults: dict[str, Any] = {}
    _box_resolved_defaults: dict[str, Any] = {}

    _protected_keys = [
        "to_dict",
        "to_json",
        "to_yaml",
        "from_yaml",
        "from_json",
        "from_toml",
        "to_toml",
        "to_msgpack",
        "from_msgpack",
        "to_toon",
        "from_toon",
        "merge_update",
        "get_comment",
        "set_comment",
        "del_comment",
    ] + [attr for attr in dir({}) if not attr.startswith("_")]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        own = cls.__dict__.get("_box_defaults", {})
        unknown = sorted(set(own) - set(BOX_OPTION_DEFAULTS))
        if unknown:
            raise BoxError(f"Unknown Box options in {cls.__name__}._box_defaults: {', '.join(unknown)}")
        # Merged along the inheritance chain, so a subclass only lists what it changes
        cls._box_resolved_defaults = {**getattr(cls, "_box_resolved_defaults", {}), **own}

    def __new__(cls, *args: Any, **kwargs: Any):
        """
        Due to the way pickling works in python 3, we need to make sure
        the box config is created as early as possible.
        """
        config = _build_box_config(cls, kwargs)
        obj = super().__new__(cls, *args, **kwargs)
        obj._box_config = config
        # Pickle reconstructs via __new__ + item assignment + __setstate__.
        # Item assignment happens first, while this Box still has default options,
        # so nested Box/BoxList values must be stored as-is (see __convert_and_store).
        obj._box_config["__unpickling"] = True
        return obj

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__()
        self._box_config = _build_box_config(self.__class__, kwargs)
        if not self._box_config["conversion_box"] and self._box_config["box_duplicates"] != "ignore":
            raise BoxError("box_duplicates are only for conversion_boxes")
        if (
            self._box_config["camel_killer_box_keep_keys"]
            and self._box_config["camel_killer_box"]
            and not self._box_config["conversion_box"]
        ):
            raise BoxError("camel_killer_box_keep_keys needs conversion_box, it provides the snake_case aliases")
        if len(args) == 1:
            if isinstance(args[0], str):
                raise BoxValueError("Cannot extrapolate Box from string")
            if isinstance(args[0], Mapping):
                for k, v in args[0].items():
                    if v is args[0]:
                        v = self
                    if v is None and self._box_config["default_box"] and self._box_config["default_box_none_transform"]:
                        continue
                    self.__setitem__(k, v)
            elif isinstance(args[0], Iterable):
                for k, v in args[0]:
                    self.__setitem__(k, v)
            else:
                raise BoxValueError("First argument must be mapping or iterable")
            if isinstance(args[0], Box):
                args[0]._comment_copy_to(self)
        elif args:
            raise BoxTypeError(f"Box expected at most 1 argument, got {len(args)}")

        for k, v in kwargs.items():
            if args and isinstance(args[0], Mapping) and v is args[0]:
                v = self
            self.__setitem__(k, v)

        self._box_config["__created"] = True

    def __add__(self, other: Mapping[Any, Any]):
        if not isinstance(other, dict):
            raise BoxTypeError("Box can only merge two boxes or a box and a dictionary.")
        new_box = self.copy()
        new_box.merge_update(other, _force_unfrozen=True)  # type: ignore[attr-defined]
        return new_box

    def __radd__(self, other: Mapping[Any, Any]):
        if not isinstance(other, dict):
            raise BoxTypeError("Box can only merge two boxes or a box and a dictionary.")

        new_box = other.copy() if isinstance(other, Box) else self.__new_from_plain(other)
        new_box.merge_update(self, _force_unfrozen=True)  # type: ignore[attr-defined]
        new_box._box_config["frozen_box"] = self._box_config["frozen_box"]  # type: ignore[attr-defined]
        return new_box

    def __new_from_plain(self, other):
        """A Box of this box's class and options (unfrozen, top level) holding a plain dict's data"""
        config = self.__box_config()
        config["frozen_box"] = False
        config.pop("box_namespace")
        return self._box_config["box_class"](other, **config)

    def __iadd__(self, other: Mapping[Any, Any]):
        if not isinstance(other, dict):
            raise BoxTypeError("Box can only merge two boxes or a box and a dictionary.")
        self.merge_update(other)
        return self

    def __or__(self, other: Mapping[Any, Any]):
        if not isinstance(other, dict):
            raise BoxTypeError("Box can only merge two boxes or a box and a dictionary.")
        new_box = self.copy()
        new_box._box_config["frozen_box"] = False
        new_box.update(other)  # type: ignore[attr-defined]
        new_box._box_config["frozen_box"] = self._box_config["frozen_box"]
        return new_box

    def __ror__(self, other: Mapping[Any, Any]):
        if not isinstance(other, dict):
            raise BoxTypeError("Box can only merge two boxes or a box and a dictionary.")
        new_box = other.copy() if isinstance(other, Box) else self.__new_from_plain(other)
        new_box._box_config["frozen_box"] = False  # type: ignore[attr-defined]
        new_box.update(self)  # type: ignore[attr-defined]
        new_box._box_config["frozen_box"] = self._box_config["frozen_box"]  # type: ignore[attr-defined]
        return new_box

    def __ior__(self, other: Mapping[Any, Any]):  # type: ignore[override]
        if not isinstance(other, dict):
            raise BoxTypeError("Box can only merge two boxes or a box and a dictionary.")
        self.update(other)
        return self

    def __sub__(self, other: Mapping[Any, Any]):
        frozen = self._box_config["frozen_box"]
        config = self.__box_config()
        config["frozen_box"] = False
        config.pop("box_namespace")  # Detach namespace; it will be reassigned if we nest again
        output = self._box_config["box_class"](**config)
        if not isinstance(other, dict):
            raise BoxError("Box can only compare two boxes or a box and a dictionary.")
        if not isinstance(other, Box):
            other = self._box_config["box_class"](other, **config)
        for item in self:
            if item not in other:
                output[item] = self[item]
            elif isinstance(self.get(item), Box) and isinstance(other.get(item), Box):
                output[item] = self[item] - other[item]
                if not output[item]:
                    del output[item]
        output._box_config["frozen_box"] = frozen
        return output

    def __hash__(self):
        if self._box_config["frozen_box"]:
            hashing = 54321
            for item in self.items():
                hashing ^= hash(item)
            return hashing
        raise BoxTypeError('unhashable type: "Box"')

    def __dir__(self) -> list[str]:
        items = set(super().__dir__())
        # Only show items accessible by dot notation
        for key in self.keys():
            key = str(key)
            if key.isidentifier() and not iskeyword(key):
                items.add(key)

        keep_keys = self._box_config["camel_killer_box_keep_keys"] and self._box_config["camel_killer_box"]
        for key in self.keys():
            if key not in items or keep_keys:
                if self._box_config["conversion_box"]:
                    key = self._safe_attr(key)
                    if key:
                        items.add(key)

        return list(items)

    def __contains__(self, item):
        in_me = super().__contains__(item)
        if not self._box_config["box_dots"] or not isinstance(item, str):
            return in_me
        if in_me:
            return True
        if not self.__process_dotted_key(item):
            return False
        first_item, children = _parse_box_dots(self, item)
        first_item = self.__dots_int_key(first_item)
        if not super().__contains__(first_item):
            return False
        it = self[first_item]
        if isinstance(it, Box):
            return it.__dots_int_key(children) in it
        if isinstance(it, (box.BoxList, _BoxTuple)):
            # children is the rest of the path starting with "[", e.g. "[0].x"
            try:
                it.__getitem__(children, _ignore_default=True)
            except (KeyError, IndexError, TypeError):
                return False
            return True
        # Other values (strings, numbers) are not traversed by box_dots lookups either
        return False

    def keys(self, dotted: bool = False):
        if not dotted:
            return super().keys()

        if not self._box_config["box_dots"]:
            raise BoxError("Cannot return dotted keys as this Box does not have `box_dots` enabled")

        keys = set()
        for key, value in self.items():
            added = False
            if isinstance(key, str):
                if isinstance(value, Box):
                    for sub_key in value.keys(dotted=True):
                        keys.add(f"{key}.{sub_key}")
                        added = True
                elif isinstance(value, box.BoxList):
                    for pos in value._dotted_helper():
                        keys.add(f"{key}{pos}")
                        added = True
                if not added:
                    keys.add(key)
        return sorted(keys, key=lambda x: str(x))

    def items(self, dotted: bool = False):
        if not dotted:
            return super().items()

        if not self._box_config["box_dots"]:
            raise BoxError("Cannot return dotted keys as this Box does not have `box_dots` enabled")

        return [(k, self[k]) for k in self.keys(dotted=True)]

    def get(self, key, default=NO_DEFAULT):
        if key not in self:
            if default is NO_DEFAULT:
                if self._box_config["default_box"] and self._box_config["default_box_none_transform"]:
                    return self.__get_default(key)
                else:
                    return None
            if isinstance(default, dict) and not isinstance(default, Box):
                return Box(default)
            if isinstance(default, list) and not isinstance(default, box.BoxList):
                return box.BoxList(default)
            return default
        return self[key]

    def __copy_internals(self, new, deep=False, memo=None):
        """Carry instance-only attributes listed in `_box_internal_attrs`, and comments, over to `new`."""
        self._comment_copy_to(new)
        for name in self._box_internal_attrs:
            if name in self.__dict__:
                value = self.__dict__[name]
                object.__setattr__(new, name, copy.deepcopy(value, memo) if deep else value)
        return new

    def copy(self):
        config = self.__box_config()
        config.pop("box_namespace")  # Detach namespace; it will be reassigned if we nest again
        return self.__copy_internals(self.__class__(super().copy(), **config))

    def __copy__(self):
        return self.copy()

    def __deepcopy__(self, memodict=None):
        config = self.__box_config()
        out = self.__class__(**config)
        memodict = memodict if memodict is not None else {}
        memodict[id(self)] = out
        # Fill it like __init__ does, still "being created", so nested Boxes get the frozen config too
        frozen = self._box_config["frozen_box"]
        if frozen:
            out._box_config["__created"] = False
        for k, v in self.items():
            out[copy.deepcopy(k, memodict)] = copy.deepcopy(v, memodict)
        out._box_config["__created"] = True
        self.__copy_internals(out, deep=True, memo=memodict)
        return out

    def __setstate__(self, state):
        self._box_config = state["_box_config"]
        self.__dict__.update(state)
        self._box_config["__created"] = True
        self._box_config["__unpickling"] = False

    def __dots_int_key(self, item):
        """
        A segment of a box_dots path made of digits also matches the int key with that value, so
        "a.2" reaches {"a": {2: ...}} (#123). Only used for path segments, a str key of the same
        value wins, and plain (non dotted) keys are never mapped.
        """
        if (
            self._box_config["box_dots"]
            and isinstance(item, str)
            and item.isascii()
            and item.lstrip("-").isdigit()
            and not dict.__contains__(self, item)
        ):
            as_int = int(item)
            if dict.__contains__(self, as_int):
                return as_int
        return item

    def __camel_destructive(self):
        """camel_killer_box renames keys to snake_case unless camel_killer_box_keep_keys is set"""
        return self._box_config["camel_killer_box"] and not self._box_config["camel_killer_box_keep_keys"]

    def __process_dotted_key(self, item):
        if self._box_config["box_dots"] and isinstance(item, str):
            return ("[" in item) or (
                "." in item
                and not (self._box_config["box_dots_exclude"] and self._box_config["box_dots_exclude"].match(item))
            )
        return False

    def __get_default(self, item):
        if item in ("getdoc", "shape") and _is_ipython():
            return None
        default_value = self._box_config["default_box_attr"]
        if default_value in (self._box_config["box_class"], dict):
            value = self._box_config["box_class"](**self.__box_config(extra_namespace=item))
        elif isinstance(default_value, dict):
            value = self._box_config["box_class"](**self.__box_config(extra_namespace=item), **default_value)
        elif isinstance(default_value, list) or default_value is list:
            value = box.BoxList(**self.__box_config(extra_namespace=item))
        elif isinstance(default_value, Callable):
            # Parameters named key / box_instance receive the missing key and this box. Any other
            # parameter must be optional, so plain factories such as int, set or a lambda work too.
            args = []
            kwargs = {}
            try:
                params = list(signature(default_value).parameters.values())
            except (TypeError, ValueError):  # pragma: no cover (callables without a readable signature)
                params = []
            for param in params:
                if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                    continue
                if param.name in ("key", "box_instance"):
                    passed = item if param.name == "key" else self
                    if param.kind is param.POSITIONAL_ONLY:
                        args.append(passed)
                    else:
                        kwargs[param.name] = passed
                elif param.default is param.empty:
                    raise BoxError(
                        "default_box_attr can only have the required arguments 'key' and 'box_instance', "
                        f"not {param.name!r}"
                    )
            value = default_value(*args, **kwargs)
        elif hasattr(default_value, "copy"):
            value = default_value.copy()
        else:
            value = default_value
        if self._box_config["default_box_create_on_get"]:
            if self.__process_dotted_key(item):
                first_item, children = _parse_box_dots(self, item)
                # An existing first_item only gets here when its value can't be looked into
                # (for example an int), so there is nowhere to store the default
                if first_item not in self.keys():
                    self._flush_pending_parent()
                    super().__setitem__(
                        first_item, self._box_config["box_class"](**self.__box_config(extra_namespace=first_item))
                    )
                    self[first_item].__setitem__(children, value)
            else:
                super().__setitem__(item, value)
        elif isinstance(value, Box) and not self.__process_dotted_key(item):
            # Lookups stay ephemeral, but a later assignment on this child
            # should create the missing parent keys (see _flush_pending_parent).
            # A strong reference is required: intermediate ephemeral parents are otherwise garbage collected.
            value._box_config["__pending_parent"] = (self, item)
        return value

    def __box_config(self, extra_namespace: Any = NO_NAMESPACE) -> dict:
        out = {}
        for k, v in self._box_config.copy().items():
            if not k.startswith("__"):
                out[k] = v
        if extra_namespace is not NO_NAMESPACE and self._box_config["box_namespace"] is not False:
            out["box_namespace"] = (*out["box_namespace"], extra_namespace)
        return out

    def __recast(self, item, value):
        if self._box_config["box_recast"] and item in self._box_config["box_recast"]:
            recast = self._box_config["box_recast"][item]
            try:
                if isinstance(recast, type) and issubclass(recast, (Box, box.BoxList)):
                    return recast(value, **self.__box_config())
                else:
                    return recast(value)
            except ValueError as err:
                raise BoxValueError(f"Cannot convert {value} to {recast}") from _exception_cause(err)
        return value

    def __convert_and_store(self, item, value):
        self._flush_pending_parent()
        if self._box_config["conversion_box"]:
            safe_key = self._safe_attr(item)
            self._box_config["__safe_keys"][safe_key] = item
        if isinstance(value, (int, float, str, bytes, bytearray, bool, complex, set, frozenset)):
            return super().__setitem__(item, value)
        # If the value has already been converted or should not be converted, return it as-is
        if self._box_config["box_intact_types"] and isinstance(value, self._box_config["box_intact_types"]):
            return super().__setitem__(item, value)
        # Pickle sets items before __setstate__, so this Box still has default
        # options. Nested Box/BoxList objects already carry the correct config
        # from their own unpickle; recreating them here would drop box_dots etc.
        if self._box_config.get("__unpickling") and isinstance(value, (Box, box.BoxList)):
            return super().__setitem__(item, value)
        # This is the magic sauce that makes sub dictionaries into new box objects
        if isinstance(value, dict):
            # If box_dots is enabled and the key already exists as a Box (possibly created from dotted keys),
            # merge the new dict into the existing Box instead of overwriting it
            # This fixes issue #305 where dotted keys are lost when a non-dotted key with the same prefix comes after
            if (
                self._box_config["box_dots"]
                and item in self
                and isinstance(self[item], Box)
                and not self._box_config["__created"]
            ):
                # Merge the new dict into the existing Box by setting each key-value pair
                # This ensures proper conversion of nested structures
                for k, v in value.items():
                    self[item].__setitem__(k, v)
                return
            # We always re-create even if it was already a Box object to pass down configurations correctly
            value = self._box_config["box_class"](value, **self.__box_config(extra_namespace=item))
        elif isinstance(value, list) and not isinstance(value, box.BoxList):
            if self._box_config["frozen_box"]:
                value = _recursive_tuples(
                    value,
                    recreate_tuples=self._box_config["modify_tuples_box"],
                    **self.__box_config(extra_namespace=item),
                )
            else:
                value = box.BoxList(value, **self.__box_config(extra_namespace=item))
        elif isinstance(value, box.BoxList):
            if self._box_config["frozen_box"]:
                # A frozen Box gets its own frozen copy, the list it was given stays as it was
                value = box.BoxList(value, **self.__box_config(extra_namespace=item))
            else:
                value.box_options.update(self.__box_config(extra_namespace=item))
        elif self._box_config["modify_tuples_box"] and isinstance(value, tuple):
            value = _recursive_tuples(value, recreate_tuples=True, **self.__box_config(extra_namespace=item))
        super().__setitem__(item, value)

    def __getitem__(self, item, _ignore_default=False):
        try:
            return super().__getitem__(item)
        except KeyError as err:
            if item == "_box_config":
                cause = _exception_cause(err)
                raise BoxKeyError("_box_config should only exist as an attribute and is never defaulted") from cause
            if isinstance(item, slice):
                # In Python 3.12 this changes to a KeyError instead of TypeError
                new_box = self._box_config["box_class"](**self.__box_config())
                for x in list(super().keys())[item.start : item.stop : item.step]:
                    new_box[x] = self[x]
                return new_box
            if self.__process_dotted_key(item):
                first_item, children = _parse_box_dots(self, item)
                first_item = self.__dots_int_key(first_item)
                if first_item not in self.keys() and self.__camel_destructive():
                    first_item = _camel_killer(first_item)
                if first_item in self.keys():
                    child = self[first_item]
                    if isinstance(child, Box):
                        children = child.__dots_int_key(children)
                    if hasattr(child, "__getitem__"):
                        if _ignore_default and isinstance(child, (Box, box.BoxList, _BoxTuple)):
                            return child.__getitem__(children, _ignore_default=True)
                        return child[children]
            if self.__camel_destructive() and isinstance(item, str):
                converted = _camel_killer(item)
                if converted in self.keys():
                    return super().__getitem__(converted)
            if self._box_config["default_box"] and not _ignore_default:
                return self.__get_default(item)
            raise BoxKeyError(str(err)) from _exception_cause(err)
        except TypeError as err:
            if isinstance(item, slice):  # pragma: no cover (Python 3.11, slices became hashable in 3.12)
                new_box = self._box_config["box_class"](**self.__box_config())
                for x in list(super().keys())[item.start : item.stop : item.step]:
                    new_box[x] = self[x]
                return new_box
            raise BoxTypeError(str(err)) from _exception_cause(err)

    def __getattr__(self, item):
        try:
            try:
                value = self.__getitem__(item, _ignore_default=True)
            except KeyError:
                value = object.__getattribute__(self, item)
        except AttributeError as err:
            if item == "_box_config":
                raise BoxError("_box_config key must exist") from _exception_cause(err)
            if self._box_config["conversion_box"]:
                safe_key = self._safe_attr(item)
                if safe_key in self._box_config["__safe_keys"]:
                    return self.__getitem__(self._box_config["__safe_keys"][safe_key])
            if self._box_config["default_box"]:
                if item.startswith("_") and item.endswith("_"):
                    raise BoxKeyError(f"{item}: Does not exist and internal methods are never defaulted")
                return self.__get_default(item)
            raise BoxKeyError(str(err)) from _exception_cause(err)
        return value

    def _flush_pending_parent(self):
        """
        With `default_box_create_on_get=False` a missing key returns an ephemeral child Box that is
        not stored in its parent. The first time something is actually written to that child, attach it
        (and any ephemeral ancestors) to the parent so `b.a.b = 1` creates `a`.

        Nothing is attached if the key has been given a real value since the child was handed out:
        the stale child is left detached rather than overwriting data, so writes to it are lost
        just like any other ephemeral lookup.
        """
        pending = self._box_config.pop("__pending_parent", None)
        if pending is None:
            return
        parent, key = pending
        parent._flush_pending_parent()
        if dict.__contains__(parent, key):
            return
        if parent._box_config["frozen_box"] and parent._box_config["__created"]:
            raise BoxError("Box is frozen")
        if parent._box_config["conversion_box"]:
            parent._box_config["__safe_keys"][parent._safe_attr(key)] = key
        dict.__setitem__(parent, key, self)

    def _comment_store(self, create: bool = True) -> Any:
        store = self._box_config.get("__comments")
        if store is None and create:
            store = self._box_config["__comments"] = {}
        return store

    def _comment_document(self, create: bool = True) -> Any:
        document = self._box_config.get("__comments_document")
        if document is None and create:
            document = self._box_config["__comments_document"] = {}
        return document

    def _comment_check_frozen(self):
        if self._box_config["frozen_box"] and self._box_config["__created"]:
            raise BoxError("Box is frozen")

    def _comment_resolve(self, key):
        """The stored key a key from YAML or the comment API refers to (camel_killer renames keys)."""
        if dict.__contains__(self, key):
            return key
        if isinstance(key, str) and self.__camel_destructive():
            converted = _camel_killer(key)
            if dict.__contains__(self, converted):
                return converted
        return key

    def _comment_owner(self, key):
        """(container, key) that holds the comment for `key`, following box_dots paths."""
        if key is None:
            return self, None
        resolved = self._comment_resolve(key)
        if dict.__contains__(self, resolved):
            return self, resolved
        if self.__process_dotted_key(key):
            first, children = _parse_box_dots(self, key)
            first = self._comment_resolve(self.__dots_int_key(first))
            if dict.__contains__(self, first):
                child = dict.__getitem__(self, first)
                if isinstance(child, Box):
                    return child._comment_owner(child.__dots_int_key(children))
                if isinstance(child, (box.BoxList, _BoxTuple)):
                    return child._comment_owner(children)
        raise BoxKeyError(f"{key!r} is not in the Box, comments can only be attached to existing keys")

    def _comment_copy_to(self, other):
        store = self._box_config.get("__comments")
        if store:
            other._comment_store().update(
                {k: copy.deepcopy(v) for k, v in store.items() if dict.__contains__(other, k)}
            )
        document = self._box_config.get("__comments_document")
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

    def __getstate__(self):
        # Ephemeral-child bookkeeping (a reference to the parent) must never be pickled
        state = self.__dict__.copy()
        config = state.get("_box_config")
        if config is not None and "__pending_parent" in config:
            state["_box_config"] = {k: v for k, v in config.items() if k != "__pending_parent"}
        return state

    def __setitem__(self, key, value):
        if key != "_box_config" and self._box_config["frozen_box"] and self._box_config["__created"]:
            raise BoxError("Box is frozen")
        if self.__process_dotted_key(key):
            first_item, children = _parse_box_dots(self, key)
            first_item = self.__dots_int_key(first_item)
            if first_item in self.keys():
                child = self[first_item]
                if isinstance(child, Box):
                    children = child.__dots_int_key(children)
                if hasattr(child, "__setitem__"):
                    return child.__setitem__(children, value)
            elif self._box_config["default_box"]:
                self._flush_pending_parent()
                if children.startswith("["):
                    super().__setitem__(first_item, box.BoxList(**self.__box_config(extra_namespace=first_item)))
                else:
                    super().__setitem__(
                        first_item, self._box_config["box_class"](**self.__box_config(extra_namespace=first_item))
                    )
                return self[first_item].__setitem__(children, value)
            else:
                raise BoxKeyError(f"'{self.__class__}' object has no attribute {first_item}")
        value = self.__recast(key, value)
        if key not in self.keys() and self.__camel_destructive():
            if isinstance(key, str):
                key = _camel_killer(key)
        if self._box_config["conversion_box"] and self._box_config["box_duplicates"] != "ignore":
            self._conversion_checks(key)
        self.__convert_and_store(key, value)

    def __setattr__(self, key, value):
        if key == "_box_config":
            return object.__setattr__(self, key, value)
        if key in self._box_internal_attrs:
            return object.__setattr__(self, key, value)
        if self._box_config["frozen_box"] and self._box_config["__created"]:
            raise BoxError("Box is frozen")
        if key in self._protected_keys:
            raise BoxKeyError(f'Key name "{key}" is protected')

        safe_key = self._safe_attr(key)
        if safe_key in self._box_config["__safe_keys"]:
            key = self._box_config["__safe_keys"][safe_key]

        # if user has customized property setter, fall back to default implementation
        if _get_property_func(self, key)[1] is not None:
            super().__setattr__(key, value)
        else:
            self.__setitem__(key, value)

    def __delitem__(self, key):
        if self._box_config["frozen_box"]:
            raise BoxError("Box is frozen")
        if key not in self.keys() and self.__process_dotted_key(key):
            first_item, children = _parse_box_dots(self, key)
            first_item = self.__dots_int_key(first_item)
            child = self.__getitem__(first_item, _ignore_default=True)
            if isinstance(child, Box):
                children = child.__dots_int_key(children)
            if hasattr(child, "__delitem__"):
                return child.__delitem__(children)
        if key not in self.keys() and self.__camel_destructive():
            if isinstance(key, str):
                for each_key in self:
                    if _camel_killer(key) == each_key:
                        key = each_key
                        break
        try:
            super().__delitem__(key)
        except KeyError as err:
            raise BoxKeyError(str(err)) from _exception_cause(err)
        store = self._box_config.get("__comments")
        if store:
            store.pop(key, None)
        if self._box_config["conversion_box"]:
            safe_key = self._safe_attr(key)
            safe_keys = self._box_config["__safe_keys"]
            if safe_key in safe_keys and safe_keys[safe_key] == key:
                del safe_keys[safe_key]

    def __delattr__(self, item):
        if item in self._box_internal_attrs:
            return object.__delattr__(self, item)
        if self._box_config["frozen_box"]:
            raise BoxError("Box is frozen")
        if item == "_box_config":
            raise BoxError('"_box_config" is protected')
        if item in self._protected_keys:
            raise BoxKeyError(f'Key name "{item}" is protected')

        property_fdel = _get_property_func(self, item)[2]

        # if user has customized property deleter, route to it
        if property_fdel is not None:
            property_fdel(self)
            return
        try:
            self.__delitem__(item)
        except KeyError as err:
            if self._box_config["conversion_box"]:
                safe_key = self._safe_attr(item)
                if safe_key in self._box_config["__safe_keys"]:
                    self.__delitem__(self._box_config["__safe_keys"][safe_key])
                    return
            if self._box_config["default_box"] and not self._box_config["default_box_create_on_get"]:
                # Every attribute of a default_box looks present (hasattr is True) without being
                # stored, so deleting a missing one is a no-op. argparse.parse_args relies on this.
                return
            raise BoxKeyError(str(err)) from _exception_cause(err)

    def pop(self, key, *args):
        if self._box_config["frozen_box"]:
            raise BoxError("Box is frozen")

        if args:
            if len(args) != 1:
                raise BoxError('pop() takes only one optional argument "default"')
            try:
                item = self.__getitem__(key, _ignore_default=True)
            except (KeyError, IndexError):
                return args[0]
            else:
                del self[key]
                return item
        try:
            item = self[key]
        except KeyError:
            raise BoxKeyError(f"{key}") from None
        else:
            if key in self:
                del self[key]
            # else: a default_box returned a default without storing it, there is nothing to remove
            return item

    def clear(self):
        if self._box_config["frozen_box"]:
            raise BoxError("Box is frozen")
        super().clear()
        self._box_config["__safe_keys"].clear()
        self._box_config.pop("__comments", None)

    def popitem(self):
        if self._box_config["frozen_box"]:
            raise BoxError("Box is frozen")
        try:
            key = next(reversed(super().keys()))  # O(1), most recently inserted like dict
        except StopIteration:
            raise BoxKeyError("Empty box") from None
        return key, self.pop(key)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self})"

    def __str__(self) -> str:
        return str(self.to_dict())

    def __iter__(self) -> Generator:  # type: ignore[type-arg]
        for key in self.keys():
            yield key

    def __reversed__(self) -> Generator:  # type: ignore[type-arg]
        for key in reversed(list(self.keys())):
            yield key

    def to_dict(self) -> dict:
        """
        Turn the Box and sub Boxes back into a native python dictionary.

        :return: python dictionary of this Box
        """
        out_dict = dict(self)
        for k, v in out_dict.items():
            if v is self:
                out_dict[k] = out_dict
            elif isinstance(v, Box):
                out_dict[k] = v.to_dict()
            elif isinstance(v, box.BoxList):
                out_dict[k] = v.to_list()
            elif isinstance(v, tuple):
                out_dict[k] = _to_native_tuple(v)
        return out_dict

    def update(self, *args, **kwargs):
        if self._box_config["frozen_box"]:
            raise BoxError("Box is frozen")
        if len(args) > 1:
            raise BoxTypeError(f"update expected at most 1 argument, got {len(args)}")
        single_arg = next(iter(args), None)
        if single_arg:
            if hasattr(single_arg, "keys"):
                for k in single_arg:
                    self._update_store(k, single_arg[k])
            else:
                for k, v in single_arg:
                    self._update_store(k, v)
        for k in kwargs:
            self._update_store(k, kwargs[k])

    def _update_store(self, key, value):
        # In box_dots mode a dotted key is a path, the same as in
        # __setitem__ and merge_update; storing it literally would create
        # a parallel key that dots lookups cannot reach consistently.
        if self.__process_dotted_key(key):
            self.__setitem__(key, value)
        else:
            self.__convert_and_store(key, value)

    def merge_update(self, *args, **kwargs):
        """
        Recursively update the Box, merging nested dictionaries instead of
        overwriting them like the built-in ``dict.update``.

        The ``box_merge_lists`` keyword controls how lists sharing a key are
        combined:

        * ``None`` (default) - the incoming list replaces the existing one
        * ``"extend"`` - the incoming items are appended to the existing list
        * ``"unique"`` - only incoming items not already present are appended
        * ``"merge"`` - lists are merged element by element, recursing into
          dictionaries that share the same index so their keys are combined.
          Lists nested directly inside lists are merged the same way, any other
          value at a shared index is replaced by the incoming one, and extra
          incoming elements are appended. If the existing value is not a list,
          the incoming list simply replaces it.

        Any other value raises ``BoxValueError``. Note that merging is done in place
        and is not atomic, if an error is raised (for example the Box is frozen)
        part of the update may already have been applied.

        .. code-block:: python

            box_one = Box({"data": [{"a": 1}, {"b": 2}]})
            box_one.merge_update({"data": [{"c": 3}]}, box_merge_lists="merge")
            # Box({'data': [{'a': 1, 'c': 3}, {'b': 2}]})

        :param box_merge_lists: strategy used to merge lists, see above
        """
        merge_type = None
        if "box_merge_lists" in kwargs:
            merge_type = kwargs.pop("box_merge_lists")
        if merge_type not in (None, False, "extend", "unique", "merge"):
            raise BoxValueError(f'box_merge_lists must be None, "extend", "unique" or "merge", got {merge_type!r}')
        force_unfrozen = kwargs.pop("_force_unfrozen", False)

        was_frozen = self._box_config["frozen_box"]
        if force_unfrozen:
            self._box_config["frozen_box"] = False

        try:

            def merge_lists(target, incoming):
                # Element by element: dicts at the same index are merged recursively, lists at the
                # same index are merged the same way, anything else is replaced by the incoming
                # value, and incoming elements beyond the end of `target` are appended.
                for index, item in enumerate(incoming):
                    if index >= len(target):
                        target.append(item)
                        continue
                    current = target[index]
                    if isinstance(current, Box) and isinstance(item, dict):
                        current.merge_update(item, box_merge_lists=merge_type, _force_unfrozen=force_unfrozen)
                    elif isinstance(current, list) and isinstance(item, list):
                        merge_lists(current, item)
                    else:
                        target[index] = item

            def convert_and_set(k, v):
                intact_type = self._box_config["box_intact_types"] and isinstance(
                    v, self._box_config["box_intact_types"]
                )
                if isinstance(v, dict) and not intact_type:
                    # Box objects must be created in case they are already
                    # in the `converted` box_config set
                    v = self._box_config["box_class"](v, **self.__box_config(extra_namespace=k))
                    if k in self and isinstance(self[k], dict):
                        self[k].merge_update(v, box_merge_lists=merge_type, _force_unfrozen=force_unfrozen)
                        return
                if isinstance(v, list) and not intact_type:
                    v = box.BoxList(v, **self.__box_config(extra_namespace=k))
                    if merge_type == "extend" and k in self and isinstance(self[k], list):
                        self[k].extend(v)
                        return
                    if merge_type == "unique" and k in self and isinstance(self[k], list):
                        for item in v:
                            if item not in self[k]:
                                self[k].append(item)
                        return
                    if merge_type == "merge" and k in self and isinstance(self[k], list):
                        merge_lists(self[k], v)
                        return
                self.__setitem__(k, v)

            if (len(args) + int(bool(kwargs))) > 1:
                raise BoxTypeError(f"merge_update expected at most 1 argument, got {len(args) + int(bool(kwargs))}")
            single_arg = next(iter(args), None)
            if single_arg:
                if hasattr(single_arg, "keys"):
                    for k in single_arg:
                        convert_and_set(k, single_arg[k])
                else:
                    for k, v in single_arg:
                        convert_and_set(k, v)

            for key in kwargs:
                convert_and_set(key, kwargs[key])

        finally:
            if force_unfrozen:
                self._box_config["frozen_box"] = was_frozen

    def setdefault(self, item, default=None):
        if item in self:
            return self[item]

        if isinstance(default, dict):
            default = self._box_config["box_class"](default, **self.__box_config(extra_namespace=item))
        if isinstance(default, list):
            default = box.BoxList(default, **self.__box_config(extra_namespace=item))
        self[item] = default
        return self[item]

    def _safe_attr(self, attr):
        """Convert a key into something that is accessible as an attribute"""
        if self._box_config["camel_killer_box_keep_keys"] and self._box_config["camel_killer_box"]:
            # Keys keep their spelling, the attribute alias is the snake_case form
            if isinstance(attr, str):
                attr = _camel_killer(attr)
        if isinstance(attr, str):
            # By assuming most people are using string first we get substantial speed ups
            if attr.isidentifier() and not iskeyword(attr):
                return attr

        if isinstance(attr, tuple):
            attr = "_".join([str(x) for x in attr])

        attr = attr.decode("utf-8", "ignore") if isinstance(attr, bytes) else str(attr)
        if self.__box_config()["camel_killer_box"]:
            attr = _camel_killer(attr)

        if attr.isidentifier() and not iskeyword(attr):
            return attr

        if sum(1 for character in attr if character.isidentifier() and not iskeyword(character)) == 0:
            attr = f"{self.__box_config()['box_safe_prefix']}{attr}"
            if attr.isidentifier() and not iskeyword(attr):
                return attr

        out = []
        last_safe = 0
        for i, character in enumerate(attr):
            if f"x{character}".isidentifier():
                last_safe = i
                out.append(character)
            elif not out:
                continue
            else:
                if last_safe == i - 1:
                    out.append("_")

        out = "".join(out)[: last_safe + 1]

        try:
            int(out[0])
        except (ValueError, IndexError):
            pass
        else:
            out = f"{self.__box_config()['box_safe_prefix']}{out}"

        if iskeyword(out):
            out = f"{self.__box_config()['box_safe_prefix']}{out}"

        return out

    def _conversion_checks(self, item):
        """
        Internal use for checking if a duplicate safe attribute already exists

        :param item: Item to see if a dup exists
        """
        safe_item = self._safe_attr(item)

        if safe_item in self._box_config["__safe_keys"] and self._box_config["__safe_keys"][safe_item] != item:
            dups = [f"{item}({safe_item})", f"{self._box_config['__safe_keys'][safe_item]}({safe_item})"]
            if self._box_config["box_duplicates"].startswith("warn"):
                warnings.warn(f"Duplicate conversion attributes exist: {dups}", BoxWarning)
            else:
                raise BoxError(f"Duplicate conversion attributes exist: {dups}")

    def to_json(
        self,
        filename: str | PathLike | None = None,
        encoding: str = "utf-8",
        errors: str = "strict",
        **json_kwargs,
    ):
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
    def from_json(
        cls,
        json_string: str | None = None,
        filename: str | PathLike | None = None,
        encoding: str = "utf-8",
        errors: str = "strict",
        **kwargs,
    ) -> Box:
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
            raise BoxError(f"json data not returned as a dictionary, but rather a {type(data).__name__}")
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
            Transform the Box object into a YAML string.

            :param filename:  If provided will save to file
            :param default_flow_style: False will recursively dump dicts
            :param encoding: File encoding
            :param errors: How to handle encoding errors
            :param width: Line width for YAML output
            :param sort_keys: True sorts keys alphabetically, the default False keeps insertion order
            :param yaml_kwargs: additional arguments to pass to yaml.dump
            :return: string of YAML (if no filename provided)
            """
            return _comments.dump_yaml(
                self,
                self.to_dict(),
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
        ) -> Box:
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

            data, comments = _from_yaml_with_comments(
                yaml_string=yaml_string, filename=filename, encoding=encoding, errors=errors, **kwargs
            )
            if not data:
                result = cls(**box_args)
            elif not isinstance(data, dict):
                raise BoxError(f"yaml data not returned as a dictionary but rather a {type(data).__name__}")
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
        ) -> Box:
            raise BoxError('yaml is unavailable on this system, please install the "ruamel.yaml" or "PyYAML" package')

    if toml_write_library is not None:

        def to_toml(self, filename: str | PathLike | None = None, encoding: str = "utf-8", errors: str = "strict"):
            """
            Transform the Box object into a toml string.

            :param filename: File to write toml object too
            :param encoding: File encoding
            :param errors: How to handle encoding errors
            :return: string of TOML (if no filename provided)
            """
            return _to_toml(self.to_dict(), filename=filename, encoding=encoding, errors=errors)

    else:

        def to_toml(self, filename: str | PathLike | None = None, encoding: str = "utf-8", errors: str = "strict"):
            raise BoxError('toml is unavailable on this system, please install the "tomli-w" package')

    if toml_read_library is not None:

        @classmethod
        def from_toml(
            cls,
            toml_string: str | None = None,
            filename: str | PathLike | None = None,
            encoding: str = "utf-8",
            errors: str = "strict",
            **kwargs,
        ) -> Box:
            """
            Transforms a toml string or file into a Box object

            :param toml_string: string to pass to `toml.load`
            :param filename: filename to open and pass to `toml.load`
            :param encoding: File encoding
            :param errors: How to handle encoding errors
            :param kwargs: parameters to pass to `Box()`
            :return: Box object
            """
            box_args = {}
            for arg in kwargs.copy():
                if arg in BOX_PARAMETERS:
                    box_args[arg] = kwargs.pop(arg)

            data = _from_toml(toml_string=toml_string, filename=filename, encoding=encoding, errors=errors)
            return cls(data, **box_args)

    else:

        @classmethod
        def from_toml(
            cls,
            toml_string: str | None = None,
            filename: str | PathLike | None = None,
            encoding: str = "utf-8",
            errors: str = "strict",
            **kwargs,
        ) -> Box:
            raise BoxError('toml is unavailable on this system, please install the "tomli" package')

    if msgpack_available:

        def to_msgpack(self, filename: str | PathLike | None = None, **kwargs):
            """
            Transform the Box object into a msgpack string.

            :param filename: File to write msgpack object too
            :param kwargs: parameters to pass to `msgpack.pack`
            :return: bytes of msgpack (if no filename provided)
            """
            return _to_msgpack(self.to_dict(), filename=filename, **kwargs)

        @classmethod
        def from_msgpack(
            cls,
            msgpack_bytes: bytes | None = None,
            filename: str | PathLike | None = None,
            **kwargs,
        ) -> Box:
            """
            Transforms msgpack bytes or file into a Box object

            :param msgpack_bytes: string to pass to `msgpack.unpackb`
            :param filename: filename to open and pass to `msgpack.unpack`
            :param kwargs: parameters to pass to `Box()`
            :return: Box object
            """
            box_args = {}
            for arg in kwargs.copy():
                if arg in BOX_PARAMETERS:
                    box_args[arg] = kwargs.pop(arg)

            data = _from_msgpack(msgpack_bytes=msgpack_bytes, filename=filename, **kwargs)
            if not isinstance(data, dict):
                raise BoxError(f"msgpack data not returned as a dictionary but rather a {type(data).__name__}")
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
        ) -> Box:
            raise BoxError('msgpack is unavailable on this system, please install the "msgpack" package')

    if toon_available:

        def to_toon(
            self, filename: str | PathLike | None = None, encoding: str = "utf-8", errors: str = "strict", **kwargs
        ):
            """
            Transform the Box object into a TOON string.

            :param filename: File to write TOON object too
            :param encoding: File encoding
            :param errors: How to handle encoding errors
            :param kwargs: parameters to pass to `toon_format.encode`
            :return: string of TOON (if no filename provided)
            """
            return _to_toon(self.to_dict(), filename=filename, encoding=encoding, errors=errors, **kwargs)

        @classmethod
        def from_toon(
            cls,
            toon_string: str | None = None,
            filename: str | PathLike | None = None,
            encoding: str = "utf-8",
            errors: str = "strict",
            **kwargs,
        ) -> Box:
            """
            Transforms a TOON string or file into a Box object

            :param toon_string: string to pass to `toon_format.decode`
            :param filename: filename to open and pass to `toon_format.decode`
            :param encoding: File encoding
            :param errors: How to handle encoding errors
            :param kwargs: parameters to pass to `Box()`
            :return: Box object
            """
            box_args = {}
            for arg in kwargs.copy():
                if arg in BOX_PARAMETERS:
                    box_args[arg] = kwargs.pop(arg)

            data = _from_toon(toon_string=toon_string, filename=filename, encoding=encoding, errors=errors, **kwargs)
            if not isinstance(data, dict):
                raise BoxError(f"toon data not returned as a dictionary but rather a {type(data).__name__}")
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
        ) -> Box:
            raise BoxError('toon is unavailable on this system, please install the "toon_format" package')
