|BuildStatus| |License|

|BoxImage|

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

.. code:: bash

        pip install --upgrade python-box[all]

Box 5 is no longer forcing install of external dependencies such as yaml and toml. Instead you can specify which you want,
for example, `all` is shorthand for:

.. code:: bash

        pip install --upgrade python-box[ruamel.yaml,toml,msgpack]

But you can also sub out "ruamel.yaml" for "PyYAML".

Check out `more details <https://github.com/cdgriffith/Box/wiki/Installation>`_ on installation details.

Box 5 is tested on python 3.6+ and pypy3, if you are upgrading from previous versions, please look through
`any breaking changes and new features <https://github.com/cdgriffith/Box/wiki/Major-Version-Breaking-Changes-and-New-Features>`_.


If you have any issues please open a github issue with the error you are experiencing!

Overview
========

`Box` is designed to be an easy drop in transparently replacements for
dictionaries, thanks to Python's
duck typing capabilities, which adds dot notation access. Any sub
dictionaries or ones set after initiation will be automatically converted to
a `Box` object. You can always run `.to_dict()` on it to return the object
and all sub objects back into a regular dictionary.

Check out the `Quick Start <https://github.com/cdgriffith/Box/wiki/Quick-Start>`_  for more in depth details.

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

All dicts (and lists) added to a `Box` will be converted on lookup to a `Box` (or `BoxList`),
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

MIT License, Copyright (c) 2017-2020 Chris Griffith. See LICENSE_ file.


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
