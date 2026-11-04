#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Reflected operators keep options, class factories for default_box_attr, ConfigBox "off"."""

import pytest

from box import Box, BoxError, BoxList, ConfigBox


class Sub(Box):
    pass


class TestReflectedOperatorsKeepOptions:
    @pytest.mark.parametrize("op", ["|", "+"])
    def test_plain_dict_on_the_left(self, op):
        right = Sub({"b": {"c": 1}}, box_dots=True, default_box=True, camel_killer_box=True)
        result = {"CamelKey": 1} | right if op == "|" else {"CamelKey": 1} + right
        assert type(result) is Sub
        for option in ("box_dots", "default_box", "camel_killer_box"):
            assert result._box_config[option] is True, option
        assert result["b.c"] == 1
        assert result.camel_key == 1
        assert result.missing == Sub()

    def test_frozen_right_side(self):
        right = Box({"b": 2}, frozen_box=True)
        for result in ({"a": 1} | right, {"a": 1} + right):
            assert result.to_dict() == {"a": 1, "b": 2}
            with pytest.raises(BoxError):
                result.c = 3
        assert right.to_dict() == {"b": 2}

    def test_order_rules_unchanged(self):
        right = Box({"a": 2, "b": 2}, box_dots=True)
        assert ({"a": 1} | right).to_dict() == {"a": 2, "b": 2}
        assert ({"a": 1} + right).to_dict() == {"a": 2, "b": 2}
        assert (right | {"a": 1}).to_dict() == {"a": 1, "b": 2}

    def test_left_operand_is_not_changed(self):
        left = {"a": {"x": 1}}
        result = left | Box(box_dots=True)
        result["a.x"] = 2
        assert left == {"a": {"x": 1}}


class TestDefaultBoxAttrFactories:
    def test_list_class_like_defaultdict(self):
        b = Box(default_box=True, default_box_attr=list)
        assert isinstance(b.tags, BoxList) and b.tags == []
        b.tags = b.tags + [1]
        assert b.to_dict() == {"tags": [1]}

    def test_list_class_with_create_on_get(self):
        b = Box(default_box=True, default_box_attr=list, default_box_create_on_get=True)
        b.tags.append({"a": 1})
        assert b.to_dict() == {"tags": [{"a": 1}]}
        assert type(b.tags[0]) is Box

    @pytest.mark.parametrize("factory, expected", [(int, 0), (str, ""), (set, set()), (lambda: "x", "x")])
    def test_other_factories(self, factory, expected):
        assert Box(default_box=True, default_box_attr=factory).missing == expected

    def test_optional_parameters_are_left_alone(self):
        def factory(key, prefix="item-"):
            return prefix + key

        assert Box(default_box=True, default_box_attr=factory).thing == "item-thing"

    def test_positional_only_and_keyword_only(self):
        def positional(key, box_instance, /):
            return (key, type(box_instance).__name__)

        def keyword_only(*, box_instance, key):
            return (key, type(box_instance).__name__)

        assert Box(default_box=True, default_box_attr=positional).a == ("a", "Box")
        assert Box(default_box=True, default_box_attr=keyword_only).a == ("a", "Box")

    def test_required_unknown_parameter(self):
        def factory(key, other):
            return key

        with pytest.raises(BoxError, match="not 'other'"):
            Box(default_box=True, default_box_attr=factory).a

    def test_class_with_key_parameter(self):
        class Named:
            def __init__(self, key):
                self.key = key

        assert Box(default_box=True, default_box_attr=Named).thing.key == "thing"


class TestConfigBoxBool:
    @pytest.mark.parametrize("value", ["off", "OFF", " Off ", "no", "false", "0", "n", "f", ""])
    def test_false_values(self, value):
        assert ConfigBox(flag=value).bool("flag") is False

    @pytest.mark.parametrize("value", ["on", "yes", "true", "1", "y", "t", "anything"])
    def test_true_values(self, value):
        assert ConfigBox(flag=value).bool("flag") is True
