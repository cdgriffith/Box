#!/usr/bin/env python
try:
    from test.common import *
except ImportError:
    from .common import *
from pathlib import Path

from box.converters import _to_toml, _from_toml

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
        shutil.rmtree(tmp_dir, ignore_errors=True)
        try:
            os.mkdir(tmp_dir)
        except OSError:
            pass
        yield
        shutil.rmtree(tmp_dir, ignore_errors=True)

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
        assert result['movies']['Spaceballs']['length'] == 96

    def test_from_toml_file(self):
        out_file = Path(tmp_dir, "toml_test.tml")
        assert not out_file.exists()
        out_file.write_text(toml_string)
        result = _from_toml(filename=out_file)
        assert result['movies']['Spaceballs']['length'] == 96

    def test_bad_from_toml(self):
        with pytest.raises(BoxError):
            _from_toml()
