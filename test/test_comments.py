#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Comments on Box keys and BoxList items, read from and written to YAML (#184)."""

import copy
import json
import pickle

import pytest

import box.converters as converters
from box import Box, BoxError, BoxKeyError, BoxList, ConfigBox
from box.exceptions import BoxValueError

pytestmark = pytest.mark.skipif(not converters.ruamel_available, reason="comments need ruamel.yaml")

DOCUMENT = """\
# Service settings
# second line

name: box  # the name
# Where to listen
server:
  host: localhost  # bind address

  port: 8080
# Things
items:
# first
- a  # eol a
- b
last: 1
# end of the document
"""


class TestReadAndWrite:
    def test_round_trip_is_unchanged(self):
        assert Box.from_yaml(DOCUMENT).to_yaml() == DOCUMENT

    def test_comments_are_read(self):
        bx = Box.from_yaml(DOCUMENT)
        assert bx.get_comment(None) == {"start": "Service settings\nsecond line\n", "end": "end of the document"}
        assert bx.get_comment("name") == {"eol": "the name"}
        assert bx.get_comment("server") == {"before": "Where to listen"}
        assert bx.server.get_comment("host") == {"eol": "bind address"}
        assert bx.server.get_comment("port") == {"before": ""}  # the blank line
        assert bx["items"].get_comment(0) == {"before": "first", "eol": "eol a"}
        assert bx["items"].get_comment(1) is None
        assert bx.get_comment("last") is None

    def test_data_is_unaffected(self):
        bx = Box.from_yaml(DOCUMENT)
        plain = {"name": "box", "server": {"host": "localhost", "port": 8080}, "items": ["a", "b"], "last": 1}
        assert bx.to_dict() == plain
        assert json.loads(bx.to_json()) == plain
        assert bx == plain
        assert Box.from_yaml(DOCUMENT) == Box(plain)

    def test_edits_keep_comments_on_their_keys(self):
        bx = Box.from_yaml(DOCUMENT)
        del bx.name
        bx.server.port = 9090
        bx.server.timeout = 30
        bx.new = "x"
        out = bx.to_yaml()
        assert out.startswith("# Service settings\n# second line\n\n# Where to listen\nserver:\n")
        assert "  host: localhost  # bind address\n\n  port: 9090\n  timeout: 30\n" in out
        assert "the name" not in out
        assert out.endswith("last: 1\nnew: x\n# end of the document\n")

    def test_comment_between_key_and_nested_value(self):
        bx = Box.from_yaml("server:\n  # inside\n  host: x\n")
        assert bx.server.get_comment("host") == {"before": "inside"}
        assert bx.to_yaml() == "server:\n  # inside\n  host: x\n"

    def test_nested_list_of_maps(self):
        src = "items:\n- a: 1  # one\n  b: 2\n# second item\n- a: 3\n"
        bx = Box.from_yaml(src)
        assert bx["items"][0].get_comment("a") == {"eol": "one"}
        assert bx["items"].get_comment(1) == {"before": "second item"}
        assert bx.to_yaml() == src

    def test_document_without_comments_has_none(self):
        bx = Box.from_yaml("a: 1\nb: [1, 2]\n")
        assert bx.get_comment(None) is None
        assert bx._box_config.get("__comments") is None

    def test_comment_only_document(self):
        bx = Box.from_yaml("# nothing here\n")
        assert bx == {}

    def test_numeric_keys(self):
        bx = Box.from_yaml("1: one  # first\n2.5: x\n")
        assert bx.get_comment(1) == {"eol": "first"}
        assert bx.to_yaml() == "1: one  # first\n2.5: x\n"

    def test_files(self, tmp_path):
        path = tmp_path / "config.yaml"
        path.write_text(DOCUMENT)
        bx = Box.from_yaml(filename=path)
        bx.set_comment("last", "still last")
        out = tmp_path / "out.yaml"
        assert bx.to_yaml(filename=out) is None
        assert out.read_text() == DOCUMENT.replace("last: 1\n", "last: 1  # still last\n")

    def test_box_list_documents(self):
        src = "# people\n- name: a  # first\n# then\n- name: b\n"
        bl = BoxList.from_yaml(src)
        assert bl.get_comment(None) == {"start": "people"}
        assert bl[0].get_comment("name") == {"eol": "first"}
        assert bl.get_comment(1) == {"before": "then"}
        assert bl.to_yaml() == src


