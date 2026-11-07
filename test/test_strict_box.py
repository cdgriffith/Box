import copy
import pickle
import re
from collections import defaultdict
from collections.abc import MutableMapping

import pytest

from box import Box, BoxError, BoxKeyError, ConfigBox, StrictBox


def test_existing_fields_remain_mutable():
    settings = StrictBox(host="localhost", port=8000, optional=None, tags=[])
    settings.port = 8080
    settings.optional = "set"
    settings.tags.append("local")
    with pytest.raises(BoxKeyError, match="Cannot create field"):
        settings.prot = 8080
    assert settings.to_dict() == {
        "host": "localhost",
        "port": 8080,
        "optional": "set",
        "tags": ["local"],
    }


@pytest.mark.parametrize("method", ["item", "update", "merge_update", "setdefault", "union"])
def test_dictionary_operations_can_define_fields(method):
    settings = StrictBox()
    if method == "item":
        settings["name"] = "app"
    elif method == "update":
        settings.update(name="app")
    elif method == "merge_update":
        settings.merge_update(name="app")
    elif method == "setdefault":
        settings.setdefault("name", "app")
    else:
        settings |= {"name": "app"}
    settings.name = "renamed"
    assert settings.name == "renamed"


def test_nested_boxes_and_list_members():
    settings = StrictBox(server={"port": 8000}, workers=[{"name": "first"}])
    settings.server.port = 8080
    settings.workers[0].name = "changed"
    for nested in [settings.server, settings.workers[0]]:
        assert isinstance(nested, StrictBox)
        with pytest.raises(BoxKeyError):
            nested.unknown = True
    settings.server = {"host": "localhost"}
    settings.server.host = "example.org"
    with pytest.raises(BoxKeyError):
        settings.server.port = 9000
    settings.workers.append({"name": "second"})
    with pytest.raises(BoxKeyError):
        settings.workers[1].unknown = True


@pytest.mark.parametrize(
    "data, options, attribute, stored",
    [
        ({"a b": 1}, {}, "a_b", "a b"),
        ({"CamelCase": 1}, {"camel_killer_box": True}, "CamelCase", "camel_case"),
        ({"CamelCase": 1}, {"camel_killer_box": True, "camel_killer_box_keep_keys": True}, "camel_case", "CamelCase"),
        ({"a.b": 1}, {}, "a_b", "a.b"),
    ],
)
def test_attribute_aliases(data, options, attribute, stored):
    settings = StrictBox(data, **options)
    setattr(settings, attribute, 2)
    assert settings.to_dict() == {stored: 2}
    with pytest.raises(BoxKeyError):
        settings.missing = 3


def test_conversion_can_be_disabled():
    settings = StrictBox({"a b": 1}, conversion_box=False)
    with pytest.raises(BoxKeyError):
        settings.a_b = 2
    setattr(settings, "a b", 2)
    assert settings.to_dict() == {"a b": 2}


def test_dotted_attribute_assignment_checks_the_destination():
    settings = StrictBox({"server": {"port": 8000}, "workers": [{"name": "first"}]}, box_dots=True)
    setattr(settings, "server.port", 8080)
    setattr(settings, "workers[0].name", "changed")
    assert settings.server.port == 8080
    assert settings.workers[0].name == "changed"
    for path in ["server.prot", "workers[0].unknown", "missing.value"]:
        with pytest.raises(BoxKeyError):
            setattr(settings, path, True)
    assert settings.to_dict() == {"server": {"port": 8080}, "workers": [{"name": "changed"}]}


@pytest.mark.parametrize("create_on_get", [False, True])
def test_default_lookup_does_not_authorize_new_attribute_writes(create_on_get):
    settings = StrictBox(existing=1, default_box=True, default_box_create_on_get=create_on_get)
    with pytest.raises(BoxKeyError):
        settings.unknown = 2
    assert settings.to_dict() == {"existing": 1}
    settings.existing = 2
    assert settings.existing == 2


def test_failed_nested_default_assignment_does_not_attach_ephemeral_parents():
    settings = StrictBox(default_box=True)
    with pytest.raises(BoxKeyError):
        settings.parent.child = 1
    assert settings.to_dict() == {}


