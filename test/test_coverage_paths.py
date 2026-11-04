#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Behaviour of less travelled code paths: error branches, optional backends and fallbacks."""

import sys
import types

import pytest

import box.converters as converters
import box.from_file as from_file
from box import Box, BoxError, BoxKeyError, BoxList, ConfigBox, box_from_file, box_from_string
from box.box import _parse_box_dots
from box.exceptions import BoxTypeError


@pytest.fixture
def fake_ipython(monkeypatch):
    module = types.ModuleType("IPython")
    module.get_ipython = lambda: object()
    monkeypatch.setitem(sys.modules, "IPython", module)
    return module


class TestBoxPaths:
    def test_ipython_probes_are_not_defaulted(self, fake_ipython):
        b = Box(default_box=True)
        assert b.getdoc is None
        assert b.shape is None
        assert b.other == Box()

    def test_ipython_installed_but_not_running(self, fake_ipython, monkeypatch):
        monkeypatch.setattr(fake_ipython, "get_ipython", lambda: None)
        assert Box(default_box=True).shape == Box()

    def test_parse_box_dots_without_separator(self):
        with pytest.raises(BoxError):
            _parse_box_dots(Box(), "nodots")

    def test_tuple_holding_box_list_to_dict(self):
        b = Box({"a": (BoxList([1, {"x": 1}]), Box(y=2))})
        assert b.to_dict() == {"a": ([1, {"x": 1}], {"y": 2})}
        assert type(b.to_dict()["a"][0]) is list
        assert type(b.to_dict()["a"][0][1]) is dict

    def test_default_box_attr_function_arguments(self):
        def positional(key, box_instance):
            return f"{key}-{type(box_instance).__name__}"

        def keyword(*, key, box_instance):
            return f"{key}:{type(box_instance).__name__}"

        assert Box(default_box=True, default_box_attr=positional).hi == "hi-Box"
        assert Box(default_box=True, default_box_attr=keyword).hi == "hi:Box"

        def bad(name):
            return name

        with pytest.raises(BoxError, match="can only have the arguments"):
            Box(default_box=True, default_box_attr=bad).hi

    def test_create_on_get_dotted_through_non_container(self):
        b = Box({"a": 5}, default_box=True, box_dots=True, default_box_create_on_get=True)
        assert b["a.b"] == Box()
        assert b.to_dict() == {"a": 5}

    def test_unhashable_key(self):
        with pytest.raises(BoxTypeError):
            Box()[["unhashable"]]

    def test_ephemeral_child_of_frozen_box(self):
        b = Box(default_box=True, frozen_box=True)
        child = b.missing
        with pytest.raises(BoxError, match="frozen"):
            child.x = 1
        assert b.to_dict() == {}

    def test_ephemeral_child_without_conversion_box(self):
        b = Box(default_box=True, conversion_box=False)
        b.new.key = 1
        assert b.to_dict() == {"new": {"key": 1}}

    def test_dotted_set_without_parent(self):
        with pytest.raises(BoxKeyError, match="has no attribute a"):
            Box(box_dots=True)["a.b"] = 1

    def test_dotted_paths_through_non_containers(self):
        b = Box({"a": 5}, box_dots=True)
        with pytest.raises(BoxKeyError):
            b["a.b"]
        assert "a.b" not in b
        b["a.b"] = 1  # the int can't hold "b", so the whole key is stored
        assert b.to_dict() == {"a": 5, "a.b": 1}
        del b["a.b"]
        assert b.to_dict() == {"a": 5}
        b2 = Box({"a": 5}, box_dots=True)
        with pytest.raises(BoxKeyError):
            del b2["a.b"]

    def test_dotted_contains_into_box_list(self):
        b = Box({"a": [1, 2]}, box_dots=True)
        assert "a.b" not in b

    def test_camel_killer_delete_non_string_key(self):
        b = Box({1: "a"}, camel_killer_box=True)
        with pytest.raises(BoxKeyError):
            del b[2]
        del b[1]
        assert b == {}

    def test_merge_update_too_many_arguments(self):
        with pytest.raises(BoxTypeError, match="at most 1 argument"):
            Box().merge_update({"a": 1}, b=2)

    def test_setdefault_with_list_path(self):
        b = Box({"a": [1, 2]}, box_dots=True)
        assert b.setdefault("a[1]", 5) == 2
        assert b.to_dict() == {"a": [1, 2]}

    def test_keep_keys_non_string_key(self):
        b = Box({1: "a", "camelCase": 2}, camel_killer_box=True, camel_killer_box_keep_keys=True)
        assert b[1] == "a"
        assert b.camel_case == 2

    def test_operators_with_boxes(self):
        assert (Box(a=1) + Box(b=2)).to_dict() == {"a": 1, "b": 2}
        assert (Box(a=1) | Box(b=2)).to_dict() == {"a": 1, "b": 2}

    def test_subtract_nested_keeps_differences(self):
        result = Box(a={"x": 1, "y": 2}, b=1) - Box(a={"x": 1})
        assert result.to_dict() == {"a": {"y": 2}, "b": 1}

    def test_reflected_operators_with_box(self):
        assert Box(a=1).__radd__(Box(b=2)).to_dict() == {"b": 2, "a": 1}
        assert Box(a=1).__ror__(Box(a=2, b=2)).to_dict() == {"a": 1, "b": 2}

    def test_ephemeral_unfrozen_child_of_frozen_box(self):
        class Other(Box):
            pass

        b = Box(default_box=True, frozen_box=True, default_box_attr=Other)
        child = b.missing
        assert type(child) is Other
        with pytest.raises(BoxError, match="frozen"):
            child.x = 1
        assert b.to_dict() == {}

    def test_dir_skips_keys_without_attribute_name(self):
        names = dir(Box({"...": 1, "ok": 2}, box_safe_prefix=""))
        assert "ok" in names and "" not in names

    def test_dir_without_conversion_box(self):
        names = dir(Box({"good": 1, "not valid": 2}, conversion_box=False))
        assert "good" in names
        assert "not valid" not in names and "not_valid" not in names


