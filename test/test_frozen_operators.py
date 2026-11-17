import pytest

from box import Box, BoxError


@pytest.mark.parametrize("frozen", [False, True])
@pytest.mark.parametrize("reverse", [False, True])
def test_addition_preserves_nested_frozen_state(reverse, frozen):
    incoming = {"nested": {"value": 1}, "rows": [{"value": 2}]}
    original = Box({"existing": {"value": 0}}, frozen_box=frozen)
    result = incoming + original if reverse else original + incoming

    assert result._box_config["frozen_box"] is frozen
    assert result.nested._box_config["frozen_box"] is frozen
    assert result.rows[0]._box_config["frozen_box"] is frozen
    assert original.to_dict() == {"existing": {"value": 0}}
    if frozen:
        assert isinstance(hash(result), int)
        with pytest.raises(BoxError):
            result.nested.value = 3
        with pytest.raises(BoxError):
            result.rows[0].value = 3
        with pytest.raises((BoxError, AttributeError)):
            result.rows.append({"value": 3})
    else:
        result.nested.value = 3
        result.rows[0].value = 3

    assert incoming == {"nested": {"value": 1}, "rows": [{"value": 2}]}


def test_frozen_addition_applies_recast_once_and_restores_freeze_on_error():
    original = Box(frozen_box=True, box_recast={"value": lambda value: int(value) + 1})
    result = original + {"value": 1, "nested": {"value": 2}}
    assert result.value == 2
    with pytest.raises(BoxError):
        result.value = 3
    with pytest.raises(BoxError):
        original.merge_update({"value": "invalid"}, _force_unfrozen=True)
    with pytest.raises(BoxError):
        original.new_value = 1


def test_frozen_addition_replaces_recast_dictionaries_with_box_dots():
    original = Box({"nested": {"old": 1}}, frozen_box=True, box_dots=True, box_recast={"nested": dict})
    result = original + {"nested": (("new", 2),)}
    assert result.nested == {"new": 2}
    with pytest.raises(BoxError):
        result.nested.new = 3


def test_forced_merge_restores_permission_after_reentrant_recast():
    def recast(value):
        original.merge_update({"marker": True}, _force_unfrozen=True)
        return int(value)

    original = Box(frozen_box=True, box_recast={"value": recast})
    original.merge_update({"value": "1", "after": 2}, _force_unfrozen=True)
    assert original.to_dict() == {"marker": True, "value": 1, "after": 2}
    assert "__force_unfrozen" not in original._box_config
    with pytest.raises(BoxError):
        original.after = 3
