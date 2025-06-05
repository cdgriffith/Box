|BuildStatus| |License|

|BoxImage|

**Fork Notice**
===============

This is a fork of the original `python-box <https://github.com/cdgriffith/Box>`_ library with enhanced notification capabilities.

**New Features in This Fork:**

* **Change Notifications**: Box and BoxList objects support an ``on_change`` callback parameter that gets triggered whenever values are modified
* **Hierarchical Propagation**: Changes in nested objects automatically propagate up to parent objects 
* **Root Detection**: The ``is_root`` parameter distinguishes between direct changes and propagated changes from nested objects
* **Modern Build System**: Migrated to pyproject.toml and uv for dependency management while maintaining Cython optimization support

**Notification System Usage:**

.. code:: python

        from box import Box

        def track_changes(obj, key, value, action, is_root):
            if is_root:
                print(f"Direct change: {key} = {value}")
            else:
                print(f"Nested change propagated: {key} changed")

        # Create Box with change tracking
        data = Box({
            'user': {'name': 'John', 'age': 30},
            'settings': ['theme', 'lang']
        }, on_change=track_changes)
        
        data.status = 'active'        # Triggers: Direct change: status = active
        data.user.name = 'Jane'       # Triggers: Nested change propagated: user changed
        data.settings.append('tz')    # Triggers: Nested change propagated: settings changed

For more details on the notification system, see the comprehensive test suite in ``test/test_notification.py``.

**Original Box Features**
=========================

.. code:: python

        from box import Box

        movie_box = Box({ "Robin Hood: Men in Tights": { "imdb stars": 6.7, "length": 104 } })

        movie_box.Robin_Hood_Men_in_Tights.imdb_stars
        # 6.7


Box will automatically make otherwise inaccessible keys safe to access as an attribute.
You can always pass `conversion_box=False` to `Box` to disable that behavior.
Also, all new dict and lists added to a Box or BoxList object are converted automatically.

There are over a half dozen ways to customize your Box and make it work for you.

Check out the new `Box github wiki <https://github.com/cdgriffith/Box/wiki>`_ for more details and examples!

Install
=======

**Fork Installation**

This fork is not published to PyPI. To use it, install directly from source:

.. code:: bash

        # Clone this fork
        git clone <your-fork-url>
        cd Box
        
        # Install with uv (recommended)
        uv sync --all-extras
        uv build  # Creates optimized wheel with Cython extensions
        
        # Or install with pip in development mode
        pip install -e .[all]

**Build with Cython Optimization**

This fork maintains full Cython optimization support:

.. code:: bash

        # Install dependencies including Cython
        uv sync --all-extras
        
        # Build optimized wheel
        uv build
        
        # Install the built wheel
        pip install dist/python_box-*.whl

**Original Installation (upstream)**

For the original python-box library without notification features:

.. code:: bash

        pip install python-box[all]~=7.0 --upgrade

Install with selected dependencies
----------------------------------

Box does not install external dependencies such as yaml and toml writers. Instead you can specify which you want,
for example, `[all]` is shorthand for:

.. code:: bash

        pip install python-box[ruamel.yaml,tomli_w,msgpack]~=7.0 --upgrade

But you can also sub out `ruamel.yaml` for `PyYAML`.

Check out `more details <https://github.com/cdgriffith/Box/wiki/Installation>`_ on installation details.

Box 7 is tested on python 3.7+, if you are upgrading from previous versions, please look through
`any breaking changes and new features <https://github.com/cdgriffith/Box/wiki/Major-Version-Breaking-Changes>`_.

Optimized Version
-----------------

Box has introduced Cython optimizations for major platforms by default.
Loading large data sets can be up to 10x faster!

If you are **not** on a x86_64 supported system you will need to do some extra work to install the optimized version.
There will be an warning of "WARNING: Cython not installed, could not optimize box" during install.
You will need python development files, system compiler, and the python packages `Cython` and `wheel`.

**Linux Example:**

First make sure you have python development files installed (`python3-dev` or `python3-devel` in most repos).
You will then need `Cython` and `wheel` installed and then install (or re-install with `--force`) `python-box`.

.. code:: bash

        pip install Cython wheel
        pip install python-box[all]~=7.0 --upgrade --force

If you have any issues please open a github issue with the error you are experiencing!

Overview
========

`Box` is designed to be a near transparent drop in replacements for
dictionaries that add dot notation access and other powerful feature.

There are a lot of `types of boxes <https://github.com/cdgriffith/Box/wiki/Types-of-Boxes>`_
to customize it for your needs, as well as handy `converters <https://github.com/cdgriffith/Box/wiki/Converters>`_!

Keep in mind any sub dictionaries or ones set after initiation will be automatically converted to
a `Box` object, and lists will be converted to `BoxList`, all other objects stay intact.

Check out the `Quick Start <https://github.com/cdgriffith/Box/wiki/Quick-Start>`_  for more in depth details.

Notification System (Fork Feature)
===================================

This fork adds a comprehensive change notification system to Box and BoxList objects.

**Basic Usage**

Pass an ``on_change`` callback when creating a Box or BoxList:

.. code:: python

        def my_callback(obj, key, value, action, is_root):
            print(f"Change: {key} = {value} (action: {action}, is_root: {is_root})")
        
        data = Box({'user': {'name': 'John'}}, on_change=my_callback)
        data.user.name = 'Jane'  # Triggers callback

**Callback Parameters**

* ``obj``: The object where the callback was originally set (always the root)
* ``key``: The key/index that changed 
* ``value``: The new value (or None for deletions)
* ``action``: Type of change (``'set'``, ``'delete'``, ``'clear'``, ``'append'``, ``'insert'``, ``'child_change'``)
* ``is_root``: ``True`` for direct changes, ``False`` for nested changes that propagated up

**Change Types**

* **Direct changes**: ``is_root=True`` - modifications made directly to the root object
* **Propagated changes**: ``is_root=False`` - modifications made to nested objects that bubble up

**Supported Operations**

All modification operations trigger notifications:

.. code:: python

        data = Box({}, on_change=callback)
        
        # Set operations
        data.key = 'value'              # action='set', is_root=True
        data['key'] = 'value'           # action='set', is_root=True
        data.update({'a': 1, 'b': 2})   # action='set', is_root=True (per key)
        
        # Delete operations  
        del data.key                    # action='delete', is_root=True
        data.pop('key')                 # action='delete', is_root=True
        data.clear()                    # action='clear', is_root=True
        
        # Nested changes
        data.nested.value = 42          # action='child_change', is_root=False

**BoxList Support**

BoxList objects also support notifications:

.. code:: python

        items = BoxList([1, 2, 3], on_change=callback)
        
        items.append(4)                 # action='append', is_root=True
        items.insert(0, 0)              # action='insert', is_root=True  
        items[1] = 'new'                # action='set', is_root=True
        items.pop()                     # action='pop', is_root=True
        items.remove('new')             # action='remove', is_root=True
        items.clear()                   # action='clear', is_root=True

**Error Handling**

Callback errors are silently caught to prevent disrupting normal operations:

.. code:: python

        def bad_callback(obj, key, value, action, is_root):
            raise Exception("Callback error!")
        
        data = Box(on_change=bad_callback)
        data.key = 'value'  # Works normally, error is ignored

**Use Cases**

* **Change tracking**: Monitor all modifications to complex data structures
* **Validation**: Implement custom validation logic on data changes  
* **Persistence**: Automatically save data when changes occur
* **Debugging**: Log all changes for debugging purposes
* **Event systems**: Trigger events based on data modifications

**Performance Notes**

* Cython optimization is fully supported for notification-enabled objects
* Callback overhead is minimal when no callback is set
* Parent references are efficiently managed automatically

`Box` can be instantiated the same ways as `dict`.

.. code:: python

        Box({'data': 2, 'count': 5})
        Box(data=2, count=5)
        Box({'data': 2, 'count': 1}, count=5)
        Box([('data', 2), ('count', 5)])

        # All will create
        # <Box: {'data': 2, 'count': 5}>

`Box` is a subclass of `dict` which overrides some base functionality to make
sure everything stored in the dict can be accessed as an attribute or key value.

.. code:: python

      small_box = Box({'data': 2, 'count': 5})
      small_box.data == small_box['data'] == getattr(small_box, 'data')

All dicts (and lists) added to a `Box` will be converted on insertion to a `Box` (or `BoxList`),
allowing for recursive dot notation access.

`Box` also includes helper functions to transform it back into a `dict`,
as well as into `JSON`, `YAML`, `TOML`, or `msgpack` strings or files.


Thanks
======

A huge thank you to everyone that has given features and feedback over the years to Box! Check out everyone that has contributed_.

A big thanks to Python Software Foundation, and PSF-Trademarks Committee, for official approval to use the Python logo on the `Box` logo!

Also special shout-out to PythonBytes_, who featured Box on their podcast.


License
=======

MIT License, Copyright (c) 2017-2023 Chris Griffith. See LICENSE_ file.


.. |BoxImage| image:: https://raw.githubusercontent.com/cdgriffith/Box/master/box_logo.png
   :target: https://github.com/cdgriffith/Box
.. |BuildStatus| image:: https://github.com/cdgriffith/Box/workflows/Tests/badge.svg?branch=master
   :target: https://github.com/cdgriffith/Box/actions?query=workflow%3ATests
.. |License| image:: https://img.shields.io/pypi/l/python-box.svg
   :target: https://pypi.python.org/pypi/python-box/

.. _PythonBytes: https://pythonbytes.fm/episodes/show/19/put-your-python-dictionaries-in-a-box-and-apparently-python-is-really-wanted
.. _contributed: AUTHORS.rst
.. _`Wrapt Documentation`: https://wrapt.readthedocs.io/en/latest
.. _reusables: https://github.com/cdgriffith/reusables#reusables
.. _created: https://github.com/cdgriffith/Reusables/commit/df20de4db74371c2fedf1578096f3e29c93ccdf3#diff-e9a0f470ef3e8afb4384dc2824943048R51
.. _LICENSE: https://github.com/cdgriffith/Box/blob/master/LICENSE