class TestBoxListPaths:
    def test_tuple_indexing_into_non_list(self):
        bl = BoxList([[1, 2], {"a": 1}])
        assert bl[0, 1] == 2
        with pytest.raises(BoxTypeError, match="numpy-style"):
            bl[1, 0]

    def test_dotted_delete_into_non_container(self):
        bl = BoxList([5], box_dots=True)
        with pytest.raises(TypeError):
            del bl["[0].x"]
        assert bl == [5]


class TestBoxListPickleFormats:
    def test_loads_box_7_pickles(self, monkeypatch):
        import pickle

        # Box 7 had no __reduce_ex__: items were appended first, then the instance state restored
        with monkeypatch.context() as patch:
            patch.delattr(BoxList, "__reduce_ex__")
            data = pickle.dumps(BoxList([1, {"a": 1}], box_dots=True), protocol=2)
        out = pickle.loads(data)
        assert type(out) is BoxList
        assert out.to_list() == [1, {"a": 1}]
        assert out.box_options["box_dots"] is True

    def test_self_referencing_items_survive_pickle(self):
        import pickle

        bl = BoxList([{"a": 1}])
        bl[0].parent = bl
        out = pickle.loads(pickle.dumps(bl))
        assert out[0].parent is out


class TestConfigBoxPaths:
    def test_update_non_string_and_exact_keys(self):
        cb = ConfigBox({"a": 1})
        cb.update({1: "one", "a": 2})
        assert cb.to_dict() == {"a": 2, 1: "one"}

    def test_missing_dotted_key(self):
        cb = ConfigBox({"a": {"b": 1}}, box_dots=True)
        assert "nope.x" not in cb
        assert cb["A.B"] == 1

    def test_index_rebuilds_after_direct_dict_write(self):
        cb = ConfigBox({"a": 1})
        assert "A" in cb  # builds the lower case index
        dict.__setitem__(cb, "Raw", 2)
        cb["b"] = 3  # the index is stale: dropped and rebuilt on the next lookup
        assert cb.raw == 2 and cb.B == 3

    def test_index_rebuilds_after_direct_write_then_exact_write(self):
        cb = ConfigBox({"a": 1})
        assert "A" in cb
        dict.__setitem__(cb, "Raw", 2)
        cb["a"] = 5  # exact key, no lookup first, so the stale index is noticed on the write
        assert cb.raw == 2 and cb.A == 5

    def test_reflected_add_on_config_box(self):
        assert ({"FOO": 2} + ConfigBox({"Foo": 1, "bar": 3})).to_dict() == {"bar": 3, "Foo": 1}

    def test_index_tracks_non_string_keys(self):
        cb = ConfigBox({"a": 1})
        assert "A" in cb
        cb[5] = "five"
        assert cb[5] == "five" and cb.A == 1

    def test_index_invalidated_by_nested_dotted_write(self):
        cb = ConfigBox(default_box=True, box_dots=True)
        assert "x" not in cb
        cb["a.b"] = 1
        assert cb["A.B"] == 1

    def test_case_variants_without_conversion_box(self):
        cb = ConfigBox({"Foo": 1}, conversion_box=False)
        cb["FOO"] = 2
        cb.merge_update({"foo": 3})
        assert cb.to_dict() == {"foo": 3}

    def test_take_over_keeps_other_alias(self):
        cb = ConfigBox({"a_b": 1, "a b": 2})
        cb["A_B"] = 3
        assert cb.to_dict() == {"a b": 2, "A_B": 3}

    def test_box_config_key_is_stored_as_data(self):
        cb = ConfigBox()
        cb["_box_config"] = 5
        assert dict.__getitem__(cb, "_box_config") == 5

    def test_update_too_many_arguments(self):
        with pytest.raises(BoxTypeError, match="at most 1 argument"):
            ConfigBox().update({"a": 1}, {"b": 2})

    def test_union_on_frozen_config_box(self):
        cb = ConfigBox({"Foo": 1}, frozen_box=True)
        result = cb | {"FOO": 2}
        assert result.to_dict() == {"FOO": 2}
        assert cb.to_dict() == {"Foo": 1}

    def test_list_without_strip(self):
        cb = ConfigBox(items="[a, b]")
        assert cb.list("items", strip=False) == ["[a", " b]"]


