Changelog
---------

Version 3.4.6
~~~~~~~~~~~~~

* Fixing allowing frozen boxes to be deep copyable (thanks to jandelgado)

Version 3.4.5
~~~~~~~~~~~~~

* Fixing update does not convert new sub dictionaries or lists (thanks to Michael Stella)
* Changing update to work as it used to with sub merging until major release

Version 3.4.4
~~~~~~~~~~~~~

* Fixing pop not properly resetting box_heritage (thanks to Jeremiah Lowin)

Version 3.4.3
~~~~~~~~~~~~~

* Fixing propagation of box options when adding a new list via setdefault (thanks to Stretch)
* Fixing update does not keep box_intact_types (thanks to pwwang)
* Fixing update to operate the same way as a normal dictionary (thanks to Craig Quiter)
* Fixing deepcopy not copying box options (thanks to Nikolay Stanishev)

Version 3.4.2
~~~~~~~~~~~~~

* Adding license, changes and authors files to source distribution

Version 3.4.1
~~~~~~~~~~~~~

* Fixing copy of inherited classes (thanks to pwwang)
* Fixing `get` when used with default_box

Version 3.4.0
~~~~~~~~~~~~~

* Adding `box_intact_types` that allows preservation of selected object types (thanks to pwwang)
* Adding limitations section to readme

Version 3.3.0
~~~~~~~~~~~~~

* Adding `BoxObject` (thanks to Brandon Gomes)

Version 3.2.4
~~~~~~~~~~~~~

* Fixing recursion issue #68 when using setdefault (thanks to sdementen)
* Fixing ordered_box would make 'ordered_box_values' internal helper as key in sub boxes

Version 3.2.3
~~~~~~~~~~~~~

* Fixing pickling with default box (thanks to sdementen)

Version 3.2.2
~~~~~~~~~~~~~

* Adding hash abilities to new frozen BoxList
* Fixing hashing returned unpredictable values (thanks to cebaa)
* Fixing update to not handle protected words correctly (thanks to deluxghost)
* Removing non-collection support for mapping and callable identification

Version 3.2.1
~~~~~~~~~~~~~

* Fixing pickling on python 3.7 (thanks to Martijn Pieters)
* Fixing rumel loader error (thanks to richieadler)
* Fixing frozen_box does not freeze the outermost BoxList (thanks to V.Anh Tran)

Version 3.2.0
~~~~~~~~~~~~~

* Adding `ordered_box` option to keep key order based on insertion (thanks to pwwang)
* Adding custom `__iter__`, `__revered__`, `pop`, `popitems`
* Fixing ordering of camel_case_killer vs default_box (thanks to Matan Rosenberg)
* Fixing non string keys not being supported correctly (thanks to Matt Wisniewski)

Version 3.1.1
~~~~~~~~~~~~~

* Fixing `__contains__` (thanks to Jiang Chen)
* Fixing `get` could return non box objects

Version 3.1.0
~~~~~~~~~~~~~

* Adding `copy` and `deepcopy` support that with return a Box object
* Adding support for customizable safe attr replacement
* Adding custom error for missing keys
* Changing that for this 3.x release, 2.6 support exists
* Fixing that a recursion loop could occur if `_box_config` was somehow removed
* Fixing pickling

Version 3.0.1
~~~~~~~~~~~~~

* Fixing first level recursion errors
* Fixing spelling mistakes (thanks to John Benediktsson)
* Fixing that list insert of lists did not use the original list but create an empty one

Version 3.0.0
~~~~~~~~~~~~~

* Adding default object abilities with `default_box` and `default_box_attr` kwargs
* Adding `from_json` and `from_yaml` functions to both `Box` and `BoxList`
* Adding `frozen_box` option
* Adding `BoxError` exception for custom errors
* Adding `conversion_box` to automatically try to find matching attributes
* Adding `camel_killer_box` that converts CamelCaseKeys to camel_case_keys
* Adding `SBox` that has `json` and `yaml` properties that map to default `to_json()` and `to_yaml()`
* Adding `box_it_up` property that will make sure all boxes are created and populated like previous version
* Adding `modify_tuples_box` option to recreate tuples with Boxes instead of dicts
* Adding `to_json` and `to_yaml` for `BoxList`
* Changing how the Box object works, to conversion on extraction
* Removing `__call__` for compatibly with django and to make more like dict object
* Removing support for python 2.6
* Removing `LightBox`
* Removing default indent for `to_json`

Version 2.2.0
~~~~~~~~~~~~~

* Adding support for `ruamel.yaml` (Thanks to Alexandre Decan)
* Adding Contributing and Authors files

Version 2.1.0
~~~~~~~~~~~~~

* Adding `.update` and `.set_default` functionality
* Adding `dir` support

Version 2.0.0
~~~~~~~~~~~~~

* Adding `BoxList` to allow for `Box`es to be recursively added to lists as well
* Adding `to_json` and `to_yaml` functions
* Changing `Box` original functionality to `LightBox`, `Box` now searches lists
* Changing `Box` callable to return keys, not values, and they are sorted
* Removing `tree_view` as near same can be seen with YAML


Version 1.0.0
~~~~~~~~~~~~~

* Initial release, copy from `reusables.Namespace`
* Original creation, 2\13\2014
