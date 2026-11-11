#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Integer keys in box_dots paths (#123) and non-destructive camel killer (#279)."""

import pytest

from box import Box, BoxError, BoxKeyError, ConfigBox


class TestDotsIntegerKeys:
    def test_lookup(self):
        info = Box({"uno": {2: "tres", "cuatro": 5}}, default_box=True, box_dots=True)
        assert info["uno.2"] == "tres"
        assert info["uno.cuatro"] == 5
        assert "uno.2" in info
        assert "uno.3" not in info

    def test_first_segment_and_negative(self):
        b = Box({1: {"a": "x"}, "n": {-1: "neg"}}, box_dots=True)
        assert b["1.a"] == "x"
        assert b["n.-1"] == "neg"
        assert "1.a" in b

    def test_plain_keys_are_not_mapped(self):
        b = Box({2: "int"}, box_dots=True)
        with pytest.raises(BoxKeyError):
            b["2"]
        assert "2" not in b
        b["2"] = "str"
        assert b.to_dict() == {2: "int", "2": "str"}

    def test_string_key_still_wins(self):
        b = Box({"uno": {2: "int", "2": "str"}}, box_dots=True)
        assert b["uno.2"] == "str"
        assert b.uno[2] == "int"

    def test_set_and_delete_update_the_int_key(self):
        b = Box({"uno": {2: "tres"}}, box_dots=True)
        b["uno.2"] = "dos"
        assert b.to_dict() == {"uno": {2: "dos"}}
        del b["uno.2"]
        assert b.to_dict() == {"uno": {}}

    def test_missing_still_missing(self):
        b = Box({"uno": {2: "tres"}}, box_dots=True)
        with pytest.raises(BoxKeyError):
            b["uno.3"]
        b2 = Box({"uno": {}}, box_dots=True, default_box=True)
        assert b2["uno.3"] == Box()

    def test_not_digits_or_without_box_dots(self):
        b = Box({"uno": {2: "tres", 1.5: "float"}}, box_dots=True)
        with pytest.raises(BoxKeyError):
            b["uno.²"]  # a unicode digit, not an int
        with pytest.raises(BoxKeyError):
            Box({2: "tres"})["2"]

    def test_box_list_index_unchanged(self):
        b = Box({"items": [{"a": 1}, {"a": 2}]}, box_dots=True)
        assert b["items[1].a"] == 2


class TestCamelKillerKeepKeys:
    def test_round_trip_keeps_original_keys(self):
        data = Box({"loadBalancer": "foo", "sneaky_snake": 1}, camel_killer_box=True, camel_killer_box_keep_keys=True)
        assert data.load_balancer == "foo"
        assert data.loadBalancer == "foo"
        data.load_balancer = "bar"
        assert data.to_dict() == {"loadBalancer": "bar", "sneaky_snake": 1}

    def test_nested_and_lists(self):
        data = Box(
            {"spec": {"clusterIP": "1", "ports": [{"targetPort": 80}]}},
            camel_killer_box=True,
            camel_killer_box_keep_keys=True,
        )
        assert data.spec.cluster_ip == "1"
        assert data.spec.ports[0].target_port == 80
        data.spec.ports[0].target_port = 8080
        assert data.to_dict() == {"spec": {"clusterIP": "1", "ports": [{"targetPort": 8080}]}}

    def test_item_access_uses_original_keys(self):
        data = Box({"loadBalancer": "foo"}, camel_killer_box=True, camel_killer_box_keep_keys=True)
        assert data["loadBalancer"] == "foo"
        with pytest.raises(BoxKeyError):
            data["load_balancer"]

    def test_new_keys_and_delete(self):
        data = Box({"loadBalancer": "foo"}, camel_killer_box=True, camel_killer_box_keep_keys=True)
        data.newField = 1
        data.other_field = 2
        assert data.new_field == 1
        del data.load_balancer
        assert data.to_dict() == {"newField": 1, "other_field": 2}

    def test_dir_lists_snake_aliases(self):
        data = Box({"loadBalancer": "foo"}, camel_killer_box=True, camel_killer_box_keep_keys=True)
        assert "load_balancer" in dir(data)

    def test_destructive_default_unchanged(self):
        data = Box({"loadBalancer": "foo"}, camel_killer_box=True)
        assert data.to_dict() == {"load_balancer": "foo"}

    def test_needs_conversion_box(self):
        with pytest.raises(BoxError):
            Box(camel_killer_box=True, camel_killer_box_keep_keys=True, conversion_box=False)

    def test_as_subclass_default(self):
        class KubeBox(Box):
            _box_defaults = {"camel_killer_box": True, "camel_killer_box_keep_keys": True}

        obj = KubeBox.from_json('{"metadata": {"resourceVersion": "1"}}')
        assert obj.metadata.resource_version == "1"
        assert obj.to_json() == '{"metadata": {"resourceVersion": "1"}}'

    def test_config_box(self):
        cb = ConfigBox({"maxConnections": "5"}, camel_killer_box=True, camel_killer_box_keep_keys=True)
        assert cb.int("max_connections") == 5
        assert cb.to_dict() == {"maxConnections": "5"}


class TestUpdateDottedPaths:
    """update() honors box_dots path semantics, like __setitem__ and merge_update."""

    def test_update_dotted_key_nests(self):
        b = Box(default_box=True, box_dots=True)
        b.update({"x.y": 5})
        assert b["x"]["y"] == 5

    def test_update_dotted_key_extends_existing_path(self):
        b = Box({"x": {"y": 1}}, box_dots=True)
        b.update({"x.z": 5})
        assert b.to_dict() == {"x": {"y": 1, "z": 5}}

    def test_update_dotted_key_with_dots_exclude_stays_literal(self):
        b = Box(box_dots=True, box_dots_exclude=r"^[a-z]+\.[a-z]+$")
        b.update({"keep.this": 1})
        assert b.to_dict() == {"keep.this": 1}

    def test_update_kwargs_dotted_key_nests(self):
        b = Box(default_box=True, box_dots=True)
        b.update(**{"k.k": 9})
        assert b["k"]["k"] == 9

    def test_update_non_dotted_unchanged(self):
        b = Box({"a": 1})
        b.update({"b": 2}, c=3)
        assert b.to_dict() == {"a": 1, "b": 2, "c": 3}

    def test_box_addition_merges_dotted_paths(self):
        b = Box({"x": {"y": 1}}, default_box=True, box_dots=True) + Box({"x.z": 2}, default_box=True, box_dots=True)
        assert b.to_dict() == {"x": {"y": 1, "z": 2}}