class TestConverterPaths:
    @pytest.fixture
    def pyyaml_only(self, monkeypatch):
        if not converters.pyyaml_available:
            pytest.skip("PyYAML is not installed")
        monkeypatch.setattr(converters, "ruamel_available", False)

    @pytest.fixture
    def no_yaml(self, monkeypatch):
        monkeypatch.setattr(converters, "ruamel_available", False)
        monkeypatch.setattr(converters, "pyyaml_available", False)

    def test_no_yaml_library(self, no_yaml, tmp_path):
        path = tmp_path / "a.yaml"
        path.write_text("a: 1\n")
        with pytest.raises(BoxError, match="No YAML Parser"):
            converters._to_yaml({"a": 1})
        with pytest.raises(BoxError, match="No YAML Parser"):
            converters._from_yaml("a: 1")
        with pytest.raises(BoxError, match="No YAML Parser"):
            converters._from_yaml(filename=path)

    def test_pyyaml_file_and_loader(self, pyyaml_only, tmp_path):
        import yaml

        path = tmp_path / "a.yaml"
        path.write_text("a: 1\nb: [1, 2]\n")
        assert Box.from_yaml(filename=path).to_dict() == {"a": 1, "b": [1, 2]}
        assert Box.from_yaml(filename=path, Loader=yaml.SafeLoader).a == 1
        assert Box.from_yaml("a: 1\n", Loader=yaml.SafeLoader).a == 1

    def test_ruamel_attrs_from_file(self, tmp_path):
        if not converters.ruamel_available:
            pytest.skip("ruamel.yaml is not installed")
        path = tmp_path / "a.yaml"
        path.write_text("a: 'x'\n")
        bx = Box.from_yaml(filename=path, ruamel_attrs={"preserve_quotes": True})
        assert bx.to_yaml() == "a: 'x'\n"

    def test_ruamel_dumper_without_sort_attribute(self):
        if not converters.ruamel_available:
            pytest.skip("ruamel.yaml is not installed")
        assert "a" in converters._to_yaml({"a": 1}, ruamel_typ="base")

    def test_toml_package_writer(self, monkeypatch, tmp_path):
        written = []
        fake_toml = types.ModuleType("toml")
        fake_toml.dump = lambda obj, f: written.append(obj) or f.write("a = 1\n")
        fake_toml.dumps = lambda obj: "a = 1\n"
        monkeypatch.setattr(converters, "toml_write_library", fake_toml)
        path = tmp_path / "out.toml"
        converters._to_toml({"a": 1}, filename=path)
        assert path.read_text() == "a = 1\n"
        assert written == [{"a": 1}]