def test_deleted_field_must_be_explicitly_reintroduced():
    settings = StrictBox({"a b": 1})
    del settings.a_b
    with pytest.raises(BoxKeyError):
        settings.a_b = 2
    settings["a b"] = 2
    settings.a_b = 3
    assert settings.to_dict() == {"a b": 3}


def test_internal_attributes_and_property_setters():
    class Settings(StrictBox):
        _box_internal_attrs = ("_source",)

        @property
        def doubled(self):
            return self.value * 2

        @doubled.setter
        def doubled(self, value):
            self.value = value // 2

    settings = Settings(value=1)
    settings._source = "config.json"
    settings.doubled = 8
    assert settings.to_dict() == {"value": 4}
    assert settings._source == "config.json"
    with pytest.raises(BoxKeyError):
        settings.other = 1


def test_frozen_and_protected_fields_keep_their_errors():
    settings = StrictBox(value=1, frozen_box=True)
    with pytest.raises(BoxError, match="Box is frozen"):
        settings.value = 2
    with pytest.raises(BoxError, match="Box is frozen"):
        settings.unknown = 2
    settings = StrictBox({"update": 1})
    with pytest.raises(BoxKeyError, match="protected"):
        settings.update = 2


@pytest.mark.parametrize(
    "clone", [lambda value: value.copy(), copy.copy, copy.deepcopy, lambda value: pickle.loads(pickle.dumps(value))]
)
def test_copies_and_pickle_keep_attribute_restrictions(clone):
    settings = StrictBox({"a b": {"value": 1}, "entries": [{"value": 2}]}, box_dots=True)
    restored = clone(settings)
    assert type(restored) is StrictBox
    restored.a_b.value = 3
    restored.entries[0].value = 4
    for target in [restored, restored.a_b, restored.entries[0]]:
        assert isinstance(target, StrictBox)
        with pytest.raises(BoxKeyError):
            target.missing = 5


def test_json_round_trip_and_explicit_nested_class():
    settings = StrictBox(server={"port": 8000})
    restored = StrictBox.from_json(settings.to_json())
    assert isinstance(restored.server, StrictBox)
    restored.server.port = 8080
    with pytest.raises(BoxKeyError):
        restored.server.prot = 8080

    settings = StrictBox(server={}, box_class=Box)
    settings.server.name = "allowed"
    assert type(settings.server) is Box
    with pytest.raises(BoxKeyError):
        settings.unknown = True


def test_subclass_can_set_initial_attributes_during_construction():
    class Settings(StrictBox):
        def __init__(self, **kwargs):
            self.port = 8000
            super().__init__(**kwargs)

    settings = Settings(port=8080)
    assert settings.port == 8080
    with pytest.raises(BoxKeyError):
        settings.prot = 9000


@pytest.mark.parametrize("attribute", ["parent.child", "parent_child"])
def test_shadowed_dotted_path_does_not_create_nested_field(attribute):
    value = StrictBox(parent={}, box_dots=True)
    value.update({"parent.child": 1})
    with pytest.raises(BoxKeyError):
        setattr(value, attribute, 2)
    assert value.to_dict() == {"parent": {}, "parent.child": 1}


def test_camel_read_alias_does_not_create_new_write_parent():
    value = StrictBox(
        {"camel_case": {"field": 1}},
        box_dots=True,
        camel_killer_box=True,
        default_box=True,
    )
    with pytest.raises(BoxKeyError):
        setattr(value, "CamelCase.field", 2)
    assert value.to_dict() == {"camel_case": {"field": 1}}


def test_intact_mapping_missing_hook_is_not_run_by_preflight():
    events = []

    def factory():
        events.append("missing")
        return 0

    nested = defaultdict(factory)
    value = StrictBox(parent=nested, box_dots=True, box_intact_types=(defaultdict,))
    with pytest.raises(BoxKeyError):
        setattr(value, "parent.new", 1)
    assert not events
    assert not nested


