#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Audit of the places where BoxList item comments and Box options are kept in sync by hand.

1. Every BoxList mutator, with item comments present, plain / box_dots / frozen: comments must stay
   on the item they were attached to, and new items must be converted to Box / BoxList.
2. box_dots paths must behave the same through every access method.
3. copy / deepcopy / pickle round trips of every Box flavour, with comments.

The matrix was written to reproduce the bugs found in the 8.0.1 audit; they are fixed, these tests keep them so.
"""

import copy
import pickle

import pytest

from box import Box, BoxError, BoxList, ConfigBox, SBox
from box.exceptions import BoxKeyError, BoxTypeError
from box.shorthand_box import DDBox

# --------------------------------------------------------------------------------------------------
# 1. BoxList mutators
# --------------------------------------------------------------------------------------------------

N = 4  # items 0..3, item i is {"id": i} carrying the comment "c<i>"
NEW = 100  # ids >= NEW are items added by the operation, they never carry a comment


def annotated(**options):
    bl = BoxList([{"id": i} for i in range(N)], **options)
    for i in range(N):
        bl.set_comment(i, f"c{i}")
    return bl


def frozen_annotated(**options):
    return BoxList(annotated(**options), frozen_box=True, **options)


def check_comments(bl, kept):
    """
    A comment, wherever it is, must be the one of the item now at that position, and every
    item id in `kept` must still have its comment.
    """
    seen = set()
    for i, item in enumerate(bl):
        comment = bl.get_comment(i)
        if comment is None:
            continue
        assert isinstance(item, Box), f"comment {comment} on non item {item!r} at {i}"
        assert comment == {"eol": f"c{item.id}"}, f"position {i} holds item {item.id} but has comment {comment}"
        seen.add(item.id)
    missing = set(kept) - seen
    assert not missing, f"comments lost for items {sorted(missing)}"


def check_converted(bl, **options):
    assert isinstance(bl, BoxList)
    for item in bl:
        assert not (isinstance(item, dict) and not isinstance(item, Box)), f"{item!r} not converted"
        assert not (isinstance(item, list) and not isinstance(item, BoxList)), f"{item!r} not converted"
        if isinstance(item, Box):
            for k, v in options.items():
                assert item._box_config[k] == v, f"option {k} not passed down to {item!r}"
        if isinstance(item, BoxList):
            for k, v in options.items():
                assert item.box_options.get(k) == v, f"option {k} not passed down to {item!r}"


def _setitem(bl, key, value):
    bl[key] = value


def _delitem(bl, key):
    del bl[key]


def _iadd(bl, value):
    bl += value


def _imul(bl, value):
    bl *= value


ALL = set(range(N))

# (id, operation, ids whose comment must survive)
IN_PLACE_OPS = [
    ("append", lambda bl: bl.append({"id": NEW}), ALL),
    ("append_list", lambda bl: bl.append([{"id": NEW}]), ALL),
    ("extend", lambda bl: bl.extend([{"id": NEW}, [{"id": NEW + 1}]]), ALL),
    ("extend_generator", lambda bl: bl.extend({"id": NEW + i} for i in range(2)), ALL),
    ("extend_self", lambda bl: bl.extend(bl), ALL),
    ("iadd", lambda bl: _iadd(bl, [{"id": NEW}]), ALL),
    ("iadd_tuple", lambda bl: _iadd(bl, ({"id": NEW},)), ALL),
    ("insert_0", lambda bl: bl.insert(0, {"id": NEW}), ALL),
    ("insert_mid", lambda bl: bl.insert(2, {"id": NEW}), ALL),
    ("insert_neg", lambda bl: bl.insert(-1, {"id": NEW}), ALL),
    ("insert_past_end", lambda bl: bl.insert(99, {"id": NEW}), ALL),
    ("insert_before_start", lambda bl: bl.insert(-99, {"id": NEW}), ALL),
    ("pop_last", lambda bl: bl.pop(), {0, 1, 2}),
    ("pop_0", lambda bl: bl.pop(0), {1, 2, 3}),
    ("pop_neg", lambda bl: bl.pop(-3), {0, 2, 3}),
    ("del_1", lambda bl: _delitem(bl, 1), {0, 2, 3}),
    ("del_neg", lambda bl: _delitem(bl, -1), {0, 1, 2}),
    ("remove", lambda bl: bl.remove({"id": 2}), {0, 1, 3}),
    ("clear", lambda bl: bl.clear(), set()),
    ("reverse", lambda bl: bl.reverse(), ALL),
    ("sort_desc", lambda bl: bl.sort(key=lambda x: x.id, reverse=True), ALL),
    ("sort_mixed", lambda bl: bl.sort(key=lambda x: x.id % 2), ALL),
    # A replaced item keeps the comment of its position, like a Box key; the replacement reuses the id
    ("setitem", lambda bl: _setitem(bl, 1, {"id": 1, "new": True}), ALL),
    ("setitem_neg", lambda bl: _setitem(bl, -1, {"id": 3, "new": True}), ALL),
    ("imul_1", lambda bl: _imul(bl, 1), ALL),
    ("imul_2", lambda bl: _imul(bl, 2), ALL),
    ("imul_0", lambda bl: _imul(bl, 0), set()),
    ("imul_neg", lambda bl: _imul(bl, -1), set()),
]

# Slices: the items outside the slice never move (or only shift), their comments should survive
SLICE_OPS = [
    ("del_slice_tail", lambda bl: _delitem(bl, slice(2, None)), {0, 1}),
    ("del_slice_head", lambda bl: _delitem(bl, slice(0, 1)), {1, 2, 3}),
    ("del_slice_step", lambda bl: _delitem(bl, slice(None, None, 2)), {1, 3}),
    ("setitem_slice_same_len", lambda bl: _setitem(bl, slice(3, 4), [{"id": NEW}]), {0, 1, 2}),
    ("setitem_slice_grow", lambda bl: _setitem(bl, slice(1, 2), [{"id": NEW}, {"id": NEW + 1}]), {0, 2, 3}),
    ("setitem_slice_shrink", lambda bl: _setitem(bl, slice(1, 3), []), {0, 3}),
    ("setitem_slice_append", lambda bl: _setitem(bl, slice(N, N), [{"id": NEW}]), ALL),
    ("setitem_ext_slice", lambda bl: _setitem(bl, slice(None, None, 2), [{"id": NEW}, {"id": NEW + 1}]), {1, 3}),
]

DOTS_OPS = [
    ("dots_setitem", lambda bl: _setitem(bl, "[1]", {"id": 1, "new": True}), ALL),
    ("dots_setitem_child", lambda bl: _setitem(bl, "[1].extra", {"x": 1}), ALL),
    ("dots_del", lambda bl: _delitem(bl, "[1]"), {0, 2, 3}),
    ("dots_del_child", lambda bl: _delitem(bl, "[1].id") or bl[1].__setitem__("id", 1), ALL),
]

OPTION_SETS = [pytest.param({}, id="plain"), pytest.param({"box_dots": True}, id="box_dots")]


def _ids(ops):
    return [pytest.param(fn, kept, id=name) for name, fn, kept in ops]


@pytest.mark.parametrize("options", OPTION_SETS)
@pytest.mark.parametrize("operation, kept", _ids(IN_PLACE_OPS))
def test_mutator_keeps_comments_and_converts(options, operation, kept):
    bl = annotated(**options)
    operation(bl)
    check_comments(bl, kept)
    check_converted(bl, **options)


@pytest.mark.parametrize("options", OPTION_SETS)
@pytest.mark.parametrize("operation, kept", _ids(SLICE_OPS))
def test_slice_mutator_keeps_comments_of_untouched_items(options, operation, kept):
    bl = annotated(**options)
    operation(bl)
    check_comments(bl, kept)


@pytest.mark.parametrize("options", OPTION_SETS)
@pytest.mark.parametrize("operation, kept", _ids(SLICE_OPS))
def test_slice_mutator_never_misplaces_comments(options, operation, kept):
    bl = annotated(**options)
    operation(bl)
    check_comments(bl, set())
    check_converted(bl, **options)


@pytest.mark.parametrize("operation, kept", _ids(DOTS_OPS))
def test_box_dots_mutator(operation, kept):
    bl = annotated(box_dots=True)
    operation(bl)
    check_comments(bl, kept)
    check_converted(bl, box_dots=True)


def test_box_dots_mutators_through_parent_box():
    b = Box({"l": [{"id": i} for i in range(N)]}, box_dots=True)
    for i in range(N):
        b.l.set_comment(i, f"c{i}")
    b["l[1]"] = {"id": 1, "new": True}
    check_comments(b.l, ALL)
    del b["l[0]"]
    check_comments(b.l, {1, 2, 3})
    assert b.pop("l[0]").id == 1
    check_comments(b.l, {2, 3})
    assert b.get_comment("l[0]") == {"eol": "c2"}
    assert b.get_comment("l[1]") == {"eol": "c3"}
    check_converted(b.l, box_dots=True)


# ---- non mutating operations: the result carries the comments, the original is untouched ----

COPY_OPS = [
    ("copy", copy.copy),
    ("deepcopy", copy.deepcopy),
    ("pickle", lambda bl: pickle.loads(pickle.dumps(bl))),
    ("pickle_p0", lambda bl: pickle.loads(pickle.dumps(bl, protocol=0))),
    ("BoxList()", lambda bl: BoxList(bl, **bl.box_options)),
]


@pytest.mark.parametrize("options", OPTION_SETS + [pytest.param({"frozen_box": True}, id="frozen")])
@pytest.mark.parametrize("operation", [pytest.param(fn, id=name) for name, fn in COPY_OPS])
def test_copies_keep_comments_options_and_conversion(options, operation):
    bl = frozen_annotated() if options.get("frozen_box") else annotated(**options)
    bl.set_comment(None, "document") if not options.get("frozen_box") else None
    out = operation(bl)
    assert out is not bl
    assert out == bl
    check_comments(out, ALL)
    check_converted(out, **options)
    for k, v in options.items():
        assert out.box_options.get(k) == v
    if not options.get("frozen_box"):
        assert out.get_comment(None) == {"start": "document"}
        out.set_comment(0, "changed")  # comments are not shared with the original
        assert bl.get_comment(0) == {"eol": "c0"}


@pytest.mark.parametrize(
    "operation",
    [
        pytest.param(lambda bl: bl + [{"id": NEW}], id="add"),
        pytest.param(lambda bl: bl * 2, id="mul"),
        pytest.param(lambda bl: 2 * bl, id="rmul"),
    ],
)
def test_binary_operators_convert(operation):
    out = operation(annotated(box_dots=True))
    check_comments(out, set())
    check_converted(out, box_dots=True)


@pytest.mark.parametrize(
    "operation",
    [
        pytest.param(lambda bl: bl + [{"id": NEW}], id="add"),
        pytest.param(lambda bl: bl * 2, id="mul"),
        pytest.param(lambda bl: 2 * bl, id="rmul"),
    ],
)
def test_binary_operators_keep_comments_of_left_operand(operation):
    out = operation(annotated())
    check_comments(out, ALL)


# ---- frozen ----

FROZEN_MUTATORS = [
    ("append", lambda bl: bl.append({"id": NEW})),
    ("extend", lambda bl: bl.extend([{"id": NEW}])),
    ("insert", lambda bl: bl.insert(0, {"id": NEW})),
    ("pop", lambda bl: bl.pop()),
    ("remove", lambda bl: bl.remove(bl[0])),
    ("clear", lambda bl: bl.clear()),
    ("reverse", lambda bl: bl.reverse()),
    ("sort", lambda bl: bl.sort(key=lambda x: -x.id)),
    ("setitem", lambda bl: _setitem(bl, 0, {"id": NEW})),
    ("setitem_slice", lambda bl: _setitem(bl, slice(0, 1), [{"id": NEW}])),
    ("delitem", lambda bl: _delitem(bl, 0)),
    ("delitem_slice", lambda bl: _delitem(bl, slice(0, 1))),
    ("iadd", lambda bl: _iadd(bl, [{"id": NEW}])),
    ("imul", lambda bl: _imul(bl, 2)),
    ("imul_0", lambda bl: _imul(bl, 0)),
    ("set_comment", lambda bl: bl.set_comment(0, "x")),
    ("del_comment", lambda bl: bl.del_comment(0)),
]


def _frozen_direct():
    return frozen_annotated()


def _frozen_through_box():
    # A frozen Box adopting an existing BoxList (for example Box(other_box, frozen_box=True))
    return Box({"l": annotated()}, frozen_box=True).l


def _frozen_through_box_copy():
    return Box(Box({"l": annotated()}), frozen_box=True).l


FROZEN_SOURCES = [
    pytest.param(_frozen_direct, id="BoxList(frozen_box)"),
    pytest.param(lambda: copy.deepcopy(_frozen_direct()), id="deepcopy"),
    pytest.param(lambda: pickle.loads(pickle.dumps(_frozen_direct())), id="pickle"),
    pytest.param(lambda: copy.copy(_frozen_direct()), id="copy"),
]

HALF_FROZEN_SOURCES = [
    pytest.param(_frozen_through_box, id="Box(frozen_box)-adopts-BoxList"),
    pytest.param(_frozen_through_box_copy, id="Box(Box, frozen_box)"),
]


def _frozen_check(source, operation):
    bl = source()
    before = bl.to_list()
    with pytest.raises(BoxError):
        operation(bl)
    assert bl.to_list() == before
    check_comments(bl, ALL)


@pytest.mark.parametrize("source", FROZEN_SOURCES)
@pytest.mark.parametrize("operation", [pytest.param(fn, id=name) for name, fn in FROZEN_MUTATORS])
def test_frozen_boxlist_rejects_every_mutator(source, operation):
    _frozen_check(source, operation)


@pytest.mark.parametrize("source", HALF_FROZEN_SOURCES)
@pytest.mark.parametrize(
    "operation",
    [pytest.param(fn, id=name) for name, fn in FROZEN_MUTATORS],
)
def test_boxlist_frozen_by_parent_box_rejects_every_mutator(source, operation):
    _frozen_check(source, operation)


def test_freezing_a_copy_does_not_freeze_the_source_list():
    src = Box({"l": [1, 2]})
    Box(src, frozen_box=True)
    src.l[0] = 9
    src.l.set_comment(0, "still mutable")
    assert src.l == [9, 2]


def test_freezing_a_box_freezes_list_items():
    frozen = Box(Box({"lst": [{"i": 0}]}), frozen_box=True)
    assert frozen.lst[0]._box_config["frozen_box"]
    with pytest.raises(BoxError):
        frozen.lst[0].i = 5
    hash(frozen)


def test_frozen_from_yaml_keeps_list_comments():
    pytest.importorskip("ruamel.yaml")
    text = "# doc\ntop: 1  # top-c\nlst:\n- i: 0  # i0\n- 2  # l1\n"
    assert Box.from_yaml(text).to_yaml() == text
    assert Box.from_yaml(text, frozen_box=True).to_yaml() == text


def test_frozen_boxlist_items_are_frozen_and_hash_is_stable():
    bl = frozen_annotated(box_dots=True)
    assert all(item._box_config["frozen_box"] for item in bl)
    with pytest.raises(BoxError):
        bl[0].id = 5
    with pytest.raises(BoxError):
        bl["[0].id"] = 5
    assert bl["[0].id"] == 0
    assert hash(bl) == hash(pickle.loads(pickle.dumps(bl))) == hash(copy.deepcopy(bl))


# --------------------------------------------------------------------------------------------------
# 2. box_dots consistency
# --------------------------------------------------------------------------------------------------


def dots_box(**options):
    return Box({"a": {"b": 1}, "l": [{"x": 1}, [10, 11]], "s": "str"}, box_dots=True, **options)


EXISTING_PATHS = [("a.b", 1), ("l[0].x", 1), ("l[1][0]", 10), ("l[1]", [10, 11])]
MISSING_PATHS = ["a.zz", "zz.yy", "l[0].zz", "l[9]", "l[9].x", "l[1][9]"]


@pytest.mark.parametrize("path, value", EXISTING_PATHS)
def test_dots_existing_path_same_through_every_accessor(path, value):
    b = dots_box()
    assert path in b
    assert b[path] == value
    assert b.get(path) == value
    assert b.get(path, "default") == value
    assert b.setdefault(path, "default") == value
    assert b.pop(path) == value


@pytest.mark.parametrize("path, value", EXISTING_PATHS)
def test_dots_existing_path_writes(path, value):
    for write in (
        lambda b: b.__setitem__(path, "new"),
        lambda b: b.update({path: "new"}),
        lambda b: b.update(**{path: "new"}),
        lambda b: b.merge_update({path: "new"}),
        lambda b: b.__ior__({path: "new"}),
    ):
        b = dots_box()
        write(b)
        assert b[path] == "new"
        assert path not in dict.keys(b), "dotted key stored literally"


@pytest.mark.parametrize("path", MISSING_PATHS)
def test_dots_missing_path_reads_agree(path):
    b = dots_box()
    assert path not in b
    assert b.get(path) is None
    assert b.get(path, "default") == "default"


@pytest.mark.parametrize(
    "path",
    MISSING_PATHS,
)
def test_dots_missing_path_pop_default_agrees_with_get(path):
    """Box.pop(key, default) treats an out of range list index like get() and `in` do: as missing."""
    b = dots_box()
    before = b.to_dict()
    assert b.pop(path, "default") == "default"
    assert b.to_dict() == before


def test_dots_failed_delete_has_no_side_effect():
    b = Box(box_dots=True, default_box=True, default_box_create_on_get=True)
    with pytest.raises(KeyError):
        del b["zz.yy"]
    assert b.to_dict() == {}


def test_dots_missing_reads_have_no_side_effect_with_create_on_get():
    b = Box(box_dots=True, default_box=True, default_box_create_on_get=True)
    assert "zz.yy" not in b
    assert b.get("zz.yy", 1) == 1
    assert b.pop("zz.yy", 2) == 2
    assert b.to_dict() == {}


def test_dots_list_paths_in_frozen_box():
    b = dots_box(frozen_box=True)
    assert b["l[0].x"] == 1
    assert "l[0].x" in b


def test_dots_dict_paths_in_frozen_box():
    b = dots_box(frozen_box=True)
    before = b.to_dict()
    assert b["a.b"] == 1
    assert "a.b" in b
    for write in (
        lambda: b.__setitem__("a.b", 2),
        lambda: b.update({"a.b": 2}),
        lambda: b.merge_update({"a.b": 2}),
        lambda: b.__delitem__("a.b"),
        lambda: b.pop("a.b"),
        lambda: b.setdefault("a.new", 1),
    ):
        with pytest.raises(BoxError):
            write()
    assert b.to_dict() == before


def test_dots_comments_do_not_resurrect():
    b = Box({"a": {"b": 1, "c": 2}, "l": [1, 2]}, box_dots=True)
    b.set_comment("a.b", "ab")
    del b["a.b"]
    b["a.b"] = 5
    assert b.get_comment("a.b") is None
    b.set_comment("a.c", "ac")
    b.pop("a.c")
    b.update({"a.c": 5})
    assert b.get_comment("a.c") is None
    b.l.set_comment(1, "l1")
    b.pop("l[1]")
    b.l.append(9)
    assert b.get_comment("l[1]") is None


def test_dots_boxlist_index_forms():
    bl = BoxList([{"a": [{"b": 1}]}, [[2]]], box_dots=True)
    assert bl["[0].a[0].b"] == 1
    assert bl["[1][0][0]"] == 2
    bl["[0].a[0].b"] = 3
    bl["[1][0][0]"] = 4
    assert bl.to_list() == [{"a": [{"b": 3}]}, [[4]]]
    del bl["[0].a[0]"]
    del bl["[1][0][0]"]
    assert bl.to_list() == [{"a": []}, [[]]]


def test_dots_boxlist_rejects_garbage_index():
    bl = BoxList([["a", "b"], ["c", "d"]], box_dots=True)
    with pytest.raises(BoxError):
        bl["[x][1]"]
    with pytest.raises(BoxError):
        del bl["[x][0]"]
    assert bl.to_list() == [["a", "b"], ["c", "d"]]


def test_dots_negative_index_matches_comment_api():
    b = dots_box()
    b.set_comment("l[-1]", "last")
    assert b.get_comment("l[1]") == {"eol": "last"}
    assert b["l[-1]"] == [10, 11]


def test_dots_configbox_case_insensitive_paths():
    c = ConfigBox({"Sect": {"Key": 1, "Other": 2}}, box_dots=True)
    c.Sect.set_comment("Other", "oc")
    assert c["sect.key"] == 1
    assert "SECT.KEY" in c
    assert c.get("sect.key") == 1
    assert c.setdefault("sect.key", 5) == 1
    c.update({"sect.key": 2})
    assert c.Sect.to_dict() == {"key": 2, "Other": 2}
    c.merge_update({"sect.key": 3})
    assert c["Sect.Key"] == 3
    assert c.pop("SECT.key") == 3
    assert c.get_comment("sect.other") == {"eol": "oc"}
    del c["sect.other"]
    assert c.to_dict() == {"Sect": {}}


# --------------------------------------------------------------------------------------------------
# 3. copy / deepcopy / pickle round trips
# --------------------------------------------------------------------------------------------------

ROUND_TRIPS = [
    pytest.param(copy.copy, id="copy"),
    pytest.param(copy.deepcopy, id="deepcopy"),
    pytest.param(lambda x: x.copy(), id="method_copy"),
] + [pytest.param(lambda x, p=p: pickle.loads(pickle.dumps(x, protocol=p)), id=f"pickle_p{p}") for p in (0, 2, 5)]

BOX_CLASSES = [Box, ConfigBox, SBox, DDBox]

BOX_OPTIONS = [
    pytest.param({}, id="plain"),
    pytest.param({"box_dots": True}, id="box_dots"),
    pytest.param({"frozen_box": True}, id="frozen"),
    pytest.param({"box_dots": True, "frozen_box": True}, id="box_dots-frozen"),
    pytest.param({"default_box": True}, id="default_box"),
    pytest.param({"camel_killer_box": True}, id="camel_killer"),
    pytest.param({"box_dots": True, "box_dots_exclude": r"x\.y"}, id="box_dots_exclude"),
]


def _annotated_box(cls, options):
    data = {"Top": 1, "sub": {"k": 2}, "lst": [{"i": 0}, {"i": 1}]}
    build = {k: v for k, v in options.items() if k != "frozen_box"}
    b = cls(data, **build)
    b.set_comment("Top", "top-c", "before")
    b.set_comment(None, "doc")
    b.sub.set_comment("k", "k-c")
    b.lst.set_comment(1, "l1-c")
    b.lst[0].set_comment("i", "i0-c")
    b.lst.set_comment(None, "ldoc", "end")
    if options.get("frozen_box"):
        b = cls(b, **options)
    return b


def _box_state(b):
    return (
        type(b),
        b.to_dict(),
        b.get_comment("Top"),
        b.get_comment(None),
        b.sub.get_comment("k"),
        b.lst.get_comment(1),
        b.lst[0].get_comment("i"),
        b.lst.get_comment(None),
        type(b.sub),
        type(b.lst),
        type(b.lst[0]),
        {k: v for k, v in b._box_config.items() if not k.startswith("__") and k != "box_dots_exclude"},
        b._box_config["box_dots_exclude"] and b._box_config["box_dots_exclude"].pattern,
        b.sub._box_config["box_dots"],
        b.sub._box_config["frozen_box"],
        b.lst.box_options.get("box_dots"),
        b.lst[0]._box_config["box_dots"],
    )


def test_deepcopy_of_frozen_box_is_frozen_all_the_way_down():
    frozen = Box({"sub": {"k": 1}}, frozen_box=True)
    out = copy.deepcopy(frozen)
    with pytest.raises(BoxError):
        out.sub.k = 2
    assert hash(out) == hash(frozen)


@pytest.mark.parametrize("cls", BOX_CLASSES, ids=lambda c: c.__name__)
@pytest.mark.parametrize("options", BOX_OPTIONS)
@pytest.mark.parametrize("round_trip", ROUND_TRIPS)
def test_box_round_trip(cls, options, round_trip):
    b = _annotated_box(cls, options)
    out = round_trip(b)
    assert out is not b
    assert _box_state(out) == _box_state(b)
    if options.get("frozen_box"):
        with pytest.raises(BoxError):
            out.Top = 5
        with pytest.raises(BoxError):
            out.sub.k = 5
    else:
        out.set_comment("Top", "changed")
        assert b.get_comment("Top") == {"before": "top-c"}
    if options.get("box_dots"):
        assert out["lst[0].i"] == 0
        assert out.get_comment("lst[1]") == {"eol": "l1-c"}


@pytest.mark.parametrize("round_trip", ROUND_TRIPS[:2] + ROUND_TRIPS[3:])
def test_nested_boxlist_round_trip(round_trip):
    bl = BoxList([[1, 2], [{"a": [3]}]], box_dots=True)
    bl.set_comment(1, "one")
    bl[0].set_comment(1, "inner")
    bl[1][0].a.set_comment(0, "deep")
    out = round_trip(bl)
    assert out == bl
    assert out.get_comment(1) == {"eol": "one"}
    assert out.get_comment("[0][1]") == {"eol": "inner"}
    assert out.get_comment("[1][0].a[0]") == {"eol": "deep"}
    assert out["[1][0].a[0]"] == 3
    check_converted(out, box_dots=True)


@pytest.mark.parametrize("round_trip", ROUND_TRIPS[:2] + ROUND_TRIPS[3:])
def test_self_referencing_boxlist_round_trip(round_trip):
    bl = BoxList([1])
    bl.append(bl)
    bl.set_comment(0, "c")
    out = round_trip(bl)
    assert out.get_comment(0) == {"eol": "c"}
    if round_trip is not ROUND_TRIPS[0].values[0]:  # copy.copy re-wraps items
        assert out[1] is out


@pytest.mark.parametrize("round_trip", ROUND_TRIPS[:2] + ROUND_TRIPS[3:])
def test_configbox_case_index_after_round_trip(round_trip):
    c = ConfigBox({"Host": "h", "Port": 1})
    _ = c["host"]  # builds the case index that is stored in the box config
    c.set_comment("host", "hc")
    out = round_trip(c)
    out["HOST"] = "z"
    assert out.to_dict() == {"Port": 1, "HOST": "z"}
    assert out.get_comment("host") == {"eol": "hc"}
    assert c.to_dict() == {"Host": "h", "Port": 1}


# ---- fixes of the 8.0.1 audit: frozen lists (tuples), operators ----


def _frozen_yaml_box():
    pytest.importorskip("ruamel.yaml")
    return Box.from_yaml("l:\n- a: 1  # a\n- - 5  # deep\n- 3  # three\n", frozen_box=True)


def test_frozen_list_tuple_comment_api():
    bx = _frozen_yaml_box()
    assert type(bx.l) is not tuple and isinstance(bx.l, tuple)
    assert bx.l.get_comment(2) == {"eol": "three"}
    assert bx.l.get_comment("[-1]") == {"eol": "three"}
    assert bx.l.get_comment("[0].a") == {"eol": "a"}
    assert bx.l.get_comment("[1][0]") == {"eol": "deep"}
    dots = Box.from_yaml("l:\n- - 5  # deep\n", frozen_box=True, box_dots=True)
    assert dots.get_comment("l[0][0]") == {"eol": "deep"}
    assert bx.l.get_comment(None) is None
    for call in (lambda: bx.l.set_comment(0, "x"), lambda: bx.l.del_comment(0)):
        with pytest.raises(BoxError):
            call()
    for bad in (5, "[9]", "x", "[x]", "[2].nope"):
        with pytest.raises(BoxKeyError):
            bx.l.get_comment(bad)
    bx.l._comment_document()["start"] = ["doc"]
    assert bx.l.get_comment() == {"start": "doc"}


def test_frozen_list_tuple_dotted_reads():
    bx = Box({"l": [{"a": 1}, [7, {"b": 2}]]}, box_dots=True, frozen_box=True)
    assert bx["l[0].a"] == 1
    assert bx["l[-1][1].b"] == 2
    assert bx.l["[1]"] == (7, {"b": 2})
    assert bx.l["[0]"].a == 1
    with pytest.raises(BoxTypeError):
        bx.l["[x]"]
    assert bx.l[0].a == 1
    assert "l[1][1].b" in bx
    assert "l[1][1].zz" not in bx
    assert bx.get("l[9].a", "d") == "d"


def test_frozen_list_tuple_copies_keep_comments():
    bx = _frozen_yaml_box()
    for out in (copy.deepcopy(bx), pickle.loads(pickle.dumps(bx)), copy.copy(bx)):
        assert out.l.get_comment(2) == {"eol": "three"}
        assert out.to_yaml() == bx.to_yaml()


def test_frozen_list_comments_follow_box_list_adoption():
    bl = BoxList([{"a": 1}, 2])
    bl.set_comment(1, "two")
    bx = Box({"l": bl}, frozen_box=True)
    assert bx.l.get_comment(1) == {"eol": "two"}
    assert bl.get_comment(1) == {"eol": "two"}  # the source list is left as it was


def test_dots_negative_index_set_and_delete():
    bl = BoxList([1, 2, 3], box_dots=True)
    bl["[-1]"] = 9
    del bl["[-2]"]
    assert bl == [1, 9]


@pytest.mark.parametrize("repeat", [2, 3])
def test_repeat_copies_comments_to_every_repetition(repeat):
    bl = annotated()
    original = len(bl)
    for out in (bl * repeat, repeat * bl):
        assert len(out) == original * repeat
        for index in range(len(out)):
            assert out.get_comment(index) == {"eol": f"c{index % original}"}
    bl *= repeat
    for index in range(len(bl)):
        assert bl.get_comment(index) == {"eol": f"c{index % original}"}


def test_add_copies_comments_of_both_lists_and_document():
    left = annotated()
    left.set_comment(None, "doc")
    right = annotated()
    out = left + right
    assert out.get_comment() == {"start": "doc"}
    for index in range(len(out)):
        assert out.get_comment(index) == {"eol": f"c{index % len(left)}"}
    assert (left + [{"id": NEW}]).get_comment(len(left)) is None


def test_mul_copies_document_comments():
    bl = annotated()
    bl.set_comment(None, "doc")
    assert (bl * 2).get_comment() == {"start": "doc"}
    assert (bl * 0).to_list() == []


def test_frozen_box_converts_a_box_list_inside_a_plain_list():
    bl = BoxList([1])
    bl.set_comment(0, "one")
    bx = Box({"l": [bl]}, frozen_box=True)
    assert bx.l[0].get_comment(0) == {"eol": "one"}


def test_empty_slice_delete_keeps_comments():
    bl = annotated()
    del bl[1:1]
    check_comments(bl, ALL)


def test_from_yaml_comments_inside_an_intact_dict_are_skipped():
    pytest.importorskip("ruamel.yaml")
    bx = Box.from_yaml("a:\n  b: 1  # c\nz: 2  # z\n", box_intact_types=(dict,))
    assert bx.get_comment("z") == {"eol": "z"}
