#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Test files gathered from json.org and yaml.org

import json
import operator
import os
import pickle
import shutil
from io import StringIO
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from box import Box, BoxError, BoxList
from box.exceptions import BoxTypeError
from box.converters import toml_read_library, toml_write_library
from test.common import test_root, tmp_dir


class TestBoxList:
    @pytest.fixture(autouse=True)
    def temp_dir_cleanup(self):
        shutil.rmtree(str(tmp_dir), ignore_errors=True)
        try:
            os.mkdir(str(tmp_dir))
        except OSError:
            pass
        yield
        shutil.rmtree(str(tmp_dir), ignore_errors=True)

    def test_box_list(self):
        new_list = BoxList({"item": x} for x in range(0, 10))
        new_list.extend([{"item": 22}])
        assert new_list[-1].item == 22
        new_list.append([{"bad_item": 33}])
        assert new_list[-1][0].bad_item == 33
        new_list[-1].append([{"bad_item": 33}])
        assert new_list[-1, -1, 0].bad_item == 33
        bx = Box({0: {1: {2: {3: 3}}}, (0, 1, 2, 3): 4})
        assert bx[0, 1, 2, 3] == 4
        assert repr(new_list).startswith("BoxList(")
        for x in new_list.to_list():
            assert not isinstance(x, (BoxList, Box))
        new_list.insert(0, {"test": 5})
        new_list.insert(1, ["a", "b"])
        new_list.append("x")
        assert new_list[0].test == 5
        assert isinstance(str(new_list), str)
        assert isinstance(new_list[1], BoxList)
        assert not isinstance(new_list.to_list(), BoxList)

    @pytest.mark.parametrize("falsey", [False, True])
    def test_box_list_does_not_require_iterable_truth_value(self, falsey):
        # 2026-10-10: Iterable inputs can be falsey or have no boolean value.
        class Rows:
            def __iter__(self):
                return iter([{"value": 1}])

            def __bool__(self):
                if falsey:
                    return False
                raise ValueError("ambiguous truth value")

        result = BoxList(Rows())
        assert len(result) == 1
        assert result[0].value == 1

    @pytest.mark.parametrize("values", [[], [1], [1, 2], [{"SomeKey": 3}, [4]]])
    def test_extend_self(self, values, monkeypatch):
        data = BoxList(values, camel_killer_box=True)
        expected = data.to_list() * 2
        append = data.append
        remaining = len(data)

        def bounded_append(item):
            nonlocal remaining
            assert remaining > 0, "extend revisited an appended element"
            remaining -= 1
            append(item)

        # Bound the regression test even if extend iterates its growing destination.
        monkeypatch.setattr(data, "append", bounded_append)
        assert data.extend(data) is None
        assert remaining == 0
        assert data.to_list() == expected
        if values and isinstance(values[0], dict):
            assert isinstance(data[2], Box)
            assert data[2].some_key == 3
            assert isinstance(data[3], BoxList)

    def test_extend_generator_preserves_partial_progress(self):
        data = BoxList([0])

        def items():
            yield {"value": 1}
            raise ValueError("unfinished input")

        with pytest.raises(ValueError, match="unfinished input"):
            data.extend(items())
        assert data[0] == 0
        assert isinstance(data[1], Box)
        assert data[1].value == 1

    def test_frozen_list(self):
        bl = BoxList([5, 4, 3], frozen_box=True)
        with pytest.raises(BoxError):
            bl.pop(1)
        with pytest.raises(BoxError):
            bl.remove(4)
        with pytest.raises(BoxError):
            bl.sort()
        with pytest.raises(BoxError):
            bl.reverse()
        with pytest.raises(BoxError):
            bl.append("test")
        with pytest.raises(BoxError):
            bl.extend([4])
        with pytest.raises(BoxError):
            del bl[0]
        with pytest.raises(BoxError):
            bl[0] = 5
        bl2 = BoxList([5, 4, 3])
        del bl2[0]
        assert bl2[0] == 4
        bl2[1] = 4
        assert bl2[1] == 4

    def test_frozen_list_pickle(self):
        for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
            bl = BoxList([5, 4, 3], frozen_box=True)
            dumped = pickle.dumps(bl, protocol=protocol)
            loaded = pickle.loads(dumped)
            assert loaded == [5, 4, 3]
            assert loaded.box_options.get("frozen_box") is True
            with pytest.raises(BoxError):
                loaded.append(2)
            with pytest.raises(BoxError):
                loaded.extend([1])
            with pytest.raises(BoxError):
                loaded.pop(0)
            with pytest.raises(BoxError):
                loaded.remove(5)
            with pytest.raises(BoxError):
                loaded.insert(0, 9)
            with pytest.raises(BoxError):
                loaded.reverse()
            with pytest.raises(BoxError):
                loaded.sort()
            with pytest.raises(BoxError):
                del loaded[0]
            with pytest.raises(BoxError):
                loaded[0] = 99

            empty_bl = BoxList([], frozen_box=True)
            empty_dumped = pickle.dumps(empty_bl, protocol=protocol)
            empty_loaded = pickle.loads(empty_dumped)
            assert empty_loaded == []
            assert empty_loaded.box_options.get("frozen_box") is True
            with pytest.raises(BoxError):
                empty_loaded.append(1)

    def test_box_list_pickle(self):
        for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
            bl = BoxList([1, 2, 3])
            dumped = pickle.dumps(bl, protocol=protocol)
            loaded = pickle.loads(dumped)
            assert loaded == [1, 2, 3]
            assert not loaded.box_options.get("frozen_box")
            loaded.append(4)
            assert loaded == [1, 2, 3, 4]
            loaded[0] = 9
            assert loaded[0] == 9
            del loaded[0]
            assert loaded == [2, 3, 4]

    def test_deepcopy_preserves_box_options(self):
        import copy

        # deepcopy must preserve box_options, matching __copy__ and Box.__deepcopy__
        for options in (
            {"frozen_box": True},
            {"box_dots": True},
            {"default_box": True},
            {"box_intact_types": (dict,)},
        ):
            bl = BoxList([{"a": 1}], **options)
            key = list(options)[0]
            assert copy.copy(bl).box_options.get(key) == options[key]
            assert copy.deepcopy(bl).box_options.get(key) == options[key]

        # a frozen BoxList must stay frozen (immutable + hashable) after deepcopy
        frozen = BoxList([5, 4, 3], frozen_box=True)
        clone = copy.deepcopy(frozen)
        with pytest.raises(BoxError):
            clone.append(1)
        assert hash(clone) == hash(frozen)

    @pytest.mark.parametrize("index", [0, -1, "[0]", "[1]"])
    @pytest.mark.parametrize("container", ["mapping", "sequence"])
    def test_assigned_containers_are_converted(self, index, container):
        class ChildBox(Box):
            pass

        data = BoxList([None], box_dots=True, default_box=True, camel_killer_box=True, box_class=ChildBox)
        value = {"SomeKey": 7} if container == "mapping" else [{"SomeKey": 7}]
        data[index] = value
        assigned = data[1 if index == "[1]" else 0]
        if container == "sequence":
            assert isinstance(assigned, BoxList)
            assigned = assigned[0]
        assert isinstance(assigned, ChildBox)
        assert assigned.some_key == 7
        assert assigned._box_config["box_dots"] is True

    @pytest.mark.parametrize(
        "selection, count", [(slice(1, 2), 2), (slice(None, None, 2), 2), (slice(None, None, -1), 3), (slice(2, 2), 2)]
    )
    def test_slice_assignment_converts_containers(self, selection, count):
        data = BoxList([0, 1, 2], camel_killer_box=True)
        values = [{"SomeKey": number} if number % 2 == 0 else [{"SomeKey": number}] for number in range(count)]
        expected = [0, 1, 2]
        expected[selection] = [
            {"some_key": number} if number % 2 == 0 else [{"some_key": number}] for number in range(count)
        ]
        data[selection] = (value for value in values)
        assert data.to_list() == expected
        for value in data:
            if isinstance(value, dict):
                assert isinstance(value, Box)
                assert value.some_key in range(count)
            elif isinstance(value, list):
                assert isinstance(value, BoxList)
                assert isinstance(value[0], Box)
                assert value[0].some_key in range(count)

    @pytest.mark.parametrize("index", [0, "[0]", slice(None)])
    def test_assignment_respects_intact_types(self, index):
        value = {"SomeKey": 7}
        data = BoxList([None], box_dots=True, box_intact_types=(dict,))
        data[index] = [value] if isinstance(index, slice) else value
        assert data[0] is value

    @pytest.mark.parametrize("index", [0, "[0]", slice(None)])
    def test_frozen_assignment_keeps_contents(self, index):
        data = BoxList([1], frozen_box=True, box_dots=True)
        with pytest.raises(BoxError):
            data[index] = [{"key": 2}] if isinstance(index, slice) else {"key": 2}
        assert data == [1]

    def test_invalid_slice_assignment_keeps_contents(self):
        data = BoxList([0, 1, 2])
        with pytest.raises(ValueError):
            data[::2] = [{"key": 1}]
        assert data == [0, 1, 2]
        with pytest.raises(TypeError):
            data[:] = 3
        assert data == [0, 1, 2]

    @pytest.mark.parametrize("replacement_kind", ["generator", "iterable", "noniterable"])
    def test_zero_step_does_not_consume_replacements(self, replacement_kind):
        consumed = []

        def replacements():
            consumed.append(True)
            yield {"key": 1}

        class Unreadable:
            def __iter__(self):
                raise RuntimeError("replacement must not be read")

        value = {"generator": replacements(), "iterable": Unreadable(), "noniterable": 3}[replacement_kind]
        data = BoxList([0, 1, 2])
        with pytest.raises(ValueError, match="slice step cannot be zero"):
            data[::0] = value
        assert consumed == []
        assert data == [0, 1, 2]

    @pytest.mark.parametrize("bounds", [(0, 4, 1), (3, -5, -2)])
    def test_slice_bounds_are_evaluated_once_before_replacements(self, bounds):
        def assign(list_type):
            events = []

            class Index:
                def __init__(self, name, value):
                    self.name = name
                    self.value = value

                def __index__(self):
                    events.append(self.name)
                    return self.value

            class Replacements:
                def __iter__(self):
                    events.append("iter")
                    return iter([8, 9])

            selection = slice(*(Index(name, value) for name, value in zip(("start", "stop", "step"), bounds)))
            data = list_type([0, 1, 2, 3])
            data[selection] = Replacements()
            return data, events

        expected, expected_events = assign(list)
        actual, actual_events = assign(BoxList)
        assert actual == expected
        assert actual_events == expected_events
        assert sorted(actual_events[:3]) == ["start", "step", "stop"]
        assert actual_events[3:] == ["iter"]

    def test_box_list_to_json(self):
        bl = BoxList([{"item": 1, "CamelBad": 2}])
        assert json.loads(bl.to_json())[0]["item"] == 1

    def test_box_list_from_json(self):
        alist = [{"item": 1}, {"CamelBad": 2}]
        json_list = json.dumps(alist)
        bl = BoxList.from_json(json_list, camel_killer_box=True)
        assert bl[0].item == 1
        assert bl[1].camel_bad == 2

        with pytest.raises(BoxError):
            BoxList.from_json(json.dumps({"a": 2}))

    def test_box_list_to_yaml(self):
        bl = BoxList([{"item": 1, "CamelBad": 2}])
        yaml = YAML()
        assert yaml.load(bl.to_yaml())[0]["item"] == 1

    def test_box_list_from_yaml(self):
        alist = [{"item": 1}, {"CamelBad": 2}]
        yaml = YAML()
        with StringIO() as sio:
            yaml.dump(alist, stream=sio)
            bl = BoxList.from_yaml(sio.getvalue(), camel_killer_box=True)
        assert bl[0].item == 1
        assert bl[1].camel_bad == 2

        with pytest.raises(BoxError):
            BoxList.from_yaml("a: 2")

    def test_box_list_to_toml(self):
        bl = BoxList([{"item": 1, "CamelBad": 2}])
        assert toml_read_library.loads(bl.to_toml(key_name="test"))["test"][0]["item"] == 1
        with pytest.raises(BoxError):
            BoxList.from_toml("[[test]]\nitem = 1\nCamelBad = 2\n\n", key_name="does not exist")

    def test_box_list_from_tml(self):
        alist = [{"item": 1}, {"CamelBad": 2}]
        toml_list = toml_write_library.dumps({"key": alist})
        bl = BoxList.from_toml(toml_string=toml_list, key_name="key", camel_killer_box=True)
        assert bl[0].item == 1
        assert bl[1].camel_bad == 2

        with pytest.raises(BoxError):
            BoxList.from_toml(toml_write_library.dumps({"a": 2}), "a")

        with pytest.raises(BoxError):
            BoxList.from_toml(toml_list, "bad_key")

    def test_intact_types_list(self):
        class MyList(list):
            pass

        bl = BoxList([[1, 2], MyList([3, 4])], box_intact_types=(MyList,))
        assert isinstance(bl[0], BoxList)

    def test_to_csv(self):
        data = BoxList(
            [
                {"Number": 1, "Name": "Chris", "Country": "US"},
                {"Number": 2, "Name": "Sam", "Country": "US"},
                {"Number": 3, "Name": "Jess", "Country": "US"},
                {"Number": 4, "Name": "Frank", "Country": "UK"},
                {"Number": 5, "Name": "Demo", "Country": "CA"},
            ]
        )

        file = Path(tmp_dir, "csv_file.csv")
        data.to_csv(filename=file)
        assert file.read_text().startswith("Number,Name,Country\n1,Chris,US")
        assert data.to_csv().endswith("2,Sam,US\r\n3,Jess,US\r\n4,Frank,UK\r\n5,Demo,CA\r\n")

    def test_from_csv(self):
        bl = BoxList.from_csv(filename=Path(test_root, "data", "csv_file.csv"))
        assert bl[1].Name == "Sam"
        b2 = BoxList.from_csv(
            "Number,Name,Country\r\n1,Chris,US\r\n2,Sam,US\r\n3,Jess,US\r\n4,Frank,UK\r\n5,Demo,CA\r\n"
        )
        assert b2[2].Name == "Jess"

    def test_bad_csv(self):
        data = BoxList([{"test": 1}, {"bad": 2, "data": 3}])
        file = Path(tmp_dir, "csv_file.csv")
        with pytest.raises(BoxError):
            data.to_csv(file)

    def test_toon_strings(self):
        bl = BoxList([{"item": 1, "name": "test"}, {"item": 2, "name": "two"}])
        toon_str = bl.to_toon()
        result = BoxList.from_toon(toon_str)
        assert result[0]["item"] == 1
        assert result[1]["name"] == "two"

    def test_toon_files(self):
        bl = BoxList([{"item": 1, "name": "test"}, {"item": 2, "name": "two"}])
        file = Path(tmp_dir, "toon_file.toon")
        bl.to_toon(filename=file)
        result = BoxList.from_toon(filename=file)
        assert result[0]["item"] == 1

    def test_toon_no_input(self):
        with pytest.raises(BoxError):
            BoxList.from_toon()

    def test_box_list_dots(self):
        data = BoxList(
            [
                {"test": 1},
                {"bad": 2, "data": 3},
                [[[0, -1], [77, 88]], {"inner": "one", "lister": [[{"down": "rabbit"}]]}],
                4,
            ],
            box_dots=True,
        )

        assert data["[0].test"] == 1
        assert data["[1].data"] == 3
        assert data[1].data == 3
        data["[1].data"] = "new_data"
        assert data["[1].data"] == "new_data"
        assert data["[2][0][0][1]"] == -1
        assert data[2][0][0][1] == -1
        data["[2][0][0][1]"] = 1_000_000
        assert data["[2][0][0][1]"] == 1_000_000
        assert data[2][0][0][1] == 1_000_000
        assert data["[2][1].lister[0][0].down"] == "rabbit"
        data["[2][1].lister[0][0].down"] = "hole"
        assert data["[2][1].lister[0][0].down"] == "hole"
        assert data[2][1].lister[0][0].down == "hole"

        db = Box(a=data, box_dots=True)
        keys = db.keys(dotted=True)
        assert keys == [
            "a[0].test",
            "a[1].bad",
            "a[1].data",
            "a[2][0][0][0]",
            "a[2][0][0][1]",
            "a[2][0][1][0]",
            "a[2][0][1][1]",
            "a[2][1].inner",
            "a[2][1].lister[0][0].down",
            "a[3]",
        ]
        for key in keys:
            db[key]

    @pytest.mark.parametrize("key", ["[x]", "[]", "[", "[1x]"])
    @pytest.mark.parametrize("default_box", [False, True])
    def test_box_list_dots_invalid_get(self, key, default_box):
        data = BoxList([{"value": 1}], box_dots=True, default_box=default_box)
        with pytest.raises(BoxError) as error:
            data[key]
        assert "Invalid list index" in str(error.value)
        assert repr(key) in str(error.value)
        assert data.to_list() == [{"value": 1}]

    @pytest.mark.parametrize("key", ["[x]", "[]", "[", "[1x]"])
    @pytest.mark.parametrize("default_box", [False, True])
    def test_box_list_dots_invalid_set(self, key, default_box):
        data = BoxList([{"value": 1}], box_dots=True, default_box=default_box)
        with pytest.raises(BoxError) as error:
            data[key] = 2
        assert "Invalid list index" in str(error.value)
        assert repr(key) in str(error.value)
        assert data.to_list() == [{"value": 1}]

    @pytest.mark.parametrize("key", ["[x]", "[]", "[", "[1x]"])
    @pytest.mark.parametrize("default_box", [False, True])
    def test_box_list_dots_invalid_delete(self, key, default_box):
        data = BoxList([{"value": 1}], box_dots=True, default_box=default_box)
        with pytest.raises(BoxError) as error:
            del data[key]
        assert "Invalid list index" in str(error.value)
        assert repr(key) in str(error.value)
        assert data.to_list() == [{"value": 1}]

    @pytest.mark.parametrize("method, args", [("__getitem__", ()), ("__setitem__", (2,)), ("__delitem__", ())])
    def test_box_list_dots_invalid_nested_index(self, method, args):
        data = BoxList([[1]], box_dots=True)
        with pytest.raises(BoxError) as error:
            getattr(data, method)("[0][x]", *args)
        assert "Invalid list index: '[x]'" in str(error.value)
        assert data.to_list() == [[1]]

    def test_box_list_dots_frozen_invalid_index(self):
        data = BoxList([1], box_dots=True, frozen_box=True)
        with pytest.raises(BoxError, match="Invalid list index"):
            data["[x]"]
        with pytest.raises(BoxError, match="BoxList is frozen"):
            data["[x]"] = 2
        with pytest.raises(BoxError, match="BoxList is frozen"):
            del data["[x]"]
        assert data.to_list() == [1]

    @pytest.mark.parametrize("method, args", [("__getitem__", ()), ("__setitem__", (2,)), ("__delitem__", ())])
    def test_box_list_invalid_index_without_dots(self, method, args):
        data = BoxList([1], box_dots=False)
        with pytest.raises(TypeError, match="list indices must be integers or slices"):
            getattr(data, method)("[x]", *args)
        assert data.to_list() == [1]

    def test_box_list_default_dots(self):
        box_1 = Box(default_box=True, box_dots=True)
        box_1["a[0]"] = 42
        assert box_1.a[0] == 42

        box_1["b[0].c[0].d"] = 42
        assert box_1.b[0].c[0].d == 42

        box_1["c[0][0][0]"] = 42
        assert box_1.c[0][0][0] == 42

        box_2 = Box(default_box=True, box_dots=True)
        box_2["a[4]"] = 42
        assert box_2.a.to_list() == [None, None, None, None, 42]

        box_3 = Box(default_box=True, box_dots=True)
        box_3["a.b[0]"] = 42
        assert box_3.a.b[0] == 42

        # A second dotted write into an existing list element must not discard
        # the keys already written there (regression).
        box_4 = Box(default_box=True, box_dots=True)
        box_4["a[0].x"] = 1
        box_4["a[0].y"] = 2
        assert box_4.a[0].to_dict() == {"x": 1, "y": 2}

        box_5 = Box(default_box=True, box_dots=True)
        box_5["a[0][0].x"] = 1
        box_5["a[0][1].y"] = 2
        assert box_5.a[0].to_list() == [{"x": 1}, {"y": 2}]

        # A scalar already at the position is still overwritten.
        box_6 = Box(default_box=True, box_dots=True)
        box_6["a[0]"] = 5
        box_6["a[0].x"] = 1
        assert box_6.a[0].to_dict() == {"x": 1}

    def test_box_config_propagate(self):
        structure = Box(a=[Box(default_box=False)], default_box=True, box_inherent_settings=True)
        assert structure._box_config["default_box"] is True
        assert structure.a[0]._box_config["default_box"] is True

        base = BoxList([BoxList([Box(default_box=False)])], default_box=True)
        assert base[0].box_options["default_box"] is True

        base2 = BoxList((BoxList([Box()], default_box=False),), default_box=True)
        assert base2[0][0]._box_config["default_box"] is True

        base3 = Box(
            a=[Box(default_box=False)], default_box=True, box_inherent_settings=True, box_intact_types=[Box, BoxList]
        )
        base3.a.append(Box(default_box=False))
        base3.a.append(BoxList(default_box=False))

        for item in base3.a:
            if isinstance(item, Box):
                assert item._box_config["default_box"] is True
            elif isinstance(item, BoxList):
                assert item.box_options["default_box"] is True

    def test_no_recursion_errors(self):
        a = Box({"list_of_dicts": [[{"example1": 1}]]})
        a.list_of_dicts.append([{"example2": 2}])
        assert a["list_of_dicts"][1] == [{"example2": 2}]

    def test_circular_references(self):
        circular_list = []
        circular_list.append(circular_list)
        circular_box = BoxList(circular_list)
        assert circular_box[0] == circular_box


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda value: value.clear(), []),
        (lambda value: operator.iadd(value, [3]), [1, 2, 3]),
        (lambda value: operator.imul(value, 2), [1, 2, 1, 2]),
        (lambda value: operator.imul(value, 0), []),
    ],
)
def test_frozen_list_inplace_mutations(mutate, expected):
    frozen = BoxList([1, 2], frozen_box=True)
    original_hash = hash(frozen)
    with pytest.raises(BoxError, match="BoxList is frozen"):
        mutate(frozen)
    assert frozen == [1, 2]
    assert hash(frozen) == original_hash

    mutable = BoxList([1, 2])
    alias = mutable
    mutate(mutable)
    assert mutable is alias
    assert mutable == expected


