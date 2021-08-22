Changelog
=========

Version 5.4.1
-------------

* Fixing #205 setdefault behavior with box_dots (thanks to  Ivan Pepelnjak)

Version 5.4.0
-------------

* Adding py.typed for mypy support (thanks to Dominic)
* Adding testing for Python 3.10-dev
* Fixing #189 by adding mappings for mypy
* Fixing setdefault behavior with box_dots (thanks to ipcoder)
* Changing #193 how magic methods are handled with default_box (thanks to Rexbard)


Version 5.3.0
-------------

* Adding support for functions to box_recast (thanks to Jacob Hayes)
* Adding #181 support for extending or adding new items to list during `merge_update`  (thanks to Marcos Dione)
* Fixing maintain stacktrace cause for BoxKeyError and BoxValueError (thanks to Jacob Hayes)
* Fixing #177 that emtpy yaml files raised errors instead of returning empty objects (thanks to Tim Schwenke)
* Fixing #171 that `popitems` wasn't first checking if box was frozen (thanks to Varun Madiath)
* Changing all files to LF line endings
* Removing duplicate `box_recast` calls (thanks to Jacob Hayes)
* Removing coveralls code coverage, due to repeated issues with service

Version 5.2.0
-------------

* Adding checks for frozen boxes to `pop`, `popitem` and `clear` (thanks to Varun Madiath)
* Fixing requirements-test.txt (thanks to Fabian Affolter)
* Fixing Flake8 conflicts with black (thanks to Varun Madiath)
* Fixing coveralls update (thanks to Varun Madiath)

Version 5.1.1
-------------

* Adding testing for Python 3.9
* Fixing #165 `box_dots` to work with `default_box`

Version 5.1.0
-------------

* Adding #152 `dotted` option for `items` function (thanks to ipcoder)
* Fixing #157 bug in box.set_default where value is dictionary, return the internal value and not detached temporary (thanks to Noam Graetz)
* Removing warnings on import if optional libraries are missing

Version 5.0.1
-------------

* Fixing #155 default box saving internal method calls and restricted options (thanks to Marcelo Huerta)

Version 5.0.0
-------------

* Adding support for msgpack converters `to_msgpack` and `from_msgpack`
* Adding #144 support for comparision of `Box` to other boxes or dicts via the `-` sub operator (thanks to Hitz)
* Adding support to `|` union boxes like will come default in Python 3.9 from PEP 0584
* Adding `mypy` type checking, `black` formatting and other checks on commit
* Adding #148 new parameter `box_class` for cleaner inheritance (thanks to David Aronchick)
* Adding #152 `dotted` option for `keys` method to return box_dots style keys (thanks to ipcoder)
* Fixing box_dots to properly delete items from lists
* Fixing box_dots to properly find items with dots in their key
* Fixing that recast of subclassses of `Box` or `BoxList` were not fed box properties (thanks to Alexander Kapustin)
* Changing #150 that sub boxes are always created to properly propagate settings and copy objects (thanks to ipcoder)
* Changing #67 that default_box will not raise key errors on `pop` (thanks to Patrock)
* Changing `to_csv` and `from_csv` to have same string and filename options as all other transforms
* Changing #127 back to no required external imports, instead have extra requires like [all] (thanks to wim glenn)
* Changing from putting all details in README.rst to a github wiki at https://github.com/cdgriffith/Box/wiki
* Changing `BoxList.box_class` to be stored in `BoxList.box_options` dict as `box_class`
* Changing `del` will raise `BoxKeyError`, subclass of both `KeyError` and `BoxError`
* Removing support for single level circular references
* Removing readthedocs generation
* Removing overrides for `keys`, `values` and `items` which will return views again

Version 4.2.3
-------------

* Fixing README.md example #149 (thanks to J Alan Brogan)
* Changing `protected_keys` to remove magic methods from dict #146 (thanks to Krishna Penukonda)

Version 4.2.2
-------------

* Fixing `default_box` doesn't first look for safe attributes before falling back to default (thanks to Pymancer)
* Changing from TravisCI to Github Actions
* Changing that due to `default_box` fix, `pop` or `del` no longer raise BoxKeyErrors on missing items (UNCAUGHT BUG)

Version 4.2.1
-------------

* Fixing uncaught print statement (thanks to Bruno Rocha)
* Fixing old references to `box_it_up` in the documentation


Version 4.2.0
-------------

* Adding optimizations for speed ups to creation and inserts
* Adding internal record of safe attributes for faster lookups, increases memory footprint for speed (thanks to Jonas Irgens Kylling)
* Adding all additional methods specific to `Box` as protected keys
* Fixing `merge_update` from incorrectly calling `__setattr__` which was causing a huge slowdown (thanks to Jonas Irgens Kylling)
* Fixing `copy` and `__copy__` not copying box options


Version 4.1.0
-------------

* Adding support for list traversal with `box_dots` (thanks to Lei)
* Adding `BoxWarning` class to allow for the clean suppression of warnings
* Fixing default_box_attr to accept items that evaluate to `None` (thanks to Wenbo Zhao and Yordan Ivanov)
* Fixing `BoxList` to properly send internal box options down into new lists
* Fixing issues with conversion and camel killer boxes not being set properly on insert
* Changing default_box to set objects in box on lookup
* Changing `camel_killer` to convert items on insert, which will change the keys when converted back to dict unlike before
* Fallback to `PyYAML` if `ruamel.yaml` is not detected (thanks to wim glenn)
* Removing official support for `pypy` as it's pickling behavior is not the same as CPython
* Removing internal __box_heritage as it was no longer needed due to behavior update