class TestApi:
    def test_set_get_delete(self):
        bx = Box(a=1, b={"c": 2})
        bx.set_comment("a", "eol text")
        bx.set_comment("a", "line one\nline two", position="before")
        bx.b.set_comment("c", "nested")
        assert bx.get_comment("a") == {"eol": "eol text", "before": "line one\nline two"}
        assert bx.to_yaml() == "# line one\n# line two\na: 1  # eol text\nb:\n  c: 2  # nested\n"
        bx.del_comment("a")
        assert bx.get_comment("a") is None
        bx.set_comment("b", "")  # empty text removes that position
        assert bx.get_comment("b") is None

    def test_remove_one_position(self):
        bx = Box(a=1)
        bx.set_comment("a", "x")
        bx.set_comment("a", "y", position="before")
        bx.set_comment("a", None)
        assert bx.get_comment("a") == {"before": "y"}

    def test_hash_prefix_is_optional(self):
        bx = Box(a=1)
        bx.set_comment("a", "# already commented")
        assert bx.get_comment("a") == {"eol": "already commented"}

    def test_document_comments(self):
        bx = Box(a=1)
        bx.set_comment(None, "header\n\nmore")
        bx.set_comment(None, "footer", position="end")
        assert bx.to_yaml() == "# header\n\n# more\na: 1\n# footer\n"
        bx.del_comment()
        assert bx.to_yaml() == "a: 1\n"

    @pytest.mark.parametrize(
        "args, error",
        [
            (("a", "two\nlines"), "single line"),
            (("a", "x", "start"), "position must be one of 'before', 'eol'"),
            ((None, "x", "eol"), "position must be one of 'start', 'end'"),
            (("a", 5), "must be a string"),
        ],
    )
    def test_invalid(self, args, error):
        with pytest.raises(BoxValueError, match=error):
            Box(a=1).set_comment(*args)

    def test_missing_keys(self):
        with pytest.raises(BoxKeyError, match="existing keys"):
            Box().set_comment("missing", "x")
        with pytest.raises(BoxKeyError):
            Box().get_comment("missing")
        with pytest.raises(BoxKeyError, match="existing items"):
            BoxList([1]).set_comment(3, "x")
        with pytest.raises(BoxKeyError):
            Box(a={"b": 1}).set_comment("a.b", "x")  # dotted paths need box_dots

    def test_box_dots_paths(self):
        bx = Box({"a": {"b": 1}, "l": [{"x": 1}, 2]}, box_dots=True)
        bx.set_comment("a.b", "deep")
        bx.set_comment("l[0].x", "in a list")
        bx.set_comment("l[1]", "item")
        assert bx.a.get_comment("b") == {"eol": "deep"}
        assert bx["l"][0].get_comment("x") == {"eol": "in a list"}
        assert bx.get_comment("l[1]") == {"eol": "item"}
        assert bx.get_comment("l[-1]") == {"eol": "item"}

    def test_box_dots_int_segments(self):
        bx = Box({"a": {2: "two"}}, box_dots=True)
        bx.set_comment("a.2", "int key")
        assert bx.a.get_comment(2) == {"eol": "int key"}

    def test_negative_list_index(self):
        bl = BoxList([1, 2, 3])
        bl.set_comment(-1, "last")
        assert bl.get_comment(2) == {"eol": "last"}

    def test_methods_are_protected_names(self):
        for name in ("get_comment", "set_comment", "del_comment"):
            with pytest.raises(BoxKeyError, match="protected"):
                setattr(Box(), name, 1)

    def test_frozen(self):
        bx = Box.from_yaml("a: 1  # kept\n", frozen_box=True)
        assert bx.get_comment("a") == {"eol": "kept"}
        with pytest.raises(BoxError, match="frozen"):
            bx.set_comment("a", "x")
        with pytest.raises(BoxError, match="frozen"):
            bx.del_comment("a")
        bl = BoxList([1], frozen_box=True)
        with pytest.raises(BoxError, match="frozen"):
            bl.set_comment(0, "x")


