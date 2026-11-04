#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Subclasses can change Box option defaults with _box_defaults (#296, #223, #210)."""

import copy
import pickle

import pytest

from box import Box, BoxError, BoxList, ConfigBox, DDBox


class DefaultBox(Box):
    _box_defaults = {"default_box": True}


class FrozenDefaultBox(DefaultBox):
    _box_defaults = {"frozen_box": True}


class TestBoxDefaults:
    def test_defaults_apply(self):
        b = DefaultBox()
        assert b.missing == DefaultBox()
        assert b._box_config["default_box"] is True
        assert Box()._box_config["default_box"] is False

    def test_explicit_option_wins(self):
        b = DefaultBox(default_box=False)
        with pytest.raises(AttributeError):
            b.missing

    def test_nested_boxes_keep_class_and_options(self):
        b = DefaultBox({"a": {"b": {"c": 1}}, "l": [{"x": 1}]})
        assert type(b.a) is DefaultBox and type(b.a.b) is DefaultBox
        assert type(b.l[0]) is DefaultBox
        assert b.a.b.missing == DefaultBox()
        b.new.deep = 1
        assert type(b.new) is DefaultBox
        assert b.to_dict() == {"a": {"b": {"c": 1}}, "l": [{"x": 1}], "new": {"deep": 1}}

    def test_explicit_option_carries_to_nested_boxes(self):
        b = DefaultBox({"a": {"b": 1}}, default_box=False)
        with pytest.raises(AttributeError):
            b.a.missing

    def test_inherited_and_extended(self):
        b = FrozenDefaultBox({"a": 1})
        assert b._box_config["default_box"] is True
        assert b._box_config["frozen_box"] is True
        with pytest.raises(BoxError):
            b.a = 2
        assert DefaultBox._box_resolved_defaults == {"default_box": True}

    def test_unknown_option_is_rejected_at_class_creation(self):
        with pytest.raises(BoxError, match="defualt_box"):

            class Typo(Box):
                _box_defaults = {"defualt_box": True}

    def test_no_init_override_needed(self):
        # The pattern people tried in #296 / #223 fails, this is the replacement
        class MyConfig(Box):
            _box_defaults = {"default_box": True, "box_dots": True}

        config = MyConfig()
        config["server.host"] = "localhost"
        assert config.to_dict() == {"server": {"host": "localhost"}}

    def test_copy_pickle_and_conversions_keep_defaults(self):
        b = DefaultBox({"a": {"b": 1}})
        for other in (b.copy(), copy.deepcopy(b), pickle.loads(pickle.dumps(b)), DefaultBox.from_json(b.to_json())):
            assert type(other) is DefaultBox
            assert other.a.missing == DefaultBox()

    def test_box_list_conversion(self):
        bl = BoxList([{"a": 1}], box_class=DefaultBox)
        assert type(bl[0]) is DefaultBox
        assert bl[0].missing == DefaultBox()

    def test_ddbox_uses_defaults_and_can_be_overridden(self):
        dd = DDBox({"a": {"b": 1}})
        assert dd["a.b"] == 1
        assert dd.x == DDBox()
        assert DDBox(default_box=False)._box_config["default_box"] is False

    def test_other_subclasses_unchanged(self):
        assert ConfigBox()._box_config["default_box"] is False
        assert ConfigBox._box_resolved_defaults == {}

    def test_options_are_not_data(self):
        b = DefaultBox(a=1, box_dots=True)
        assert b.to_dict() == {"a": 1}
        assert b._box_config["box_dots"] is True
