#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

from box.box import Box, _parse_box_dots
from box.exceptions import BoxError, BoxTypeError


class ConfigBox(Box):
    """
    Modified box object to add object transforms.

    Allows for build in transforms like:

    cns = ConfigBox(my_bool='yes', my_int='5', my_list='5,4,3,3,2')

    cns.bool('my_bool') # True
    cns.int('my_int') # 5
    cns.list('my_list', mod=lambda x: int(x)) # [5, 4, 3, 3, 2]

    String keys are case-insensitive, like configparser options. Lookups, ``in``,
    deletion and attribute access find a key whatever its case:

    cns = ConfigBox(HOST='localhost')
    cns.host, cns['Host'], 'host' in cns # 'localhost', 'localhost', True

    A ConfigBox never holds two keys that differ only by case. Writing a key that
    matches an existing one replaces it, and the latest write always wins: both its
    value and its spelling are kept, and the key moves to the end like a new key.

    ConfigBox({'Foo': 1, 'foo': 2}) # ConfigBox({'foo': 2})

    Only ``str`` keys are matched this way, other keys must match exactly.
    """

    _protected_keys = dir(Box) + ["bool", "int", "float", "list", "getboolean", "getfloat", "getint"]

    # Case-insensitive key matching.
    #
    # `__ci_index` in the box config maps key.lower() to the stored key, so a miss costs a dict
    # lookup rather than a scan of every key. `__ci_len` is the dict size the index was last in
    # sync with. Writes and deletes made through ConfigBox keep the index current. Any other
    # write (Box internals storing directly on the dict) changes the size, which makes the next
    # lookup rebuild the index.

    def _ci_index(self):
        config = self._box_config
        index = config.get("__ci_index")
        if index is None or config.get("__ci_len") != dict.__len__(self):
            index = {}
            for key in dict.keys(self):
                if isinstance(key, str):
                    index[key.lower()] = key
            config["__ci_index"] = index
            config["__ci_len"] = dict.__len__(self)
        return index

    def _ci_key(self, key):
        """Return the stored key equal to `key` ignoring case, or None. Only str keys are matched."""
        if not isinstance(key, str):
            return None
        if dict.__contains__(self, key):
            return key
        found = self._ci_index().get(key.lower())
        if found is not None and dict.__contains__(self, found):
            return found
        return None

    def _ci_resolve(self, key):
        """Return the key to use for `key`: the stored spelling if one matches, `key` otherwise."""
        if not isinstance(key, str) or dict.__contains__(self, key):
            return key
        found = self._ci_key(key)
        if found is not None:
            return found
        config = self._box_config
        if config["box_dots"] and ("." in key or "[" in key):
            if config["box_dots_exclude"] and config["box_dots_exclude"].match(key):
                return key
            # Match the first segment of a dotted path, nested ConfigBoxes match the rest
            first, rest = _parse_box_dots(self, key)
            found = self._ci_key(first)
            if found is not None and found != first:
                return f"{found}{rest}" if rest.startswith("[") else f"{found}.{rest}"
        return key

    def _ci_after_write(self, key, len_before, was_present):
        """Update the index after `key` was written or deleted through ConfigBox."""
        config = self._box_config
        index = config.get("__ci_index")
        if index is None:
            return
        if config.get("__ci_len") != len_before:
            config["__ci_index"] = None
            return
        present = dict.__contains__(self, key)
        if isinstance(key, str):
            lowered = key.lower()
            if present:
                index[lowered] = key
            elif index.get(lowered) == key:
                del index[lowered]
        expected = len_before + int(present and not was_present) - int(was_present and not present)
        if dict.__len__(self) == expected:
            config["__ci_len"] = expected
        else:
            # Something besides `key` changed (for example a dotted write), rebuild on next use
            config["__ci_index"] = None

    def _ci_check_frozen(self):
        if self._box_config["frozen_box"] and self._box_config["__created"]:
            raise BoxError("Box is frozen")

    def _ci_take_over(self, key, keep_value=False):
        """
        Remove a stored key that differs from `key` only by case, so `key` replaces it.
        With keep_value its value is stored again under the new spelling.
        """
        existing = self._ci_key(key)
        if existing is None or existing == key:
            return
        self._ci_check_frozen()
        comments = self._box_config.get("__comments")
        if comments and existing in comments:
            comments[key] = comments.pop(existing)  # the comment stays with the key under its new spelling
        value = dict.__getitem__(self, existing)
        len_before = dict.__len__(self)
        dict.__delitem__(self, existing)
        if self._box_config["conversion_box"]:
            safe_keys = self._box_config["__safe_keys"]
            safe_key = self._safe_attr(existing)
            if safe_keys.get(safe_key) == existing:
                del safe_keys[safe_key]
        self._ci_after_write(existing, len_before, True)
        if keep_value:
            len_before = dict.__len__(self)
            if self._box_config["conversion_box"]:
                self._box_config["__safe_keys"][self._safe_attr(key)] = key
            dict.__setitem__(self, key, value)
            self._ci_after_write(key, len_before, False)

    def _comment_resolve(self, key):
        found = self._ci_key(key)
        return found if found is not None else super()._comment_resolve(key)

    def __getitem__(self, item, _ignore_default=False):
        return super().__getitem__(self._ci_resolve(item), _ignore_default=_ignore_default)

    def __contains__(self, item):
        if super().__contains__(item):
            return True
        resolved = self._ci_resolve(item)
        return resolved != item and super().__contains__(resolved)

    def __setitem__(self, key, value):
        if key != "_box_config":
            self._ci_check_frozen()
            if isinstance(key, str) and not dict.__contains__(self, key):
                resolved = self._ci_resolve(key)
                if resolved != key and not dict.__contains__(self, resolved):
                    # Dotted path whose first segment matched, the nested box handles the rest
                    key = resolved
                else:
                    self._ci_take_over(key)
        len_before = dict.__len__(self)
        was_present = dict.__contains__(self, key)
        super().__setitem__(key, value)
        self._ci_after_write(key, len_before, was_present)

    def __delitem__(self, key):
        key = self._ci_resolve(key)
        len_before = dict.__len__(self)
        was_present = dict.__contains__(self, key)
        super().__delitem__(key)
        self._ci_after_write(key, len_before, was_present)

    def update(self, *args, **kwargs):
        if self._box_config["frozen_box"]:
            raise BoxError("Box is frozen")
        if len(args) > 1:
            raise BoxTypeError(f"update expected at most 1 argument, got {len(args)}")
        pairs = []
        single_arg = next(iter(args), None)
        if single_arg:
            if hasattr(single_arg, "keys"):
                pairs.extend((k, single_arg[k]) for k in single_arg)
            else:
                pairs.extend(single_arg)
        pairs.extend(kwargs.items())
        # One pair at a time so a later spelling of the same key replaces an earlier one
        for k, v in pairs:
            self._ci_take_over(k)
            len_before = dict.__len__(self)
            was_present = dict.__contains__(self, k)
            super().update(((k, v),))
            self._ci_after_write(k, len_before, was_present)

    def merge_update(self, *args, **kwargs):
        # Give existing keys the incoming spelling first, so the merge itself then matches exactly
        if not kwargs.get("_force_unfrozen"):
            self._ci_check_frozen()
        if len(args) == 1 and args[0]:
            if hasattr(args[0], "keys"):
                incoming = list(args[0].keys())
            else:
                args = (list(args[0]),)  # may be a one-shot iterator, it is read twice
                incoming = [k for k, _ in args[0]]
        else:
            incoming = []
        incoming.extend(k for k in kwargs if k not in ("box_merge_lists", "_force_unfrozen"))
        for k in incoming:
            self._ci_take_over(k, keep_value=True)
        return super().merge_update(*args, **kwargs)

    def _flush_pending_parent(self):
        pending = self._box_config.get("__pending_parent")
        if pending is not None:
            parent, key = pending
            if isinstance(parent, ConfigBox) and parent._ci_key(key) not in (None, key):
                # The key was given a value (under another spelling) since this child was handed
                # out, so the child is stale and is not attached. Ancestors still are, like Box.
                self._box_config.pop("__pending_parent", None)
                parent._flush_pending_parent()
                return
        super()._flush_pending_parent()

    def __dir__(self) -> list[str]:
        return super().__dir__() + ["bool", "int", "float", "list", "getboolean", "getfloat", "getint"]

    def bool(self, item, default=None):
        """
        Return value of key as a boolean

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

        # The configparser false values, plus "n" and "f"
        if isinstance(item, str) and item.strip().lower() in ("n", "no", "false", "f", "0", "off"):
            return False

        return True if item else False

    def int(self, item, default=None):
        """
        Return value of key as an int

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
        """
        Return value of key as a float

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

    def list(self, item, default=None, spliter: str = ",", strip=True, mod=None):
        """
        Return value of key as a list

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
        return f"{self.__class__.__name__}({str(self.to_dict())})"
