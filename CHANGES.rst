Version 3.0.0
=============

* Adding default object abilities with `default_box` and `default_box_attr` kwargs
* Adding `frozen_box` kwarg
* Adding `BoxError` exception for custom errors
* Adding `conversion_box` to automatically try to find matching attributes
* Adding `camel_killer_box` that converts CamelCaseKeys to camel_case_keys
* Changing how the Box object works, to conversion on extraction
* Removing `__call__` for compatibly with django and to make more like dict object

Version 2.2.0
=============

* Adding support for `ruamel.yaml` (Thanks to Alexandre Decan)
* Adding Contributing and Authors files

Version 2.1.0
=============

* Adding `.update` and `.set_default` functionality
* Adding `dir` support

Version 2.0.0
=============

* Adding `BoxList` to allow for `Box`es to be recursively added to lists as well
* Adding `to_json` and `to_yaml` functions
* Changing `Box` original functionality to `LightBox`, `Box` now searches lists
* Changing `Box` callable to return keys, not values, and they are sorted
* Removing `tree_view` as near same can be seen with YAML


Version 1.0.0
=============

* Initial release, copy from `reusables.Namespace`
* Original creation, 2\13\2014