class TestKeepingCommentsInSync:
    def test_delete_pop_popitem_clear(self):
        bx = Box(a=1, b=2, c=3, d=4)
        for key in "abcd":
            bx.set_comment(key, key)
        del bx["a"]
        bx.pop("b")
        bx.popitem()
        assert bx.get_comment("c") == {"eol": "c"}
        bx["a"] = 1
        assert bx.get_comment("a") is None  # a re-added key starts clean
        bx.clear()
        bx.c = 1
        assert bx.get_comment("c") is None

    def test_overwriting_a_value_keeps_the_comment(self):
        bx = Box(a=1, b={"x": 1})
        bx.set_comment("a", "kept")
        bx.set_comment("b", "kept too")
        bx.a = 2
        bx.b = {"y": 2}
        assert bx.get_comment("a") == {"eol": "kept"}
        assert bx.get_comment("b") == {"eol": "kept too"}

    def test_merge_update_and_update_keep_existing(self):
        bx = Box.from_yaml("a:\n  b: 1  # keep\n")
        bx.merge_update({"a": {"c": 2}})
        bx.update(z=1)
        assert bx.a.get_comment("b") == {"eol": "keep"}

    def test_copy_deepcopy_pickle_and_rebuild(self):
        bx = Box.from_yaml(DOCUMENT)
        for other in (bx.copy(), copy.copy(bx), copy.deepcopy(bx), pickle.loads(pickle.dumps(bx)), Box(bx)):
            assert other.to_yaml() == DOCUMENT
        other = copy.deepcopy(bx)
        other.server.set_comment("host", "changed")
        assert bx.server.get_comment("host") == {"eol": "bind address"}

    def test_moving_a_subtree(self):
        bx = Box.from_yaml(DOCUMENT)
        target = Box()
        target.settings = bx.server
        assert target.settings.get_comment("host") == {"eol": "bind address"}

    def test_box_list_index_changes(self):
        bl = BoxList(["a", "b", "c", "d"])
        for index in range(4):
            bl.set_comment(index, "abcd"[index])

        def comments():
            return [(bl.get_comment(i) or {}).get("eol") for i in range(len(bl))]

        bl.insert(1, "new")
        assert comments() == ["a", None, "b", "c", "d"]
        bl.pop(1)
        assert comments() == ["a", "b", "c", "d"]
        del bl[0]
        assert comments() == ["b", "c", "d"]
        bl.remove("c")
        assert comments() == ["b", "d"]
        bl.insert(-1, "x")
        assert bl == ["b", "x", "d"] and comments() == ["b", None, "d"]
        bl.reverse()
        assert comments() == ["d", None, "b"]
        bl.sort()
        assert bl == ["b", "d", "x"] and comments() == ["b", "d", None]
        bl.sort(key=lambda v: v == "b", reverse=True)
        assert bl == ["b", "d", "x"] and comments() == ["b", "d", None]
        bl.append("e")
        bl += ["f"]
        assert comments() == ["b", "d", None, None, None]
        bl.pop()
        bl[0:2] = ["y"]  # slice writes drop the list's item comments
        assert comments() == [None, None, None]
        bl.set_comment(0, "again")
        bl.clear()
        bl.append(1)
        assert bl.get_comment(0) is None

    def test_box_list_copies_and_pickles(self):
        bl = BoxList.from_yaml("- 1  # one\n- 2\n")
        for other in (copy.copy(bl), copy.deepcopy(bl), pickle.loads(pickle.dumps(bl)), BoxList(bl)):
            assert other.get_comment(0) == {"eol": "one"}

    def test_config_box_any_case_and_latest_write(self):
        cb = ConfigBox.from_yaml("Host: x  # the host\n")
        assert cb.get_comment("host") == {"eol": "the host"}
        cb.set_comment("HOST", "renamed later")
        cb["host"] = "y"  # the latest spelling wins, the comment goes with it
        assert cb.to_yaml() == "host: y  # renamed later\n"

    def test_camel_killer_keys(self):
        bx = Box.from_yaml("loadBalancer: x  # lb\n", camel_killer_box=True)
        assert bx.get_comment("load_balancer") == {"eol": "lb"}
        assert bx.get_comment("loadBalancer") == {"eol": "lb"}
        assert bx.to_yaml() == "load_balancer: x  # lb\n"

    def test_box_dots_split_keys_lose_comments_safely(self):
        bx = Box.from_yaml("a.b: 1  # dotted\n", box_dots=True, default_box=True)
        assert bx.to_dict() == {"a": {"b": 1}}
        assert bx.to_yaml() == "a:\n  b: 1\n"