Version 4.0.4
-------------

* Fixing `get` to return None when not using default box (thanks to Jeremiah Lowin)

Version 4.0.3
-------------

* Fixing non-string keys breaking when box_dots is enabled (thanks to Marcelo Huerta)

Version 4.0.2
-------------

* Fixing converters to properly pass through new box arguments (thanks to Marcelo Huerta)

Version 4.0.1
-------------

* Fixing setup.py for release
* Fixing documentation link

Version 4.0.0
-------------

* Adding support for retrieving items via dot notation in keys
* Adding `box_from_file` helper function
* Adding merge_update that acts like previous Box magic update
* Adding support to `+` boxes together
* Adding default_box now can support expanding on `None` placeholders (thanks to Harun Tuncay and Jeremiah Lowin)
* Adding ability to recast specified fields (thanks to Steven McGrath)
* Adding to_csv and from_csv capability for BoxList objects (thanks to Jiuli Gao)
* Changing layout of project to be more object specific
* Changing update to act like normal dict update
* Changing to 120 line character limit
* Changing how `safe_attr` handles unsafe characters
* Changing all exceptions to be bases of BoxError so can always be caught with that base exception
* Changing delete to also access converted keys (thanks to iordanivanov)
* Changing from `PyYAML` to `ruamel.yaml` as default yaml import, aka yaml version default is 1.2 instead of 1.1
* Removing `ordered_box` as Python 3.6+ is ordered by default
* Removing `BoxObject` in favor of it being another module

Version 3.4.6
-------------

* Fixing allowing frozen boxes to be deep copyable (thanks to jandelgado)

Version 3.4.5
-------------

* Fixing update does not convert new sub dictionaries or lists (thanks to Michael Stella)
* Changing update to work as it used to with sub merging until major release

Version 3.4.4
-------------

* Fixing pop not properly resetting box_heritage (thanks to Jeremiah Lowin)

Version 3.4.3
-------------

* Fixing propagation of box options when adding a new list via setdefault (thanks to Stretch)
* Fixing update does not keep box_intact_types (thanks to pwwang)
* Fixing update to operate the same way as a normal dictionary (thanks to Craig Quiter)
* Fixing deepcopy not copying box options (thanks to Nikolay Stanishev)

Version 3.4.2
-------------

* Adding license, changes and authors files to source distribution

Version 3.4.1
-------------

* Fixing copy of inherited classes (thanks to pwwang)
* Fixing `get` when used with default_box

Version 3.4.0
-------------

* Adding `box_intact_types` that allows preservation of selected object types (thanks to pwwang)
* Adding limitations section to readme

Version 3.3.0
-------------

* Adding `BoxObject` (thanks to Brandon Gomes)

Version 3.2.4
-------------

* Fixing recursion issue #68 when using setdefault (thanks to sdementen)
* Fixing ordered_box would make 'ordered_box_values' internal helper as key in sub boxes

Version 3.2.3
-------------

* Fixing pickling with default box (thanks to sdementen)

Version 3.2.2
-------------

* Adding hash abilities to new frozen BoxList
* Fixing hashing returned unpredictable values (thanks to cebaa)
* Fixing update to not handle protected words correctly (thanks to deluxghost)
* Removing non-collection support for mapping and callable identification

Version 3.2.1
-------------

* Fixing pickling on python 3.7 (thanks to Martijn Pieters)
* Fixing rumel loader error (thanks to richieadler)
* Fixing frozen_box does not freeze the outermost BoxList (thanks to V.Anh Tran)

Version 3.2.0
-------------

* Adding `ordered_box` option to keep key order based on insertion (thanks to pwwang)
* Adding custom `__iter__`, `__revered__`, `pop`, `popitems`
* Fixing ordering of camel_case_killer vs default_box (thanks to Matan Rosenberg)
* Fixing non string keys not being supported correctly (thanks to Matt Wisniewski)

Version 3.1.1
-------------

* Fixing `__contains__` (thanks to Jiang Chen)
* Fixing `get` could return non box objects

Version 3.1.0
-------------

* Adding `copy` and `deepcopy` support that with return a Box object
* Adding support for customizable safe attr replacement
* Adding custom error for missing keys
* Changing that for this 3.x release, 2.6 support exists
* Fixing that a recursion loop could occur if `_box_config` was somehow removed
* Fixing pickling

Version 3.0.1
-------------

* Fixing first level recursion errors
* Fixing spelling mistakes (thanks to John Benediktsson)
* Fixing that list insert of lists did not use the original list but create an empty one

Version 3.0.0
-------------

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
-------------

* Adding support for `ruamel.yaml` (Thanks to Alexandre Decan)
* Adding Contributing and Authors files

Version 2.1.0
-------------

* Adding `.update` and `.set_default` functionality
* Adding `dir` support

Version 2.0.0
-------------

* Adding `BoxList` to allow for any `Box` to be recursively added to lists as well
* Adding `to_json` and `to_yaml` functions
* Changing `Box` original functionality to `LightBox`, `Box` now searches lists
* Changing `Box` callable to return keys, not values, and they are sorted
* Removing `tree_view` as near same can be seen with YAML


Version 1.0.0
-------------

* Initial release, copy from `reusables.Namespace`
* Original creation, 2\13\2014
