#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ConfigBox string keys are case-insensitive and the latest write wins (#314)."""

import copy
import pickle
import time

import pytest

from box import Box, BoxError, ConfigBox


class TestConfigBoxCaseInsensitive:
    @pytest.mark.parametrize("outer", [list, iter])
    def test_merge_update_one_shot_pairs(self, outer):
        cb = ConfigBox({"Host": {"port": 80}})
        pairs = outer([iter(("host", {"name": "localhost"})), iter(("timeout", 30))])
        cb.merge_update(pairs)
        assert cb.to_dict() == {"host": {"port": 80, "name": "localhost"}, "timeout": 30}
        assert list(cb) == ["host", "timeout"]
        assert cb.HOST.port == 80

    def test_lookup_any_case(self):
        cb = ConfigBox({"HOST": "localhost", "ServerPort": 8080})
        assert cb["host"] == cb["Host"] == cb.host == cb.HOST == "localhost"
        assert cb.serverport == cb["SERVERPORT"] == 8080
        assert "host" in cb and "serverPORT" in cb and "nope" not in cb
        assert cb.get("host") == "localhost"
        assert cb.get("nope", 5) == 5

    def test_transforms_any_case(self):
        cb = ConfigBox({"Flag": "yes", "Count": "5", "Ratio": "1.5", "Items": "a, b"})
        assert cb.bool("flag") is True
        assert cb.int("COUNT") == 5
        assert cb.getfloat("ratio") == 1.5
        assert cb.list("items") == ["a", "b"]

    def test_latest_write_wins_on_construction(self):
        assert ConfigBox({"Foo": 1, "foo": 2}).to_dict() == {"foo": 2}
        assert ConfigBox({"Foo": 1, "foo": 2, "FOO": 3}).to_dict() == {"FOO": 3}
        assert ConfigBox(A=1, a=2).to_dict() == {"a": 2}
        assert ConfigBox.from_json('{"Foo": 1, "foo": 2}').to_dict() == {"foo": 2}

    def test_latest_write_wins_on_assignment(self):
        cb = ConfigBox({"host": "a", "port": 1})
        cb["HOST"] = "b"
        assert cb.to_dict() == {"port": 1, "HOST": "b"}
        cb.Host = "c"
        assert cb.to_dict() == {"port": 1, "Host": "c"}
        cb.Host = "d"  # same spelling replaces in place
        assert list(cb.keys()) == ["port", "Host"]
        assert cb.host == "d"

    def test_update_and_merge_update_agree(self):
        for method in ("update", "merge_update"):
            cb = ConfigBox({"Host": "h", "port": 1})
            getattr(cb, method)({"HOST": "u"})
            assert cb.to_dict() == {"port": 1, "HOST": "u"}, method
            getattr(cb, method)(host="v")
            assert cb.to_dict() == {"port": 1, "host": "v"}, method
            getattr(cb, method)([("Host", "w")])
            assert cb.to_dict() == {"port": 1, "Host": "w"}, method
        cb = ConfigBox()
        cb.update({"a": 1, "A": 2})
        assert cb.to_dict() == {"A": 2}

    def test_merge_update_merges_nested_and_takes_spelling(self):
        cb = ConfigBox({"Server": {"host": "h", "port": 1}})
        cb.merge_update({"SERVER": {"PORT": 2}})
        assert cb.to_dict() == {"SERVER": {"host": "h", "PORT": 2}}
        assert cb.server.port == 2
        cb.merge_update(iter([("server", {"x": 1})]))  # one-shot iterators are only consumed once
        assert cb.to_dict() == {"server": {"host": "h", "PORT": 2, "x": 1}}

    def test_union_right_side_wins(self):
        assert (ConfigBox({"Foo": 1, "bar": 2}) | {"FOO": 3}).to_dict() == {"bar": 2, "FOO": 3}

    def test_delete_and_pop_any_case(self):
        cb = ConfigBox({"HOST": 1, "Port": 2, "user": 3})
        del cb["host"]
        assert cb.pop("PORT") == 2
        del cb.USER
        assert cb.to_dict() == {}
        assert "host" not in cb
        with pytest.raises(KeyError):
            del cb["host"]

    def test_setdefault_keeps_existing(self):
        cb = ConfigBox({"Host": "h"})
        assert cb.setdefault("host", "x") == "h"
        assert cb.to_dict() == {"Host": "h"}

    def test_popitem_and_clear_keep_index_in_sync(self):
        cb = ConfigBox({"A": 1, "B": 2})
        assert cb.popitem() == ("B", 2)
        assert "b" not in cb and "a" in cb
        cb.clear()
        assert "a" not in cb
        cb["A"] = 1
        assert cb.a == 1

    @pytest.mark.parametrize("key", [1, None, (1, 2), 1.5, b"Bytes"])
    def test_non_string_keys_match_exactly(self, key):
        cb = ConfigBox({key: "v"})
        assert cb[key] == "v"
        assert key in cb
        assert 999 not in cb
        del cb[key]
        assert key not in cb
        assert b"bytes" not in ConfigBox({b"Bytes": 1})

    def test_missing_keys_raise_keyerror(self):
        with pytest.raises(KeyError):
            ConfigBox({"a": 1})[5]
        with pytest.raises(KeyError):
            ConfigBox({"a": 1})["b"]
        with pytest.raises(AttributeError):
            ConfigBox({"a": 1}).b

    def test_unhashable_in_raises_typeerror_like_dict(self):
        with pytest.raises(TypeError):
            [] in ConfigBox({"a": 1})

    def test_mixed_str_and_non_str_keys(self):
        cb = ConfigBox({1: "one", "One": "word"})
        cb["ONE"] = "WORD"
        assert cb.to_dict() == {1: "one", "ONE": "WORD"}

    def test_box_duplicates_error_still_raises(self):
        with pytest.raises(BoxError):
            ConfigBox({"a_b": 1, "a b": 2}, box_duplicates="error")
        # A different case is replaced rather than reported as a duplicate
        assert ConfigBox({"A_B": 1, "a_b": 2}, box_duplicates="error").to_dict() == {"a_b": 2}

    def test_conversion_alias_follows_new_spelling(self):
        cb = ConfigBox({"My Key": 1})
        assert cb.My_Key == 1
        cb["my key"] = 2
        assert cb.my_key == 2
        assert cb.to_dict() == {"my key": 2}

    def test_nested_boxes_are_case_insensitive(self):
        cb = ConfigBox({"Database": {"Host": "h"}})
        assert isinstance(cb.database, ConfigBox)
        assert cb.DATABASE.host == "h"
        cb.database.HOST = "x"
        assert cb.to_dict() == {"Database": {"HOST": "x"}}

    def test_box_dots_any_case(self):
        cb = ConfigBox({"Server": {"Host": "h", "Ports": [1, 2]}}, box_dots=True)
        assert cb["server.host"] == "h"
        assert cb["SERVER.ports[1]"] == 2
        assert "server.HOST" in cb
        cb["server.host"] = "x"
        assert cb.to_dict() == {"Server": {"host": "x", "Ports": [1, 2]}}
        del cb["SERVER.HOST"]
        assert cb.to_dict() == {"Server": {"Ports": [1, 2]}}

    def test_box_dots_literal_dotted_key(self):
        cb = ConfigBox({"A.B": 1}, box_dots=True, box_dots_exclude=r"(?i)a\.b")
        assert cb["a.b"] == 1
        cb["a.b"] = 2
        assert cb.to_dict() == {"a.b": 2}

    def test_default_box_any_case(self):
        cb = ConfigBox({"Host": "h"}, default_box=True)
        assert cb.host == "h"
        cb.HOST = "x"
        assert cb.to_dict() == {"HOST": "x"}

    def test_default_box_created_key_found_any_case(self):
        cb = ConfigBox(default_box=True)
        cb.Section.Key = 1
        assert cb.section.key == 1
        assert cb.to_dict() == {"Section": {"Key": 1}}

    def test_stale_ephemeral_child_is_not_attached(self):
        cb = ConfigBox(default_box=True, default_box_create_on_get=False)
        child = cb.Section
        cb["SECTION"] = {"a": 1}
        child.b = 2
        assert cb.to_dict() == {"SECTION": {"a": 1}}

    def test_frozen(self):
        cb = ConfigBox({"Host": "h", "host": "x"}, frozen_box=True)
        assert cb.to_dict() == {"host": "x"}
        assert cb.HOST == "x"
        for action in (
            lambda: cb.__setitem__("HOST", 1),
            lambda: cb.update(HOST=1),
            lambda: cb.merge_update(HOST=1),
            lambda: cb.__delitem__("HOST"),
        ):
            with pytest.raises(BoxError):
                action()
        assert cb.to_dict() == {"host": "x"}

    def test_copy_pickle_round_trip(self):
        cb = ConfigBox({"Host": "h", "Nested": {"Key": 1}})
        for other in (cb.copy(), copy.deepcopy(cb), pickle.loads(pickle.dumps(cb))):
            assert type(other) is ConfigBox
            assert other.host == "h" and other.nested.key == 1
            other["HOST"] = "x"
            assert other.to_dict() == {"Nested": {"Key": 1}, "HOST": "x"}
        assert cb.to_dict() == {"Host": "h", "Nested": {"Key": 1}}

    def test_plain_box_unchanged(self):
        bx = Box({"Foo": 1, "foo": 2})
        assert bx.to_dict() == {"Foo": 1, "foo": 2}
        with pytest.raises(KeyError):
            bx["FOO"]

    def test_index_survives_direct_dict_writes(self):
        cb = ConfigBox({"a": 1})
        assert "A" in cb
        dict.__setitem__(cb, "New", 2)  # bypasses ConfigBox, as some Box internals do
        assert cb.new == 2

    def test_large_box_misses_and_construction_are_fast(self):
        start = time.perf_counter()
        cb = ConfigBox({f"Key{i}": i for i in range(20000)})
        built = time.perf_counter() - start
        start = time.perf_counter()
        for _ in range(2000):
            assert "nope" not in cb
            assert cb.get("KEY19999") == 19999
        lookups = time.perf_counter() - start
        # Generous limits: a scan of every key per miss takes seconds here, quadratic construction minutes
        assert built < 5
        assert lookups < 1