class TestOtherBackends:
    def test_safe_dumper_ignores_comments(self):
        bx = Box.from_yaml(DOCUMENT)
        assert "#" not in bx.to_yaml(ruamel_typ="safe")

    def test_safe_loader_reads_none(self):
        bx = Box.from_yaml(DOCUMENT, ruamel_typ="safe")
        assert bx.get_comment(None) is None and bx.get_comment("name") is None

    def test_pyyaml(self, monkeypatch):
        if not converters.pyyaml_available:
            pytest.skip("PyYAML is not installed")
        monkeypatch.setattr(converters, "ruamel_available", False)
        bx = Box.from_yaml(DOCUMENT)
        assert bx.get_comment("name") is None
        bx.set_comment("name", "ignored by PyYAML")
        assert "#" not in bx.to_yaml()

    def test_output_without_comments_is_unchanged(self):
        data = {"z": 1, "a": {"b": [1, {"c": 2}]}}
        assert Box(data).to_yaml() == converters._to_yaml(data)
        assert BoxList([data]).to_yaml() == converters._to_yaml([data])


class TestEdgeCases:
    def test_missing_keys_and_paths(self):
        with pytest.raises(BoxKeyError):
            Box(camel_killer_box=True).set_comment("missingKey", "x")
        dotted = Box({"a": 1, "l": [1]}, box_dots=True)
        for key in ("nope.x", "a.x", "l[0].x", "l[5]", "l[x]", "l.x"):
            with pytest.raises(BoxKeyError):
                dotted.set_comment(key, "x")
        with pytest.raises(BoxKeyError):
            BoxList([1]).set_comment(1.5, "x")

    def test_delete_without_comments(self):
        bx = Box(a=1)
        bx.del_comment("a")
        bl = BoxList([1])
        bl.del_comment(0)
        bl.set_comment(0, "x")
        bl.del_comment(0)
        assert bl.get_comment(0) is None

    def test_box_list_document_and_positions(self):
        bl = BoxList([1, 2])
        bl.set_comment(None, "top")
        bl.set_comment(0, "above", position="before")
        bl.set_comment(0, None, position="before")
        assert bl.get_comment(0) is None
        assert copy.copy(bl).get_comment(None) == {"start": "top"}
        bl.del_comment()
        assert bl.get_comment(None) is None

    def test_box_list_without_comments_keeps_working(self):
        bl = BoxList([3, 1, 2])
        bl.sort()
        bl.reverse()
        del bl[0:1]
        assert bl == [2, 1]

    def test_dotted_list_deletion_keeps_surviving_comments(self):
        values = BoxList.from_yaml("- first  # first comment\n- second  # second comment\n", box_dots=True)
        del values["[0]"]
        assert values.to_yaml() == "- second  # second comment\n"

    def test_sort_with_comments_evaluates_keys_once(self):
        values = BoxList.from_yaml("- z  # Z\n- a  # A\n")
        ranks = {"z": 2, "a": 1}
        assert values.sort(key=ranks.pop) is None
        assert ranks == {}
        assert values.to_yaml() == "- a  # A\n- z  # Z\n"

    def test_slice_delete_drops_item_comments(self):
        bl = BoxList([1, 2, 3])
        bl.set_comment(2, "x")
        del bl[0:1]
        assert bl.get_comment(1) is None

    def test_empty_comment_and_missing_final_newline(self):
        bx = Box.from_yaml("a: 1 #\nb: 2  # two\n# end")
        assert bx.get_comment("a") is None
        assert bx.get_comment("b") == {"eol": "two"}
        assert bx.get_comment(None) == {"end": "end"}

    def test_frozen_lists_skip_item_comments(self):
        bx = Box.from_yaml("l:\n- a: 1  # in a frozen list\n", frozen_box=True)
        assert bx.to_dict() == {"l": ({"a": 1},)}  # frozen boxes store lists as tuples

    def test_box_dots_split_parent_key(self):
        bx = Box.from_yaml("a.b:\n  c: 1  # c\n", box_dots=True, default_box=True)
        assert bx.to_dict() == {"a": {"b": {"c": 1}}}

    def test_self_reference(self):
        bx = Box(a=1)
        dict.__setitem__(bx, "me", bx)  # Box itself never builds cycles, guard against them anyway
        assert bx.to_yaml() == "&id001\na: 1\nme: *id001\n"
        bx.set_comment("a", "x")
        assert "a: 1  # x" in bx.to_yaml()


