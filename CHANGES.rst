Changelog
---------

Version 3.1.0
~~~~~~~~~~~~~

* Adding copy and deepcopy support that with return a Box object
* Adding support for customizable safe attr replacement
* Fixing that a recursion loop could occur if `_box_config` was somehow removed

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
