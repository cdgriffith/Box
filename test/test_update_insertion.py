import pytest

from box import Box, BoxError, ConfigBox
from box.exceptions import BoxWarning


@pytest.mark.parametrize("box_class", [Box, ConfigBox])
@pytest.mark.parametrize("source_type", [dict, list, iter])
def test_update_recasts_each_incoming_value_once(box_class, source_type):
    calls = []

    def cast(value):
        calls.append(value)
        return int(value)

    bx = box_class(box_recast={"batch_size": cast})
    pairs = [("batch_size", "12")]
    assert bx.update(source_type(pairs), batch_size="13") is None
    assert bx.batch_size == 13
    assert calls == ["12", "13"]
    assert pairs == [("batch_size", "12")]


@pytest.mark.parametrize("method", ["__or__", "__ior__"])
def test_union_uses_configured_insertions(method):
    bx = Box({"TimeOut": 10}, camel_killer_box=True, box_recast={"batch_size": int})
    source = {"TimeOut": 30, "batch_size": "12"}
    result = getattr(bx, method)(source)
    assert result.to_dict() == {"time_out": 30, "batch_size": 12}
    assert result.batch_size * 2 == 24
    assert source == {"TimeOut": 30, "batch_size": "12"}


def test_update_rejects_invalid_recast_without_replacing_value():
    bx = Box(batch_size=10, box_recast={"batch_size": int})
    with pytest.raises(ValueError, match="Cannot convert"):
        bx.update(batch_size="invalid")
    assert bx.batch_size == 10


@pytest.mark.parametrize("keep_keys", [False, True])
def test_update_respects_camel_key_policy(keep_keys):
    bx = Box({"TimeOut": 10}, camel_killer_box=True, camel_killer_box_keep_keys=keep_keys)
    bx.update({"TimeOut": 30})
    key = "TimeOut" if keep_keys else "time_out"
    assert bx.to_dict() == {key: 30}
    assert bx.time_out == 30


@pytest.mark.parametrize("policy", ["error", "warn", "ignore"])
def test_update_respects_duplicate_policy(policy):
    bx = Box({"a b": 1}, box_duplicates=policy)
    bx.update({"a b": 2})
    if policy == "error":
        with pytest.raises(BoxError, match="Duplicate"):
            bx.update({"a-b": 3})
        assert bx.to_dict() == {"a b": 2}
    elif policy == "warn":
        with pytest.warns(BoxWarning, match="Duplicate"):
            bx.update({"a-b": 3})
        assert bx.to_dict() == {"a b": 2, "a-b": 3}
    else:
        bx.update({"a-b": 3})
        assert bx.to_dict() == {"a b": 2, "a-b": 3}


def test_update_dispatches_subclass_assignment_and_replaces_nested_values():
    calls = []

    class RecordingBox(Box):
        def __setitem__(self, key, value):
            calls.append(key)
            super().__setitem__(key, value)

    bx = RecordingBox(service={"keep": 1}, box_dots=True)
    calls.clear()
    source = {"service": {"replace": 2}}
    bx.update(source)
    assert calls == ["service", "replace"]
    assert bx.to_dict() == source
    assert bx.service.to_dict() == {"replace": 2}


def test_config_box_update_keeps_latest_case_spelling_and_recasts():
    bx = ConfigBox({"batch_size": 10}, box_recast={"BATCH_SIZE": int})
    bx.update({"BATCH_SIZE": "12"})
    assert bx.to_dict() == {"BATCH_SIZE": 12}
    assert bx.batch_size == 12