@pytest.mark.parametrize("as_iterator", [False, True])
def test_iadd_converts_containers_and_preserves_options(as_iterator):
    class CustomBox(Box):
        pass

    values = [{"someKey": 1}, [{"otherKey": 2}]]
    source = iter(values) if as_iterator else values
    data = BoxList([0], box_class=CustomBox, camel_killer_box=True)
    original = data

    data += source

    assert data is original
    assert data[0] == 0
    assert isinstance(data[1], CustomBox)
    assert data[1].some_key == 1
    assert isinstance(data[2], BoxList)
    assert isinstance(data[2][0], CustomBox)
    assert data[2][0].other_key == 2
    assert data.box_options["box_class"] is CustomBox
    assert data[2].box_options["camel_killer_box"] is True
    assert values == [{"someKey": 1}, [{"otherKey": 2}]]


def test_iadd_respects_intact_types():
    item = {"value": 1}
    data = BoxList(box_intact_types=(dict,))
    data += [item]
    assert data[0] is item


@pytest.mark.parametrize("values", [[], [1, 2], [{"value": 1}]])
def test_iadd_self(values):
    data = BoxList(values)
    original = data
    data += data
    assert data is original
    assert data.to_list() == values + values


def test_iadd_partial_iterator_failure():
    def source():
        yield {"value": 1}
        raise RuntimeError("source failed")

    data = BoxList()
    with pytest.raises(RuntimeError, match="source failed"):
        data += source()
    assert len(data) == 1
    assert isinstance(data[0], Box)
    assert data[0].value == 1


