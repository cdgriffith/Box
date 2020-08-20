#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import os
import shutil
from pathlib import Path
from test.common import movie_data, tmp_dir

import msgpack
import pytest
import ruamel.yaml as yaml

from box import BoxError
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

    def test_to_yaml(self):
        m_file = os.path.join(tmp_dir, "movie_data")
        movie_string = _to_yaml(movie_data)
        assert "Rick Moranis" in movie_string
        _to_yaml(movie_data, filename=m_file)
        assert "Rick Moranis" in open(m_file).read()
        assert yaml.load(open(m_file), Loader=yaml.SafeLoader) == yaml.load(movie_string, Loader=yaml.SafeLoader)

    def test_to_msgpack(self):
        m_file = os.path.join(tmp_dir, "movie_data")
        msg_data = _to_msgpack(movie_data)
        assert b"Rick Moranis" in msg_data
        _to_msgpack(movie_data, filename=m_file)
        assert b"Rick Moranis" in open(m_file, "rb").read()
        assert msgpack.unpack(open(m_file, "rb")) == msgpack.unpackb(msg_data)
