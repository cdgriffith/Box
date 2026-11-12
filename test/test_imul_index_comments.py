"""In-place repetition must normalize index-protocol counts before mutation."""

import operator

import pytest

from box import BoxError, BoxList


class IndexOnce:
    def __init__(self, value):
        self.value = value
        self.calls = 0

    def __index__(self):
        self.calls += 1
        if self.calls > 1:
            raise AssertionError("count evaluated twice")
        return self.value


@pytest.mark.parametrize("count", [2, 1, 0, -2])
@pytest.mark.parametrize("comments", [True, False])
def test_imul_index_count_normalized_once(count, comments):
    values = BoxList(["a", "b"])
    if comments:
        values.set_comment(0, "first")
        values.set_comment(1, "second")
    key = IndexOnce(count)
    result = operator.imul(values, key)
    assert result is values
    assert list(values) == ["a", "b"] * count
    assert key.calls == 1
    if comments:
        for index in range(max(count, 0) * 2):
            assert values.get_comment(index) == {"eol": "first" if index % 2 == 0 else "second"}
        if count <= 0:
            assert not values.__dict__.get("_box_comments")


def test_imul_invalid_index_preserves_data_and_comments():
    class InvalidIndex:
        def __index__(self):
            raise ValueError("bad count")

    values = BoxList(["a", "b"])
    values.set_comment(1, "second")
    with pytest.raises(ValueError, match="bad count"):
        operator.imul(values, InvalidIndex())
    assert list(values) == ["a", "b"]
    assert values.get_comment(1) == {"eol": "second"}


def test_imul_frozen_refuses_before_index_conversion():
    values = BoxList(["a"], frozen_box=True)
    key = IndexOnce(2)
    with pytest.raises(BoxError):
        operator.imul(values, key)
    assert key.calls == 0
    assert list(values) == ["a"]