class TestCommentTextIsNeverYaml:
    @pytest.mark.parametrize("brk", ["\n", "\r", "\r\n", "\x85", "\u2028", "\u2029"])
    def test_end_of_line_comments_reject_every_line_break(self, brk):
        with pytest.raises(BoxValueError, match="single line"):
            Box(a=1).set_comment("a", f"x{brk}injected: 1")

    @pytest.mark.parametrize("brk", ["\n", "\r", "\r\n", "\x85", "\u2028", "\u2029"])
    @pytest.mark.parametrize("key, position", [("a", "before"), (None, "start"), (None, "end")])
    def test_multi_line_comments_stay_comments(self, brk, key, position):
        bx = Box(a=1)
        bx.set_comment(key, f"one{brk}injected: 1", position=position)
        out = bx.to_yaml()
        assert Box.from_yaml(out).to_dict() == {"a": 1}, out
        assert "# injected: 1" in out

    @pytest.mark.parametrize("char", ["\x00", "\x08", "\x0b", "\x0c", "\x1b", "\x7f"])
    def test_control_characters_are_rejected(self, char):
        with pytest.raises(BoxValueError, match="control characters"):
            Box(a=1).set_comment("a", f"x{char}y", position="before")

    def test_tabs_are_fine(self):
        bx = Box(a=1)
        bx.set_comment("a", "x\ty")
        assert Box.from_yaml(bx.to_yaml()).get_comment("a") == {"eol": "x\ty"}


@pytest.mark.parametrize("count", [0, -1, -3])
def test_inplace_repetition_drops_comments_of_removed_items(count):
    values = BoxList.from_yaml("# list heading\n- old  # obsolete explanation\n")
    original = values
    values *= count
    assert values is original
    assert values == []
    values.append("new")
    assert values.get_comment(0) is None
    assert values.get_comment() == {"start": "list heading"}
    assert values.to_yaml() == "# list heading\n- new\n"


@pytest.mark.parametrize("count", [1, 2])
def test_inplace_repetition_keeps_surviving_item_comments(count):
    values = BoxList.from_yaml("- old  # explanation\n")
    original = values
    values *= count
    assert values is original
    assert values == ["old"] * count
    assert values.get_comment(0) == {"eol": "explanation"}


def test_inplace_repetition_keeps_comments_on_false_valued_subclass():
    class FalseBoxList(BoxList):
        def __bool__(self):
            return False

    values = FalseBoxList(["old"])
    values.set_comment(0, "explanation")
    values *= 1
    assert values.get_comment(0) == {"eol": "explanation"}
