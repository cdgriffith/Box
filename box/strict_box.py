from __future__ import annotations

from collections.abc import Mapping

from box.box import Box, _camel_killer, _get_property_func, _parse_box_dots
from box.box_list import BoxList, _list_pos_re
from box.config_box import ConfigBox
from box.exceptions import BoxKeyError


def _existing_destination(target, key):
    """Check the destination used by item assignment without defaulting missing keys."""
    if isinstance(target, ConfigBox):
        key = target._ci_resolve(key)

    if isinstance(target, Box):
        if not _existing_parents(target):
            return False
        if target._Box__process_dotted_key(key):
            first, children = _parse_box_dots(target, key)
            first = target._Box__dots_int_key(first)
            if not dict.__contains__(target, first):
                return False
            child = dict.__getitem__(target, first)
            if hasattr(child, "__setitem__"):
                if isinstance(child, Box):
                    children = child._Box__dots_int_key(children)
                return _existing_destination(child, children)

        if not dict.__contains__(target, key) and target._Box__camel_destructive() and isinstance(key, str):
            key = _camel_killer(key)
        return dict.__contains__(target, key)

    if isinstance(target, BoxList) and target.box_options.get("box_dots") and isinstance(key, str):
        if not key.startswith("["):
            return False
        index = _list_pos_re.search(key)
        if index is None:
            return False
        pos = int(index.group(1))
        if pos >= len(target):
            return False
        if len(index.group()) == len(key):
            return True
        children = key[len(index.group()) :].lstrip(".")
        child = list.__getitem__(target, pos)
        if target.box_options.get("default_box"):
            expected = BoxList if children.startswith("[") else Box
            if not isinstance(child, expected):
                return False
        return _existing_destination(child, children)

    if isinstance(target, dict):
        return dict.__contains__(target, key)
    return isinstance(target, Mapping) and any(stored is key or stored == key for stored in target)


def _existing_parents(target):
    """An ephemeral default must not attach new parent fields during this write."""
    while target._box_config.get("__pending_parent") is not None:
        parent, key = target._box_config["__pending_parent"]
        if not dict.__contains__(parent, key):
            if not isinstance(target, ConfigBox) or not isinstance(parent, ConfigBox) or parent._ci_key(key) is None:
                return False
        target = parent
    return True


class StrictBox(Box):
    """
    A Box whose attributes can only update existing fields.

    Use item assignment or dictionary methods to add fields explicitly. Values
    remain mutable, and nested dictionaries use StrictBox by default.

    .. code-block:: python

        settings = StrictBox(host="localhost", port=8000)
        settings.port = 8080
        settings.prot = 8080  # raises BoxKeyError instead of adding a typo
        settings["debug"] = False
        settings.debug = True

    This restricts attribute assignment, not the shape or types of the data.
    Replacing a nested dictionary establishes its new fields. Normal Box
    options, property setters and declared internal attributes still apply.
    """

    def __setattr__(self, key, value):
        if key == "_box_config" or key in self._box_internal_attrs:
            return super().__setattr__(key, value)

        config = self._box_config
        if config["__created"] and not config["frozen_box"] and key not in self._protected_keys:
            resolved = config["__safe_keys"].get(self._safe_attr(key), key)
            if _get_property_func(self, resolved)[1] is None:
                if not _existing_destination(self, resolved):
                    raise BoxKeyError(
                        f'Cannot create field "{key}" through attribute assignment; use item assignment instead'
                    )

        return super().__setattr__(key, value)
