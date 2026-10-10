#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json

import pytest

from box import BoxList


@pytest.mark.parametrize("data", [[], [{"a": 1}], [{"a": 1}, {"b": 2}], [None, False, 3, "café\u2028text"]])
def test_multiline_string_output_matches_file(tmp_path, data):
    values = BoxList(data)
    path = tmp_path / "values.jsonl"
    values.to_json(filename=path, multiline=True)

    result = values.to_json(multiline=True)

    assert result == path.read_text(encoding="utf-8")
    assert result == "\n".join(json.dumps(value, ensure_ascii=False) for value in data)


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_multiline_string_input_matches_file(tmp_path, newline):
    text = newline.join(["# comment", "", '{"FirstKey": 1}', "   ", ' {"SecondKey": "café\u2028text"} ', "# end"])
    path = tmp_path / "values.jsonl"
    path.write_bytes(text.encode("utf-8"))

    result = BoxList.from_json(text, multiline=True, camel_killer_box=True)
    from_file = BoxList.from_json(filename=path, multiline=True, camel_killer_box=True)

    assert result == from_file
    assert result[0].first_key == 1
    assert result[1].second_key == "café\u2028text"


@pytest.mark.parametrize("text", ["", "\n \r\n", "# comment\n  # another\n"])
def test_empty_multiline_string_input(text):
    assert BoxList.from_json(text, multiline=True) == []


def test_multiline_string_json_options():
    values = BoxList([{"b": 2, "a": 1}, {"c": 3}])
    text = values.to_json(multiline=True, sort_keys=True, separators=(",", ":"))

    assert text == '{"a":1,"b":2}\n{"c":3}'
    assert BoxList.from_json(text, multiline=True, parse_int=str) == [{"a": "1", "b": "2"}, {"c": "3"}]


@pytest.mark.parametrize("text", ['{"a": 1}\nnot json', '{"a": 1}\n{"b":'])
def test_multiline_string_rejects_invalid_json(text):
    with pytest.raises(json.JSONDecodeError):
        BoxList.from_json(text, multiline=True)


def test_multiple_objects_require_multiline():
    with pytest.raises(json.JSONDecodeError):
        BoxList.from_json('{"a": 1}\n{"b": 2}')


def test_default_json_array_behavior():
    values = BoxList([{"a": 1}, {"b": 2}])
    assert json.loads(values.to_json()) == values.to_list()
    assert BoxList.from_json(values.to_json()) == values
