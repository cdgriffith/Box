#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Edge case and regression tests: hidden state (pickle / copy), ephemeral default_box children,
box_dots parsing, frozen containers, merge_update, operators, converters and subclassing.
"""

import copy
import json
import math
import pickle
import warnings

import pytest

from box import (
    Box,
    BoxError,
    BoxKeyError,
    BoxList,
    ConfigBox,
    DDBox,
    SBox,
    box_from_file,
)
from box.exceptions import BoxTypeError, BoxValueError, BoxWarning


class ListBox(Box):
    pass


class DotsDefaultBox(Box):
    _box_defaults = {"default_box": True, "box_dots": True}


class ParentDefaults(Box):
    _box_defaults = {"box_dots": True}


class ChildDefaults(ParentDefaults):
    _box_defaults = {"default_box": True}


class TrackedBox(Box):
    _box_internal_attrs = ("_meta",)


class PropBox(Box):
    @property
    def temp(self):
        return self.__dict__.get("_temp")

    @temp.setter
    def temp(self, value):
        self.__dict__["_temp"] = value

    @temp.deleter
    def temp(self):
        self.__dict__.pop("_temp", None)

    def describe(self):
        return "described"


class IntactDict(dict):
    pass


class IntactList(list):
    pass


class TestPickleAndCopy:
    def test_pickle_nested_box_dots_keeps_working(self):
        bx = Box({"a": {"b": {"c": 1}}, "l": [{"x": 1}]}, box_dots=True)
        out = pickle.loads(pickle.dumps(bx))
        assert out["a.b.c"] == 1
        assert out["l[0].x"] == 1
        out["a.b.d"] = 2
        assert out.a.b.d == 2
        assert out.a._box_config["box_dots"] is True
        assert out.l.box_options["box_dots"] is True

    def test_pickle_frozen_stays_frozen_and_hashable(self):
        bx = Box({"a": [1, {"b": 2}], "c": 3}, frozen_box=True)
        out = pickle.loads(pickle.dumps(bx))
        assert out == bx
        assert hash(out) == hash(bx)
        assert isinstance(out.a, tuple)
        with pytest.raises(BoxError):
            out.c = 4
        with pytest.raises(BoxError):
            out.a[1].b = 5

    def test_pickle_config_box_keeps_case_insensitivity(self):
        cfg = ConfigBox({"Host": "h", "sub": {"Port": 1}})
        assert cfg.host == "h"  # builds the case index before pickling
        out = pickle.loads(pickle.dumps(cfg))
        assert type(out) is ConfigBox
        assert type(out.sub) is ConfigBox
        assert out["HOST"] == "h"
        assert out.SUB.port == 1
        out["HOST"] = "other"
        assert list(out) == ["sub", "HOST"]

    @pytest.mark.parametrize("module", [pickle, copy])
    def test_subclass_defaults_survive_roundtrip(self, module):
        bx = DotsDefaultBox({"n": {"x": 1}})
        out = pickle.loads(pickle.dumps(bx)) if module is pickle else copy.deepcopy(bx)
        assert type(out) is DotsDefaultBox
        assert type(out.n) is DotsDefaultBox
        assert out["n.x"] == 1
        assert out.missing.deeper is not None
        assert "missing" not in out

    def test_pickle_ephemeral_child_drops_parent_reference(self):
        parent = Box(default_box=True)
        child = parent.ghost
        assert "__pending_parent" in child._box_config
        data = pickle.dumps(child)
        assert b"__pending_parent" not in data
        out = pickle.loads(data)
        assert "__pending_parent" not in out._box_config
        out.x = 1
        assert out == {"x": 1}
        assert "ghost" not in parent

    def test_copy_deepcopy_and_pickle_internal_attrs(self):
        bx = TrackedBox({"a": 1})
        bx._meta = {"seen": [1]}
        assert "_meta" not in bx
        assert bx.to_dict() == {"a": 1}
        shallow = copy.copy(bx)
        deep = copy.deepcopy(bx)
        unpickled = pickle.loads(pickle.dumps(bx))
        assert shallow._meta is bx._meta
        assert deep._meta == bx._meta and deep._meta is not bx._meta
        assert unpickled._meta == {"seen": [1]}
        for each in (shallow, deep, unpickled):
            assert type(each) is TrackedBox
            assert each == {"a": 1}

    @pytest.mark.parametrize("how", ["pickle", "deepcopy"])
    def test_self_referencing_boxlist_roundtrip(self, how):
        bl = BoxList([1, {"a": 2}])
        bl.append(bl)
        out = pickle.loads(pickle.dumps(bl)) if how == "pickle" else copy.deepcopy(bl)
        assert out is not bl
        assert out[2] is out
        assert out[1].a == 2
        as_list = out.to_list()
        assert as_list[2] is as_list

    def test_frozen_boxlist_pickle_copy_deepcopy_refuse_list_mutation(self):
        bl = BoxList([1, {"a": [2, 3]}], frozen_box=True)
        for out in (pickle.loads(pickle.dumps(bl)), copy.copy(bl), copy.deepcopy(bl)):
            assert out == bl
            with pytest.raises(BoxError):
                out.append(1)
            with pytest.raises(BoxError):
                out[0] = 2
        assert hash(copy.copy(bl)) == hash(bl)

    def test_frozen_boxlist_pickle_and_deepcopy_keep_items_frozen(self):
        bl = BoxList([{"a": [2, 3]}], frozen_box=True)
        for out in (pickle.loads(pickle.dumps(bl)), copy.deepcopy(bl)):
            assert hash(out) == hash(bl)
            with pytest.raises(BoxError):
                out[0].a = 1

    def test_pickle_keeps_options_of_boxes_inside_lists(self):
        bx = Box({"l": [{"a": {"b": 1}}]}, box_dots=True)
        out = pickle.loads(pickle.dumps(bx))
        assert out.l[0]._box_config["box_dots"] is True
        standalone = BoxList([{"a": 1}], box_class=ListBox, default_box=True)
        again = pickle.loads(pickle.dumps(standalone))
        assert type(again[0]) is ListBox
        assert again[0]._box_config["default_box"] is True


class TestEphemeralDefaultBox:
    def test_chained_assignment_creates_every_parent(self):
        bx = Box(default_box=True)
        bx.a.b.c = 1
        bx.a.b.d.e = 2
        bx["x"].y["z"] = 3
        assert bx == {"a": {"b": {"c": 1, "d": {"e": 2}}}, "x": {"y": {"z": 3}}}

    def test_lookups_never_store_and_look_empty(self):
        bx = Box({"real": 1}, default_box=True)
        ghost = bx.a.b.c
        assert not ghost
        assert len(ghost) == 0
        assert "x" not in ghost
        assert ghost == {}
        assert ghost == Box()
        assert bx["q"] == {}
        assert bx.get("w") == {}
        assert bx == {"real": 1}
        assert "a" not in bx

    def test_stale_child_does_not_overwrite_real_value(self):
        bx = Box(default_box=True)
        stale = bx.a
        bx.a = {"k": 1}
        stale.z = 2
        assert bx.a == {"k": 1}
        assert stale == {"z": 2}

    def test_child_stored_elsewhere_is_copied_not_aliased(self):
        bx = Box(default_box=True)
        child = bx.a
        bx.other = child
        child.x = 1
        assert bx.other == {}
        assert bx.a == {"x": 1}

    def test_box_dots_missing_list_and_dict_paths_are_created_on_write(self):
        bx = DDBox()
        assert bx["rows[3].name"] == {}
        assert bx == {}
        bx["rows[1].name"] = "x"
        bx["a.b.c"] = 1
        assert bx.rows == [None, {"name": "x"}]
        assert bx["a.b.c"] == 1
        assert isinstance(bx.rows, BoxList)

    def test_frozen_default_box_refuses_child_writes(self):
        bx = Box({"a": 1}, default_box=True, frozen_box=True)
        with pytest.raises(BoxError):
            bx.missing.x = 1
        with pytest.raises(BoxError):
            bx["m"].n = 1
        assert bx == {"a": 1}

    def test_update_and_merge_update_on_ephemeral_child_attach_it(self):
        bx = Box(default_box=True)
        bx.a.merge_update({"x": {"y": 1}})
        bx.b.update(z=2)
        bx.c.update({})
        assert bx == {"a": {"x": {"y": 1}}, "b": {"z": 2}}

    def test_pop_delattr_and_pop_default_are_noops_for_missing_keys(self):
        bx = Box({"keep": 1}, default_box=True)
        assert bx.pop("nope") == {}
        assert bx.pop("nope", 5) == 5
        assert hasattr(bx, "ghost")
        delattr(bx, "ghost")
        with pytest.raises(BoxKeyError):
            del bx["ghost"]
        assert bx == {"keep": 1}


class TestBoxDots:
    def test_negative_and_out_of_range_list_indexes(self):
        bx = Box({"a": [1, 2, 3]}, box_dots=True)
        assert bx["a[2]"] == 3
        with pytest.raises(IndexError):
            bx["a[10]"]
        with pytest.raises(BoxTypeError):
            bx["a[-1]"]
        with pytest.raises(BoxTypeError):
            bx["a[x]"]

    def test_nested_lists_get_set_delete(self):
        bx = Box({"a": [[1, 2], [3, {"y": 4}]]}, box_dots=True)
        assert bx["a[0][1]"] == 2
        assert bx["a[1][1].y"] == 4
        bx["a[1][1].y"] = 5
        bx["a[0][0]"] = {"n": 1}
        assert bx.a[1][1].y == 5
        assert isinstance(bx.a[0][0], Box)
        del bx["a[1][1].y"]
        assert bx.a[1][1] == {}
        del bx["a[0]"]
        assert len(bx.a) == 1

    def test_keys_dotted_are_all_resolvable(self):
        bx = Box({"a": {"b": 1, "c": [1, {"d": 2}, [3]]}, "e": 2}, box_dots=True)
        keys = bx.keys(dotted=True)
        assert keys == ["a.b", "a.c[0]", "a.c[1].d", "a.c[2][0]", "e"]
        for key in keys:
            assert bx[key] is not None
        assert dict(bx.items(dotted=True)) == {"a.b": 1, "a.c[0]": 1, "a.c[1].d": 2, "a.c[2][0]": 3, "e": 2}
        with pytest.raises(BoxError):
            Box({"a": 1}).keys(dotted=True)

    def test_contains_agrees_with_dotted_lookup_through_lists(self):
        bx = Box({"a": [{"x": 1}], "b": {"c": 1}}, box_dots=True)
        for key in bx.keys(dotted=True):
            assert bx[key] is not None
            assert key in bx, key

    def test_get_agrees_with_getitem_for_list_paths(self):
        bx = Box({"a": [{"x": 1}]}, box_dots=True)
        assert bx["a[0].x"] == 1
        assert bx.get("a[0].x") == 1

    def test_box_dots_exclude_keeps_literal_dotted_keys(self):
        bx = Box({"v1.0": 1, "a": {"b": 2}}, box_dots=True, box_dots_exclude=r"v\d")
        assert bx["v1.0"] == 1
        assert bx["a.b"] == 2
        assert "v1.0" in bx
        bx["v2.0"] = 5
        assert dict.__contains__(bx, "v2.0")
        assert list(bx) == ["v1.0", "a", "v2.0"]

    def test_dotted_write_without_parent_needs_default_box(self):
        with pytest.raises(BoxKeyError):
            Box(box_dots=True)["a.b"] = 1
        with pytest.raises(BoxKeyError):
            Box({"a.b": 1}, box_dots=True)
        bx = Box(box_dots=True, default_box=True)
        bx["a.b"] = 1
        bx["x..y"] = 2
        assert bx == {"a": {"b": 1}, "x": {"": {"y": 2}}}

    def test_trailing_dot_key_with_default_box_does_not_crash(self):
        bx = Box(box_dots=True, default_box=True)
        bx["a."] = 1
        assert bx.to_dict() == {"a": {"": 1}}

    def test_setdefault_get_and_pop_with_dotted_keys(self):
        bx = Box({"a": {"b": 1}, "l": [{"k": 1}]}, box_dots=True)
        assert bx.setdefault("a.c", 5) == 5
        assert bx.setdefault("a.b", 99) == 1
        assert bx.setdefault("l[0].k", 99) == 1
        assert bx.get("a.zz", 9) == 9
        assert type(bx.get("a.zz", {"q": 1})) is Box
        assert bx.pop("a.b") == 1
        assert bx.pop("a.b", "gone") == "gone"
        with pytest.raises(BoxKeyError):
            bx.pop("a.b")
        assert bx.a == {"c": 5}

    def test_integer_path_segments_only_match_within_dotted_paths(self):
        bx = Box({"a": {2: "two", "3": "str3", 3: "int3"}, 7: "seven"}, box_dots=True)
        assert bx["a.2"] == "two"
        assert bx["a.3"] == "str3"
        assert "a.2" in bx
        assert "a.9" not in bx
        with pytest.raises(BoxKeyError):
            bx["a"]["2"]
        bx["a.2"] = "TWO"
        assert bx.a[2] == "TWO"
        del bx["a.2"]
        assert 2 not in bx.a
        assert bx[7] == "seven"
        assert "7" not in bx


class TestConversionBox:
    def test_duplicate_detection_warn_error_and_ignore(self):
        with pytest.raises(BoxError):
            Box({"a b": 1, "a_b": 2}, box_duplicates="error")
        with pytest.warns(BoxWarning):
            Box({"a b": 1, "a_b": 2}, box_duplicates="warn")
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            quiet = Box({"a b": 1, "a_b": 2})
        assert len(quiet) == 2
        with pytest.raises(BoxError):
            Box(box_duplicates="error", conversion_box=False)

    def test_keywords_digits_and_unicode_keys_get_safe_aliases(self):
        bx = Box({"class": 1, "def": 2, "1abc": 3, "ключ": 4, "naïve key": 5, "x-y": 6})
        assert bx.xclass == 1
        assert bx.xdef == 2
        assert bx.x1abc == 3
        assert bx.ключ == 4
        assert bx.naïve_key == 5
        assert bx.x_y == 6
        assert bx["class"] == 1
        dirs = dir(bx)
        assert "xclass" in dirs and "ключ" in dirs and "class" not in dirs

    def test_deleting_a_key_releases_its_alias(self):
        bx = Box({"a b": 1}, box_duplicates="error")
        assert bx.a_b == 1
        del bx["a b"]
        with pytest.raises(BoxKeyError):
            bx.a_b
        bx["a_b"] = 2
        assert bx.a_b == 2
        bx.clear()
        bx["a b"] = 3
        assert bx.a_b == 3

    def test_protected_names_stay_methods_but_work_as_keys(self):
        bx = Box()
        with pytest.raises(BoxKeyError):
            bx.keys = 1
        with pytest.raises(BoxKeyError):
            bx.to_dict = 1
        bx["keys"] = 1
        bx["update"] = 2
        assert bx["keys"] == 1
        assert callable(bx.keys)
        assert callable(bx.update)
        assert sorted(bx.keys()) == ["keys", "update"]
        with pytest.raises(BoxKeyError):
            del bx.keys
        with pytest.raises(BoxError):
            del bx._box_config

    def test_setting_method_names(self):
        # Box's own converters are protected keys
        for name in ("to_msgpack", "from_msgpack", "to_toon", "from_toon", "to_json"):
            with pytest.raises(BoxKeyError, match="protected"):
                setattr(Box(), name, 1)

        # Other class attributes are stored as keys, the method still wins for attribute access
        class Described(Box):
            label = "class attribute"

            def describe(self):
                return "method"

        bx = Described()
        bx.describe = 1
        bx.label = 2
        assert bx.to_dict() == {"describe": 1, "label": 2}
        assert bx.describe() == "method"


class TestFrozen:
    def test_hash_equality_and_unhashable_mutable(self):
        one = Box({"a": [1, {"b": 2}], "c": "x"}, frozen_box=True)
        two = Box({"a": [1, {"b": 2}], "c": "x"}, frozen_box=True)
        assert one == two and hash(one) == hash(two)
        assert {one: 1}[two] == 1
        assert len({one, two}) == 1
        with pytest.raises(BoxTypeError):
            hash(Box(a=1))
        with pytest.raises(TypeError):
            hash(BoxList([1]))
        assert hash(BoxList([1, 2], frozen_box=True)) == hash(BoxList([1, 2], frozen_box=True))

    def test_every_mutator_is_refused_and_leaves_data_intact(self):
        bx = Box({"a": 1, "n": {"m": 1}}, frozen_box=True)
        attempts = [
            lambda: bx.__setitem__("b", 1),
            lambda: setattr(bx, "b", 1),
            lambda: delattr(bx, "a"),
            lambda: bx.__delitem__("a"),
            lambda: bx.pop("a"),
            lambda: bx.popitem(),
            lambda: bx.clear(),
            lambda: bx.update(b=1),
            lambda: bx.merge_update({"b": 1}),
            lambda: bx.merge_update({"n": {"m": 2}}),
            lambda: bx.setdefault("zz", 1),
            lambda: bx.n.__setitem__("m", 2),
            lambda: bx.n.update({"m": 2}),
        ]
        for attempt in attempts:
            with pytest.raises(BoxError):
                attempt()
        with pytest.raises(BoxError):
            bx |= {"b": 1}
        with pytest.raises(BoxError):
            bx += {"b": 1}
        assert bx == {"a": 1, "n": {"m": 1}}

    def test_frozen_boxlist_refuses_every_mutator(self):
        bl = BoxList([3, 1, {"a": 1}], frozen_box=True)
        attempts = [
            lambda: bl.append(1),
            lambda: bl.extend([1]),
            lambda: bl.insert(0, 1),
            lambda: bl.pop(),
            lambda: bl.remove(3),
            lambda: bl.reverse(),
            lambda: bl.sort(key=str),
            lambda: bl.clear(),
            lambda: bl.__setitem__(0, 1),
            lambda: bl.__setitem__(slice(0, 1), [1]),
            lambda: bl.__delitem__(0),
            lambda: bl.__iadd__([1]),
            lambda: bl.__imul__(2),
        ]
        for attempt in attempts:
            with pytest.raises(BoxError):
                attempt()
        assert bl == [3, 1, {"a": 1}]

    @pytest.mark.parametrize(
        "loader",
        [
            lambda text, **kw: Box.from_json(text, **kw),
            lambda text, **kw: Box.from_yaml(text, **kw),
        ],
        ids=["json", "yaml"],
    )
    def test_frozen_loaded_from_text_serializes_back(self, loader):
        text = json.dumps({"a": [1, {"b": [2, 3]}], "c": {"d": [{"e": 1}]}})
        bx = loader(text, frozen_box=True)
        assert isinstance(bx.a, tuple)
        assert hash(bx) == hash(loader(text, frozen_box=True))
        assert json.loads(bx.to_json()) == json.loads(text)
        assert Box.from_yaml(bx.to_yaml()).to_dict() == json.loads(text)
        with pytest.raises(BoxError):
            bx.c.d[0].e = 2

    def test_operators_on_frozen_boxes_return_new_frozen_boxes(self):
        frozen = Box({"a": 1, "n": {"x": 1}}, frozen_box=True)
        for result in (frozen + {"b": 2}, frozen | {"b": 2}, {"b": 2} + frozen, {"b": 2} | frozen):
            assert result._box_config["frozen_box"] is True
            assert result["b"] == 2 and result["a"] == 1
            with pytest.raises(BoxError):
                result.c = 1
        assert (frozen - {"a": 1})._box_config["frozen_box"] is True
        assert frozen == {"a": 1, "n": {"x": 1}}
        mutable = Box(m=1) + frozen
        mutable.k = 1
        assert mutable._box_config["frozen_box"] is False


class TestMergeUpdate:
    def test_list_strategies(self):
        def merged(strategy):
            bx = Box({"l": [1, 2], "d": [{"a": 1}]})
            bx.merge_update({"l": [2, 3], "d": [{"b": 2}, {"c": 3}]}, box_merge_lists=strategy)
            return bx.to_dict()

        assert merged(None) == {"l": [2, 3], "d": [{"b": 2}, {"c": 3}]}
        assert merged(False) == {"l": [2, 3], "d": [{"b": 2}, {"c": 3}]}
        assert merged("extend") == {"l": [1, 2, 2, 3], "d": [{"a": 1}, {"b": 2}, {"c": 3}]}
        assert merged("unique") == {"l": [1, 2, 3], "d": [{"a": 1}, {"b": 2}, {"c": 3}]}
        assert merged("merge") == {"l": [2, 3], "d": [{"a": 1, "b": 2}, {"c": 3}]}

    def test_merge_strategy_applies_to_nested_boxes_and_nested_lists(self):
        bx = Box({"a": {"b": {"l": [[1, {"x": 1}], 5]}}})
        bx.merge_update({"a": {"b": {"l": [[9, {"y": 2}, 7], {"z": 1}]}}}, box_merge_lists="merge")
        assert bx.to_dict() == {"a": {"b": {"l": [[9, {"x": 1, "y": 2}, 7], {"z": 1}]}}}
        assert isinstance(bx.a.b.l[0][1], Box)

    def test_unknown_strategy_is_rejected_before_any_change(self):
        bx = Box({"a": 1, "l": [1]})
        for bad in ("replace", "Extend", True, 1):
            with pytest.raises(BoxValueError):
                bx.merge_update({"a": 2, "l": [2]}, box_merge_lists=bad)
        assert bx == {"a": 1, "l": [1]}

    def test_merging_dicts_and_lists_into_incompatible_values(self):
        bx = Box({"num": 1, "txt": "s", "lst": [1], "dct": {"a": 1}})
        bx.merge_update({"num": {"n": 1}, "txt": [1], "lst": {"k": 1}, "dct": [1]}, box_merge_lists="extend")
        assert bx == {"num": {"n": 1}, "txt": [1], "lst": {"k": 1}, "dct": [1]}
        assert isinstance(bx.num, Box) and isinstance(bx.txt, BoxList)

    def test_merge_with_itself_and_with_its_dict_is_idempotent(self):
        bx = Box({"a": {"b": [1, {"c": 1}]}, "d": 1})
        before = bx.to_dict()
        bx.merge_update(bx)
        assert bx.to_dict() == before
        bx.merge_update(bx.to_dict(), box_merge_lists="merge")
        assert bx.to_dict() == before
        bx += bx
        assert bx.to_dict() == before

    def test_merge_update_argument_forms(self):
        bx = Box({"a": {"x": 1}})
        bx.merge_update([("b", 1), ("a", {"y": 2})])
        bx.merge_update(iter([("c", {"d": 1})]))
        bx.merge_update(e={"f": 1})
        bx.merge_update({})
        bx.merge_update()
        assert bx == {"a": {"x": 1, "y": 2}, "b": 1, "c": {"d": 1}, "e": {"f": 1}}
        with pytest.raises(BoxTypeError):
            bx.merge_update({"z": 1}, y=2)
        with pytest.raises(BoxTypeError):
            bx.merge_update({"z": 1}, {"y": 2})
        assert "z" not in bx

    def test_box_intact_types_are_not_converted_or_merged(self):
        bx = Box({"d": {"a": 1}}, box_intact_types=(IntactDict, IntactList))
        bx.merge_update({"d": IntactDict(b=2), "l": IntactList([{"x": 1}])})
        assert type(bx.d) is IntactDict and bx.d == {"b": 2}
        assert type(bx.l) is IntactList and type(bx.l[0]) is dict
        bx.merge_update({"l": IntactList([{"y": 1}])}, box_merge_lists="extend")
        assert type(bx.l) is IntactList and bx.l == [{"y": 1}]


class TestOperators:
    def test_add_merges_deeply_and_right_side_wins(self):
        left = Box({"a": {"x": 1, "y": 1}, "k": 1})
        right = {"a": {"y": 2}, "z": 3}
        assert left + right == {"a": {"x": 1, "y": 2}, "k": 1, "z": 3}
        assert right + left == {"a": {"x": 1, "y": 1}, "k": 1, "z": 3}
        assert list(left + right) == ["a", "k", "z"]
        assert left == {"a": {"x": 1, "y": 1}, "k": 1}
        assert right == {"a": {"y": 2}, "z": 3}

    def test_sub_is_recursive_and_requires_a_mapping(self):
        bx = Box({"a": {"x": 1, "y": 2}, "b": 1, "c": {"z": 1}})
        assert bx - {"a": {"x": 1}, "b": 1, "c": {"z": 1}} == {"a": {"y": 2}}
        assert bx - Box() == bx
        assert bx - bx == {}
        with pytest.raises(BoxError):
            bx - [("a", 1)]
        assert bx == {"a": {"x": 1, "y": 2}, "b": 1, "c": {"z": 1}}

    def test_non_mappings_are_rejected_with_type_error(self):
        bx = Box(a=1)
        for other in ([("b", 1)], "text", 5, None, (("b", 1),)):
            with pytest.raises(BoxTypeError):
                bx + other
            with pytest.raises(BoxTypeError):
                other + bx
            with pytest.raises(BoxTypeError):
                bx | other
            with pytest.raises(BoxTypeError):
                other | bx
            with pytest.raises(BoxTypeError):
                bx.__iadd__(other)
            with pytest.raises(BoxTypeError):
                bx.__ior__(other)
        assert bx == {"a": 1}

    def test_inplace_operators_keep_identity_and_class(self):
        bx = Box({"a": {"x": 1}})
        ident = id(bx)
        nested = bx.a
        bx += {"a": {"y": 2}}
        assert id(bx) == ident and bx.a is nested and nested == {"x": 1, "y": 2}
        bx |= {"a": {"z": 3}}
        assert id(bx) == ident and bx.a == {"z": 3}
        assert type(bx.a) is Box

    def test_results_keep_the_class_and_options_of_the_box_operand(self):
        cfg = ConfigBox({"Key": {"Inner": 1}})
        for result in (cfg + {"other": {"x": 1}}, cfg | {"other": {"x": 1}}, {"o": {"x": 1}} + cfg, {"o": 1} | cfg):
            assert type(result) is ConfigBox
            assert result.key.inner == 1
        sbx = SBox({"a": 1}, default_box=True)
        for result in (sbx + {"b": {"c": 1}}, sbx | {"b": {"c": 1}}):
            assert type(result) is SBox and type(result.b) is SBox
            assert result.missing == {}
            assert "missing" not in result


class TestConverters:
    def test_json_roundtrip_unicode_none_empty_and_encoding(self, tmp_path):
        data = {"ключ": "значение", "emoji": "😀", "none": None, "e1": {}, "e2": [], "l": [{"a": [{"b": None}]}]}
        bx = Box(data)
        assert Box.from_json(bx.to_json()).to_dict() == data
        assert "😀" in bx.to_json()
        assert "\\u" in bx.to_json(ensure_ascii=True)
        for target in (tmp_path / "a.json", str(tmp_path / "b.json")):
            assert bx.to_json(filename=target) is None
            assert Box.from_json(filename=target).to_dict() == data
        path = tmp_path / "utf16.json"
        bx.to_json(filename=path, encoding="utf-16")
        assert Box.from_json(filename=path, encoding="utf-16") == data
        with pytest.raises(UnicodeError):
            Box.from_json(filename=path, encoding="utf-8")

    def test_yaml_roundtrip_keeps_strings_that_look_like_other_types(self, tmp_path):
        data = {"s1": "1.0", "s2": "true", "s3": "null", "s4": "0x10", "s5": "", "n": None, "u": "naïve ключ"}
        data["l"] = [{"a": [], "b": {}}, [1, [2, {"c": "yes"}]]]
        bx = Box(data)
        assert Box.from_yaml(bx.to_yaml()).to_dict() == data
        path = tmp_path / "out.yaml"
        bx.to_yaml(filename=path)
        assert Box.from_yaml(filename=str(path)).to_dict() == data
        assert list(Box.from_yaml("z: 1\na: 2\nm: 3")) == ["z", "a", "m"]

    def test_yaml_scalars_load_as_builtin_types(self):
        bx = Box.from_yaml("f: 1.5\ni: 0x10\nb: true\ns: '1.5'\nd: {x: [1.25, 2]}\nn: ~")
        assert type(bx.f) is float
        assert type(bx.i) is int and bx.i == 16
        assert type(bx.b) is bool
        assert type(bx.s) is str and bx.s == "1.5"
        assert type(bx.d.x[0]) is float and type(bx.d.x[1]) is int
        assert bx.n is None
        assert type(bx) is Box and type(bx.d) is Box and type(bx.d.x) is BoxList

    def test_toml_roundtrip_and_unsupported_none(self, tmp_path):
        data = {"title": "naïve ключ", "tbl": {"a": 1, "arr": [1, 2]}, "items": [{"n": "x"}, {"n": "y"}], "e": {}}
        bx = Box(data)
        assert Box.from_toml(bx.to_toml()).to_dict() == data
        path = tmp_path / "out.toml"
        bx.to_toml(filename=path)
        assert Box.from_toml(filename=path).to_dict() == data
        with pytest.raises(TypeError):
            Box(a=None).to_toml()

    def test_msgpack_roundtrip_including_bytes_and_boxlist(self, tmp_path):
        data = {"b": b"\x00\x01", "u": "ключ", "n": None, "f": 1.5, "l": [{"a": [1, {"b": True}]}], "e": {}}
        bx = Box(data)
        assert Box.from_msgpack(bx.to_msgpack()).to_dict() == data
        path = tmp_path / "out.msgpack"
        bx.to_msgpack(filename=path)
        assert Box.from_msgpack(filename=path).to_dict() == data
        bl = BoxList([{"a": 1}, [2, {"b": 3}], None])
        assert BoxList.from_msgpack(bl.to_msgpack()) == bl
        with pytest.raises(BoxError):
            Box.from_msgpack(BoxList([1]).to_msgpack())
        with pytest.raises(BoxError):
            BoxList.from_msgpack(Box(a=1).to_msgpack())

    def test_toon_roundtrip_and_type_mismatch(self, tmp_path):
        data = {"name": "naïve", "tags": ["a", "b"], "rows": [{"id": 1, "v": "x"}, {"id": 2, "v": "y"}], "n": None}
        bx = Box(data)
        assert Box.from_toon(bx.to_toon()).to_dict() == data
        path = tmp_path / "out.toon"
        bx.to_toon(filename=path)
        assert Box.from_toon(filename=path).to_dict() == data
        bl = BoxList([{"a": 1}, {"a": 2}])
        assert BoxList.from_toon(bl.to_toon()) == bl
        with pytest.raises(BoxError):
            BoxList.from_toon(bx.to_toon())

    def test_csv_roundtrip_quoting_unicode_and_errors(self, tmp_path):
        rows = BoxList([{"a": "x,y", "b": 'say "hi"', "c": "line\nbreak"}, {"a": "ключ", "b": "", "c": "1"}])
        text = rows.to_csv()
        back = BoxList.from_csv(text)
        assert back == rows
        assert all(type(row) is Box for row in back)
        path = tmp_path / "out.csv"
        rows.to_csv(filename=path)
        assert BoxList.from_csv(filename=path) == rows
        assert BoxList([{"n": 1}]).to_csv().splitlines() == ["n", "1"]
        assert BoxList.from_csv(BoxList([{"n": 1}]).to_csv())[0].n == "1"
        with pytest.raises(BoxError):
            BoxList([{"a": 1}, {"b": 2}]).to_csv()
        with pytest.raises(BoxError):
            BoxList.from_csv(filename=tmp_path / "missing.csv")

    def test_special_floats_roundtrip(self):
        bx = Box(pos=math.inf, neg=-math.inf, nan=math.nan, small=5e-324, big=1.7976931348623157e308)
        for back in (
            Box.from_json(bx.to_json()),
            Box.from_yaml(bx.to_yaml()),
            Box.from_toml(bx.to_toml()),
            Box.from_msgpack(bx.to_msgpack()),
        ):
            assert back.pos == math.inf and back.neg == -math.inf
            assert math.isnan(back.nan)
            assert back.small == 5e-324 and back.big == 1.7976931348623157e308
            assert type(back.pos) is float

    def test_box_from_file_errors_and_overrides(self, tmp_path):
        with pytest.raises(BoxError, match="does not exist"):
            box_from_file(tmp_path / "nope.json")
        with pytest.raises(BoxError, match="unknown type"):
            box_from_file(self._write(tmp_path / "a.xyz", "{}"))
        with pytest.raises(BoxError, match="not JSON"):
            box_from_file(self._write(tmp_path / "bad.json", "not json at all"))
        yaml_in_json = self._write(tmp_path / "data.json", "a: 1\nb: [1, 2]\n")
        assert box_from_file(yaml_in_json, file_type="YAML") == {"a": 1, "b": [1, 2]}
        upper = self._write(tmp_path / "UP.JSON", '{"a": {"b": 1}}')
        loaded = box_from_file(upper, box_dots=True, frozen_box=True)
        assert loaded["a.b"] == 1
        with pytest.raises(BoxError):
            loaded.c = 1
        assert isinstance(box_from_file(self._write(tmp_path / "l.json", '[1, {"a": 2}]')), BoxList)
        assert box_from_file(str(upper)) == {"a": {"b": 1}}

    @staticmethod
    def _write(path, text):
        path.write_text(text, encoding="utf-8")
        return path


class TestConfigBox:
    def test_bool_transform_values_defaults_and_missing(self):
        cfg = ConfigBox(yes="yes", no="No", f="F", zero="0", one="1", false="FALSE", empty="", real=False, num=0, two=2)
        for name in ("yes", "one", "two"):
            assert cfg.bool(name) is True
        for name in ("no", "f", "zero", "false", "empty", "real", "num"):
            assert cfg.bool(name) is False
        assert cfg.bool("missing", True) is True
        assert cfg.bool("missing", False) is False
        assert cfg.getboolean("YES") is True
        with pytest.raises(BoxKeyError):
            cfg.bool("missing")

    def test_list_transform_options(self):
        cfg = ConfigBox(a=" 1, 2 ,3 ", b="[x;y]", c="5")
        assert cfg.list("a") == ["1", "2", "3"]
        assert cfg.list("a", mod=int) == [1, 2, 3]
        assert cfg.list("a", strip=False) == [" 1", " 2 ", "3 "]
        assert cfg.list("b", spliter=";") == ["x", "y"]
        assert cfg.list("c") == ["5"]
        assert cfg.list("missing", default=["d"]) == ["d"]
        with pytest.raises(BoxKeyError):
            cfg.list("missing")

    def test_case_insensitive_with_nested_boxes_and_box_dots(self):
        cfg = ConfigBox({"Server": {"Port": "80", "Hosts": {"Main": "a"}}}, box_dots=True)
        assert cfg.server.port == "80"
        assert cfg["SERVER"]["port"] == "80"
        assert cfg["server.port"] == "80"
        assert cfg["SERVER.hosts.MAIN"] == "a"
        assert "server.hosts.main" in cfg
        assert cfg.int("server.port", 0) in (80, 0)
        cfg["SERVER.Port"] = "81"
        assert cfg == {"Server": {"Port": "81", "Hosts": {"Main": "a"}}}
        assert type(cfg.server.hosts) is ConfigBox
        del cfg["server.HOSTS.main"]
        assert cfg.Server.Hosts == {}

    def test_latest_write_wins_for_every_write_path(self):
        cfg = ConfigBox({"Foo": 1})
        cfg["FOO"] = 2
        assert list(cfg.items()) == [("FOO", 2)]
        cfg.update(foo=3)
        assert list(cfg.items()) == [("foo", 3)]
        cfg.merge_update({"Foo": 4})
        assert list(cfg.items()) == [("Foo", 4)]
        cfg.other = 1
        cfg.FOO = 5
        assert list(cfg.items()) == [("other", 1), ("FOO", 5)]
        assert ConfigBox([("a", 1), ("A", 2)]) == {"A": 2}

    def test_default_box_and_ephemeral_children_ignore_case(self):
        cfg = ConfigBox(default_box=True)
        cfg.Sec.a = 1
        cfg.SEC.b = 2
        cfg.sec["c"] = 3
        assert cfg == {"Sec": {"a": 1, "b": 2, "c": 3}}
        stale = cfg.Other
        cfg.OTHER = {"k": 1}
        stale.z = 1
        assert cfg == {"Sec": {"a": 1, "b": 2, "c": 3}, "OTHER": {"k": 1}}
        assert "other" in cfg and "nothing" not in cfg

    def test_frozen_config_box_reads_but_never_writes(self):
        cfg = ConfigBox({"Foo": {"Bar": 1}}, frozen_box=True)
        assert cfg.FOO.bar == 1
        for attempt in (
            lambda: cfg.__setitem__("foo", 2),
            lambda: cfg.__setitem__("FOO", 2),
            lambda: cfg.update(foo=2),
            lambda: cfg.merge_update({"FOO": {"x": 1}}),
            lambda: cfg.__delitem__("foo"),
            lambda: cfg.foo.__setitem__("BAR", 2),
        ):
            with pytest.raises(BoxError):
                attempt()
        assert cfg == {"Foo": {"Bar": 1}}
        assert hash(cfg) == hash(ConfigBox({"Foo": {"Bar": 1}}, frozen_box=True))


class TestBoxListBehavior:
    def test_every_insertion_path_converts_items(self):
        bl = BoxList()
        bl.append({"a": 1})
        bl.insert(0, [{"b": 1}])
        bl.extend([{"c": 1}, [{"d": 1}]])
        bl[1:1] = [{"e": 1}]
        bl[-1] = {"f": [{"g": 1}]}
        assert type(bl[0]) is BoxList and type(bl[0][0]) is Box
        assert type(bl[1]) is Box and bl[1].e == 1
        assert type(bl[2]) is Box and type(bl[3]) is Box
        assert type(bl[-1].f) is BoxList and type(bl[-1].f[0]) is Box

    @pytest.mark.xfail(strict=True, reason="BUG: BoxList += does not convert dicts and lists, fixed by PR #347")
    def test_iadd_converts_items_like_extend(self):
        bl = BoxList()
        bl += [{"a": 1}, [{"b": 2}]]
        assert type(bl[0]) is Box
        assert type(bl[1]) is BoxList and type(bl[1][0]) is Box

    def test_box_class_propagates_to_nested_items(self):
        class MyBox(Box):
            pass

        bl = BoxList([{"a": {"b": [{"c": 1}]}}], box_class=MyBox)
        assert type(bl[0]) is MyBox
        assert type(bl[0].a) is MyBox
        assert type(bl[0].a.b) is BoxList and type(bl[0].a.b[0]) is MyBox
        bl.append({"z": {}})
        assert type(bl[1]) is MyBox and type(bl[1].z) is MyBox

    def test_box_options_flow_from_parent_box_to_list_items(self):
        bx = Box({"l": [{"a": 1}]}, box_dots=True, default_box=True, camel_killer_box=True)
        bx.l.append({"CamelKey": {"X": 1}})
        assert bx.l.box_options["box_dots"] is True
        assert bx["l[1].camel_key.x"] == 1
        assert bx.l[0].missing == {}
        assert "missing" not in bx.l[0]
        bx["l[2].fresh"] = 1
        assert bx.l[2] == {"fresh": 1}

    def test_boxlist_copy_is_shallow_deepcopy_is_independent(self):
        bl = BoxList([{"a": [1]}], box_dots=True)
        shallow = copy.copy(bl)
        deep = copy.deepcopy(bl)
        assert shallow == bl and deep == bl
        assert shallow is not bl and deep is not bl
        assert shallow.box_options["box_dots"] and deep.box_options["box_dots"]
        assert shallow.box_options["box_class"] is deep.box_options["box_class"] is Box
        deep[0].a.append(2)
        deep.append({"n": 1})
        assert bl == [{"a": [1]}]
        assert deep["[0].a[1]"] == 2
        assert deep[1]._box_config["box_dots"] is True


class TestSubclassing:
    def test_box_defaults_inherit_and_explicit_options_win(self):
        child = ChildDefaults({"a": {"b": 1}})
        assert child._box_config["box_dots"] is True
        assert child._box_config["default_box"] is True
        assert child["a.b"] == 1
        assert ParentDefaults()._box_config["default_box"] is False
        assert ChildDefaults(box_dots=False)._box_config["box_dots"] is False
        assert ChildDefaults(default_box=False)._box_config["default_box"] is False
        assert Box()._box_config["box_dots"] is False
        assert DDBox(default_box=False)._box_config["default_box"] is False

    def test_unknown_box_default_is_rejected_at_class_creation(self):
        with pytest.raises(BoxError, match="not_an_option"):

            class Bad(Box):
                _box_defaults = {"not_an_option": 1}

    def test_subclass_defaults_apply_to_nested_conversion_from_json_and_yaml(self):
        text = '{"a": {"b": [{"c": 1}]}}'
        for bx in (ChildDefaults.from_json(text), ChildDefaults.from_yaml(text)):
            assert type(bx) is ChildDefaults
            assert type(bx.a) is ChildDefaults
            assert type(bx.a.b[0]) is ChildDefaults
            assert bx["a.b[0].c"] == 1
            assert bx.a.nothing == {} and "nothing" not in bx.a
        explicit = ChildDefaults.from_json(text, box_dots=False)
        assert explicit.a._box_config["box_dots"] is False

    def test_property_setter_and_deleter_are_used_not_the_data(self):
        bx = PropBox({"k": 1})
        bx.temp = 5
        assert bx.temp == 5
        assert "temp" not in bx
        assert bx.to_dict() == {"k": 1}
        del bx.temp
        assert bx.temp is None
        bx["temp"] = "as key"
        assert bx["temp"] == "as key"
        assert bx.temp is None
        assert bx.describe() == "described"
        bx["describe"] = 1
        assert bx.describe() == "described"
        assert bx["describe"] == 1


class TestDictCompat:
    def test_dict_conversion_and_equality(self):
        bx = Box({"a": {"b": 1}, "l": [1]})
        flat = dict(bx)
        assert type(flat) is dict and type(flat["a"]) is Box
        assert bx == {"a": {"b": 1}, "l": [1]}
        assert {"a": {"b": 1}, "l": [1]} == bx
        assert bx == Box({"l": [1], "a": {"b": 1}}, default_box=True)
        assert bx != {"a": {"b": 2}, "l": [1]}
        assert bx.a == {"b": 1} and bx.l == [1]
        assert bx.l == BoxList([1])
        assert bx.a != BoxList([1])

    def test_constructor_options_are_not_data_when_passed_in_a_dict(self):
        bx = Box({"frozen_box": True, "default_box": 1})
        assert not bx._box_config["frozen_box"]
        assert not bx._box_config["default_box"]
        assert bx == {"frozen_box": True, "default_box": 1}
        bx.new = 1
        opts = Box(a=1, frozen_box=True)
        assert opts == {"a": 1}
        assert Box({"a": 1}, b=2) == {"a": 1, "b": 2}
        assert Box([("a", 1)], b=2) == {"a": 1, "b": 2}
        with pytest.raises(BoxValueError):
            Box("text")
        with pytest.raises(BoxValueError):
            Box(5)
        with pytest.raises(BoxTypeError):
            Box({"a": 1}, {"b": 2})

    def test_fromkeys_and_get_default_conversion(self):
        bx = Box.fromkeys(["a", "b"], {"x": 1})
        assert type(bx) is Box and type(bx.a) is Box and bx.a is not bx.b
        got = bx.get("none", {"q": [{"r": 1}]})
        assert type(got) is Box and type(got.q) is BoxList
        assert type(bx.get("none", [{"r": 1}])[0]) is Box
        assert bx.get("none") is None
        assert bx.get("none", None) is None
        assert "none" not in bx
        dflt = Box(default_box=True).get("zz")
        assert dflt == {}

    def test_live_views_and_reversed(self):
        bx = Box(a=1, b=2)
        keys, values, items = bx.keys(), bx.values(), bx.items()
        bx.c = {"d": 1}
        assert "c" in keys and len(keys) == 3
        assert type(list(values)[-1]) is Box
        assert ("a", 1) in items
        assert list(reversed(bx)) == ["c", "b", "a"]
        del bx.a
        assert list(keys) == ["b", "c"]
        assert bx.popitem() == ("c", {"d": 1}) and bx.popitem() == ("b", 2)
        with pytest.raises(BoxKeyError):
            bx.popitem()

    def test_repr_and_str_of_nested_frozen_and_subclass_boxes(self):
        bx = Box({"a": {"b": [1, {"c": 2}]}})
        assert repr(bx) == "Box({'a': {'b': [1, {'c': 2}]}})"
        assert str(bx) == "{'a': {'b': [1, {'c': 2}]}}"
        assert repr(bx.a.b) == "BoxList([1, {'c': 2}])"
        assert repr(ConfigBox(a=1)) == "ConfigBox({'a': 1})"
        assert repr(SBox(a=1)) == "SBox({'a': 1})"
        assert repr(ChildDefaults(a=1)) == "ChildDefaults({'a': 1})"
        frozen = Box({"a": [1, {"b": 2}]}, frozen_box=True)
        assert repr(frozen) == "Box({'a': (1, {'b': 2})})"
        assert str(Box()) == "{}" and repr(BoxList()) == "BoxList([])"

    def test_contains_with_unhashable_and_odd_keys(self):
        bx = Box({"a": 1, (1, 2): "t", None: "n", 1.5: "f"})
        with pytest.raises(TypeError):
            [] in bx
        with pytest.raises(TypeError):
            {} in bx
        with pytest.raises(TypeError):
            [] in Box(box_dots=True)
        with pytest.raises(TypeError):
            [] in ConfigBox()
        assert (1, 2) in bx and None in bx and 1.5 in bx
        assert bx[(1, 2)] == "t" and bx[None] == "n"
        assert "a.b" not in Box({"a": 1}, box_dots=True)