def test_pending_parent_is_not_attached_by_attribute_assignment():
    value = StrictBox(default_box=True, default_box_attr={"field": 1})
    with pytest.raises(BoxKeyError):
        value.missing.field = 2
    assert value.to_dict() == {}


def test_property_setter_can_explicitly_define_data_field():
    class Settings(StrictBox):
        @property
        def port(self):
            raise AssertionError("getter must not run during assignment")

        @port.setter
        def port(self, value):
            self["saved_port"] = value

    settings = Settings()
    settings.port = 1234
    assert settings.to_dict() == {"saved_port": 1234}


def test_readonly_property_getter_is_not_evaluated():
    class Settings(StrictBox):
        @property
        def port(self):
            raise AssertionError("getter must not run during assignment")

    with pytest.raises(BoxKeyError):
        Settings().port = 1234


def test_inherited_property_setter_and_declared_internal_attribute():
    class Base(StrictBox):
        _box_internal_attrs = ("_path",)

        @property
        def value(self):
            return self["stored"]

        @value.setter
        def value(self, val):
            self["stored"] = val

    class Child(Base):
        pass

    item = Child()
    item.value = 3
    item._path = "example"
    assert item.to_dict() == {"stored": 3}
    frozen = Child(frozen_box=True)
    frozen._path = "allowed"
    assert frozen.to_dict() == {}


@pytest.mark.parametrize("attribute", ["nested.port", "nested.PORT", "nested.Port"])
def test_explicit_nested_config_box_keeps_case_insensitive_writes(attribute):
    settings = StrictBox(nested={"PORT": 1}, box_class=ConfigBox, box_dots=True)
    setattr(settings, attribute, 2)
    assert settings.nested.port == 2
    assert len(settings.nested) == 1


def test_numeric_dotted_segments():
    item = StrictBox({2: {-1: {"value": 1}}}, box_dots=True)
    setattr(item, "2.-1.value", 2)
    assert item[2][-1].value == 2
    with pytest.raises(BoxKeyError):
        setattr(item, "2.-1.unknown", 2)


def test_excluded_dotted_key_keeps_literal_meaning():
    item = StrictBox({"a.b": 1}, box_dots=True, box_dots_exclude=re.compile(r"a\.b"))
    item.a_b = 2
    assert item.to_dict() == {"a.b": 2}


def test_nested_list_paths():
    item = StrictBox(values=[[{"value": 1}]], box_dots=True)
    setattr(item, "values[0][0].value", 2)
    assert item["values"][0][0].value == 2
    with pytest.raises(BoxKeyError):
        setattr(item, "values[0][0].other", 3)


def test_intact_mapping_existing_key_never_runs_missing_factory():
    def missing():
        raise AssertionError("missing must not run")

    nested = defaultdict(missing, value=1)
    item = StrictBox(parent=nested, box_dots=True, box_intact_types=(defaultdict,))
    setattr(item, "parent.value", 2)
    assert nested == {"value": 2}


def test_missing_direct_attribute_never_calls_default_factory():
    def missing():
        raise AssertionError("missing must not run")

    item = StrictBox(default_box=True, default_box_attr=missing, default_box_create_on_get=True)
    with pytest.raises(BoxKeyError):
        item.absent = 2
    assert item.to_dict() == {}


def test_existing_nullable_field_with_default_box():
    item = StrictBox(default_box=True)
    item["nullable"] = None
    item.nullable = 2
    assert item.nullable == 2


def test_detached_default_child_can_be_updated_after_parent_key_was_defined():
    item = StrictBox(default_box=True, default_box_attr={"field": 1})
    child = item.missing
    item["missing"] = {"field": 10}
    child.field = 2
    assert item.to_dict() == {"missing": {"field": 10}}
    assert child.to_dict() == {"field": 2}


def test_ordinary_box_baseline_is_unchanged():
    item = Box()
    item.new = 2
    assert item.to_dict() == {"new": 2}


