#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import os
import shutil
from pathlib import Path
from test.common import movie_data, tmp_dir

import msgpack
import pytest
from ruamel.yaml import YAML

from box import Box, BoxError, BoxList
from box.converters import _from_toml, _to_json, _to_msgpack, _to_toml, _to_yaml

toml_string = """[movies.Spaceballs]
imdb_stars = 7.1
rating = "PG"
length = 96
Director = "Mel Brooks"
[[movies.Spaceballs.Stars]]
name = "Mel Brooks"
imdb = "nm0000316"
role = "President Skroob"

[[movies.Spaceballs.Stars]]
name = "John Candy"
imdb = "nm0001006"
role = "Barf"
"""


class TestConverters:
    @pytest.fixture(autouse=True)
    def temp_dir_cleanup(self):
        shutil.rmtree(str(tmp_dir), ignore_errors=True)
        try:
            os.mkdir(str(tmp_dir))
        except OSError:
            pass
        yield
        shutil.rmtree(str(tmp_dir), ignore_errors=True)

    def test_to_toml(self):
        formatted = _to_toml(movie_data)
        assert formatted.startswith("[movies.Spaceballs]")

    def test_to_toml_file(self):
        out_file = Path(tmp_dir, "toml_test.tml")
        assert not out_file.exists()
        _to_toml(movie_data, filename=out_file)
        assert out_file.exists()
        assert out_file.read_text().startswith("[movies.Spaceballs]")

    def test_from_toml(self):
        result = _from_toml(toml_string)
        assert result["movies"]["Spaceballs"]["length"] == 96

    def test_from_toml_file(self):
        out_file = Path(tmp_dir, "toml_test.tml")
        assert not out_file.exists()
        out_file.write_text(toml_string)
        result = _from_toml(filename=out_file)
        assert result["movies"]["Spaceballs"]["length"] == 96

    def test_bad_from_toml(self):
        with pytest.raises(BoxError):
            _from_toml()

    def test_to_json(self):
        m_file = os.path.join(tmp_dir, "movie_data")
        movie_string = _to_json(movie_data)
        assert "Rick Moranis" in movie_string
        _to_json(movie_data, filename=m_file)
        assert "Rick Moranis" in open(m_file).read()
        assert json.load(open(m_file)) == json.loads(movie_string)

    @pytest.mark.parametrize("box_type", [Box, BoxList])
    @pytest.mark.parametrize("to_file", [False, True])
    @pytest.mark.parametrize(
        "ensure_ascii, expected",
        [
            (None, '{"café": "你好😀"}'),
            (False, '{"café": "你好😀"}'),
            (True, r'{"caf\u00e9": "\u4f60\u597d\ud83d\ude00"}'),
        ],
    )
    def test_to_json_ensure_ascii(self, box_type, to_file, ensure_ascii, expected, tmp_path):
        data = {"café": "你好😀"}
        if box_type is BoxList:
            data = [data]
            expected = f"[{expected}]"
        value = box_type(data)
        kwargs = {} if ensure_ascii is None else {"ensure_ascii": ensure_ascii}

        if to_file:
            filename = tmp_path / "unicode.json"
            encoding = "ascii" if ensure_ascii else "utf-8"
            assert value.to_json(filename=filename, encoding=encoding, **kwargs) is None
            actual = filename.read_text(encoding=encoding)
        else:
            actual = value.to_json(**kwargs)

        assert actual == expected
        assert json.loads(actual) == data

    @pytest.mark.parametrize("ensure_ascii", [None, False, True])
    def test_to_json_multiline_ensure_ascii(self, ensure_ascii, tmp_path):
        value = BoxList([{"text": "你好"}, {"text": "😀"}])
        kwargs = {} if ensure_ascii is None else {"ensure_ascii": ensure_ascii}
        filename = tmp_path / "unicode.jsonl"

        assert value.to_json(filename=filename, multiline=True, **kwargs) is None

        expected = '{"text": "你好"}\n{"text": "😀"}'
        if ensure_ascii:
            expected = r'{"text": "\u4f60\u597d"}' + "\n" + r'{"text": "\ud83d\ude00"}'
        assert filename.read_text(encoding="utf-8") == expected

    def test_to_json_ensure_ascii_with_other_options(self):
        value = Box(z="你好", a=1)

        assert value.to_json(ensure_ascii=True, sort_keys=True, separators=(",", ":")) == r'{"a":1,"z":"\u4f60\u597d"}'

    def test_to_yaml(self):
        m_file = os.path.join(tmp_dir, "movie_data")
        movie_string = _to_yaml(movie_data)
        assert "Rick Moranis" in movie_string
        _to_yaml(movie_data, filename=m_file)
        assert "Rick Moranis" in open(m_file).read()
        yaml = YAML()
        assert yaml.load(open(m_file)) == yaml.load(movie_string)

    def test_to_msgpack(self):
        m_file = os.path.join(tmp_dir, "movie_data")
        msg_data = _to_msgpack(movie_data)
        assert b"Rick Moranis" in msg_data
        _to_msgpack(movie_data, filename=m_file)
        assert b"Rick Moranis" in open(m_file, "rb").read()
        assert msgpack.unpack(open(m_file, "rb")) == msgpack.unpackb(msg_data)

    def test_to_yaml_ruamel(self):
        movie_string = _to_yaml(movie_data, ruamel_attrs={"width": 12})
        multiline_except = """    - name: \n        Roger\n        Rees\n      imdb: \n        nm0715953\n      role: \n        Sheriff\n        of \n        Rottingham\n    - name: \n        Amy \n        Yasbeck"""
        assert multiline_except in movie_string