class TestFromFilePaths:
    def test_toon_files(self, tmp_path):
        if not from_file.toon_available:
            pytest.skip("toon_format is not installed")
        good = tmp_path / "data.toon"
        Box(a=1, b="x").to_toon(filename=good)
        assert box_from_file(good).to_dict() == {"a": 1, "b": "x"}
        rows = tmp_path / "rows.toon"
        BoxList([{"a": 1}, {"a": 2}]).to_toon(filename=rows)
        assert box_from_file(rows).to_list() == [{"a": 1}, {"a": 2}]
        bad = tmp_path / "bad.toon"
        bad.write_text('a: "unterminated\n')
        with pytest.raises(BoxError, match="not TOON"):
            box_from_file(bad)

    def test_toon_unavailable(self, tmp_path, monkeypatch):
        monkeypatch.setattr(from_file, "toon_available", False)
        path = tmp_path / "data.toon"
        path.write_text("a: 1\n")
        with pytest.raises(BoxError, match="toon"):
            box_from_file(path)
        with pytest.raises(BoxError, match="toon"):
            box_from_string("a: 1", string_type="toon")

    def test_box_from_string_json(self):
        assert box_from_string('{"a": 1}').to_dict() == {"a": 1}
        assert box_from_string("[1, 2]").to_list() == [1, 2]
        with pytest.raises(BoxError, match="not JSON"):
            box_from_string("{nope")

    def test_box_from_string_toml(self):
        assert box_from_string("a = 1", string_type="toml").to_dict() == {"a": 1}
        with pytest.raises(BoxError, match="not TOML"):
            box_from_string("= nope", string_type="toml")

    def test_box_from_string_yaml(self):
        assert box_from_string("a: 1", string_type="yaml").to_dict() == {"a": 1}
        assert box_from_string("- 1\n- 2\n", string_type="yaml").to_list() == [1, 2]
        with pytest.raises(BoxError, match="not YAML"):
            box_from_string("a: [1", string_type="yaml")

    def test_box_from_string_toon(self):
        if not from_file.toon_available:
            pytest.skip("toon_format is not installed")
        assert box_from_string(Box(a=1).to_toon(), string_type="toon").to_dict() == {"a": 1}
        rows = BoxList([{"a": 1}, {"a": 2}]).to_toon()
        assert box_from_string(rows, string_type="toon").to_list() == [{"a": 1}, {"a": 2}]
        with pytest.raises(BoxError, match="not TOON"):
            box_from_string('a: "unterminated', string_type="toon")

    def test_box_from_string_unknown_type(self):
        with pytest.raises(BoxError, match="Unsupported"):
            box_from_string("a", string_type="xml")
