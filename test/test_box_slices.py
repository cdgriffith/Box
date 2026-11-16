"""Slicing creates an independent Box with the source's options."""

import sys

import pytest

from box import Box, BoxError, ConfigBox


@pytest.mark.parametrize("box_class", [Box, ConfigBox])
@pytest.mark.parametrize("frozen", [False, True])
@pytest.mark.parametrize("selection", [slice(None), slice(1, 3), slice(None, None, -1), slice(2, 2)])
def test_slice_preserves_order_and_frozen_state(box_class, frozen, selection):
    source = box_class(first=1, nested={"value": 2}, rows=[{"value": 3}], frozen_box=frozen)
    expected = list(source.items())[selection]
    source_hash = hash(source) if frozen else None

    result = source[selection]

    assert type(result) is box_class
    assert list(result.items()) == expected
    assert result is not source
    if frozen:
        with pytest.raises(BoxError, match="frozen"):
            result.extra = 4
        if "nested" in result:
            with pytest.raises(BoxError, match="frozen"):
                result.nested.value = 4
        if "rows" in result:
            with pytest.raises(BoxError, match="frozen"):
                result.rows[0].value = 4
        assert isinstance(hash(result), int)
        assert hash(source) == source_hash
    else:
        result.extra = 4
        assert "extra" not in source
    assert list(source) == ["first", "nested", "rows"]


@pytest.mark.parametrize("frozen", [False, True])
def test_slice_keeps_explicit_none_with_default_box(frozen):
    source = Box([("value", None)], default_box=True, frozen_box=frozen)

    result = source[:]

    assert list(result.items()) == [("value", None)]
    assert isinstance(result.missing, Box)
    assert list(result) == ["value"]


@pytest.mark.parametrize("frozen", [False, True])
def test_slice_recasts_selected_values_once(frozen):
    calls = []

    def recast(value):
        calls.append(value)
        return value + "!"

    source = Box(tag="value", omitted=1, frozen_box=frozen, box_recast={"tag": recast})
    calls.clear()

    result = source[:1]

    assert result.tag == "value!!"
    assert calls == ["value!"]
    assert source.tag == "value!"


@pytest.mark.parametrize("frozen", [False, True])
def test_slice_keeps_dotted_options(frozen):
    source = Box(nested={"value": 1}, frozen_box=frozen, box_dots=True)

    result = source[:]

    assert result["nested.value"] == 1


@pytest.mark.skipif(sys.version_info < (3, 12), reason="slice keys require Python 3.12")
def test_stored_slice_key_still_returns_its_value():
    key = slice(0, 1)
    source = Box({key: "stored"}, frozen_box=True)

    assert source[key] == "stored"