def test_iadd_frozen_does_not_consume_source():
    source = iter([{"value": 1}])
    data = BoxList([0], frozen_box=True)
    with pytest.raises(BoxError, match="BoxList is frozen"):
        data += source
    assert next(source) == {"value": 1}
    assert data == [0]


class TestBoxListOperators:
    def test_add_keeps_boxlist_and_converts(self):
        bl = BoxList([{"a": 1}], box_dots=True)
        result = bl + [{"b": 2}]
        assert isinstance(result, BoxList)
        assert isinstance(result[0], Box)
        assert isinstance(result[1], Box)
        assert result.box_options["box_dots"] is True

    def test_add_two_boxlists(self):
        result = BoxList([{"a": 1}]) + BoxList([{"b": 2}])
        assert isinstance(result, BoxList)
        assert result.to_list() == [{"a": 1}, {"b": 2}]

    def test_add_non_list_raises(self):
        with pytest.raises(BoxTypeError):
            BoxList() + 5

    def test_mul_keeps_boxlist(self):
        bl = BoxList([{"a": 1}], box_dots=True)
        result = bl * 3
        assert isinstance(result, BoxList)
        assert len(result) == 3
        assert result.box_options["box_dots"] is True
        assert result.to_list() == [{"a": 1}] * 3

    def test_mul_non_int_raises(self):
        with pytest.raises(BoxTypeError):
            BoxList() * "x"

    def test_frozen_add_result_is_frozen(self):
        frozen = BoxList([{"a": 1}], frozen_box=True)
        result = frozen + [{"b": 2}]
        assert isinstance(result, BoxList)
        with pytest.raises(BoxError):
            result.append({"c": 3})