@pytest.mark.parametrize("path", ["entries.0", "entries[bad]", "entries[3]", "entries[3].value"])
def test_invalid_or_missing_list_destinations_are_not_created(path):
    value = StrictBox(entries=[{"value": 1}], box_dots=True, default_box=True)
    with pytest.raises(BoxKeyError):
        setattr(value, path, 2)
    assert value.to_dict() == {"entries": [{"value": 1}]}


def test_existing_list_element_can_be_replaced():
    value = StrictBox(entries=[{"value": 1}], box_dots=True)
    setattr(value, "entries[0]", {"replacement": 2})
    assert value.entries[0].replacement == 2
    with pytest.raises(BoxKeyError):
        value.entries[0].unknown = 3


@pytest.mark.parametrize("nested", [False, True])
def test_existing_default_list_paths_are_updated(nested):
    entries = [[{"value": 1}]] if nested else [{"value": 1}]
    value = StrictBox(entries=entries, box_dots=True, default_box=True)
    path = "entries[0][0].value" if nested else "entries[0].value"
    setattr(value, path, 2)
    expected = [[{"value": 2}]] if nested else [{"value": 2}]
    assert value.to_dict() == {"entries": expected}


def test_default_list_path_does_not_replace_an_intact_mapping():
    entry = defaultdict(int, value=1)
    value = StrictBox(entries=[entry], box_dots=True, default_box=True, box_intact_types=(defaultdict,))
    with pytest.raises(BoxKeyError):
        setattr(value, "entries[0].value", 2)
    assert value.entries[0] is entry
    assert entry == {"value": 1}


def test_intact_plain_list_is_not_a_dotted_destination():
    entries = [1]
    value = StrictBox(entries=entries, box_dots=True, box_intact_types=(list,))
    with pytest.raises(BoxKeyError):
        setattr(value, "entries[0]", 2)
    assert entries == [1]


def test_dotted_alias_can_update_literal_key_below_non_container():
    value = StrictBox(parent=1, box_dots=True)
    value.update({"parent.field": 2})
    value.parent_field = 3
    assert value.to_dict() == {"parent": 1, "parent.field": 3}


def test_case_insensitive_parent_does_not_authorize_a_new_exact_key():
    value = ConfigBox(default_box=True, default_box_attr={"field": 1}, box_class=StrictBox)
    child = value.MISSING
    value["missing"] = {"field": 10}
    with pytest.raises(BoxKeyError):
        child.field = 2
    assert value.to_dict() == {"missing": {"field": 10}}
    assert child.to_dict() == {"field": 1}


class DefaultMapping(MutableMapping):
    def __init__(self):
        self.data = {}
        self.defaulted = []

    def __getitem__(self, key):
        if key not in self.data:
            self.defaulted.append(key)
            self.data[key] = None
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)


def test_mapping_abc_contains_must_not_trigger_default_lookup():
    nested = DefaultMapping()
    value = StrictBox(parent=nested, box_dots=True)
    with pytest.raises(BoxKeyError):
        setattr(value, "parent.new", 1)
    assert nested.data == {}
    assert nested.defaulted == []


def test_mapping_abc_existing_field_can_be_replaced():
    nested = DefaultMapping()
    nested["existing"] = 1
    value = StrictBox(parent=nested, box_dots=True)
    setattr(value, "parent.existing", 2)
    assert nested.data == {"existing": 2}
    assert nested.defaulted == []


def test_dotted_write_checks_pending_parents_of_nested_destination():
    value = StrictBox(
        default_box=True,
        default_box_attr={"field": 1},
        box_intact_types=(Box,),
        box_dots=True,
    )
    value["stored"] = value.missing
    with pytest.raises(BoxKeyError):
        setattr(value, "stored.field", 2)
    assert list(value) == ["stored"]
    assert value.stored.field == 1


def test_case_insensitive_child_uses_its_own_pending_parent_rules():
    parent = ConfigBox(default_box=True, default_box_attr={"field": 1})
    child = parent.MISSING
    parent["missing"] = {"field": 10}
    root = StrictBox(stored=child, box_dots=True, box_intact_types=(Box,))
    setattr(root, "stored.field", 2)
    assert parent.to_dict() == {"missing": {"field": 10}}
    assert child.to_dict() == {"field": 2}
