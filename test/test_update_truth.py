import pytest

from box import Box, ConfigBox


class PairsWithoutTruth:
    def __init__(self, pairs):
        self.pairs = pairs

    def __iter__(self):
        return iter(self.pairs)

    def __bool__(self):
        raise ValueError("truth value is ambiguous")


class MappingWithoutTruth(dict):
    def __bool__(self):
        raise ValueError("truth value is ambiguous")


class FalseMapping(dict):
    def __bool__(self):
        return False


@pytest.mark.parametrize("box_class", [Box, ConfigBox])
@pytest.mark.parametrize("method", ["update", "merge_update"])
@pytest.mark.parametrize("source_type", [PairsWithoutTruth, MappingWithoutTruth, FalseMapping])
def test_update_does_not_test_source_truth(box_class, method, source_type):
    pairs = [("service", {"port": 8080})]
    source = source_type(pairs)
    expected = {}
    expected.update(source)
    target = box_class()

    assert getattr(target, method)(source) is None

    assert target.to_dict() == expected
    assert isinstance(target.service, box_class)
    assert list(source) == (pairs if source_type is PairsWithoutTruth else ["service"])


@pytest.mark.parametrize("box_class", [Box, ConfigBox])
@pytest.mark.parametrize("method", ["update", "merge_update"])
@pytest.mark.parametrize("source_type", [PairsWithoutTruth, MappingWithoutTruth, FalseMapping])
def test_update_empty_source_does_not_test_truth(box_class, method, source_type):
    target = box_class(existing=1)

    assert getattr(target, method)(source_type([])) is None

    assert target.to_dict() == {"existing": 1}


@pytest.mark.parametrize("box_class", [Box, ConfigBox])
@pytest.mark.parametrize("method", ["update", "merge_update"])
def test_update_without_source_keeps_existing_none_behavior(box_class, method):
    target = box_class(existing=1)
    assert getattr(target, method)() is None
    assert getattr(target, method)(None) is None
    assert target.to_dict() == {"existing": 1}


@pytest.mark.parametrize("box_class", [Box, ConfigBox])
def test_merge_update_without_source_truth_keeps_nested_values(box_class):
    target = box_class(service={"host": "localhost"})

    target.merge_update(PairsWithoutTruth([("service", {"port": 8080})]))

    assert target.to_dict() == {"service": {"host": "localhost", "port": 8080}}
