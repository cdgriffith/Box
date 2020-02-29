|BuildStatus| |CoverageStatus| |License| |PyPi| |DocStatus|

|BoxImage|

Python dictionaries with advanced dot notation access.

.. code:: python

        from box import Box

        movie_box = Box({
            "Robin Hood: Men in Tights": {
                "imdb_stars": 6.7,
                "length": 104,
                "stars": [ {"name": "Cary Elwes", "imdb": "nm0000144", "role": "Robin Hood"},
                           {"name": "Richard Lewis", "imdb": "nm0507659", "role": "Prince John"} ]
            }
        })

        movie_box.Robin_Hood_Men_in_Tights.imdb_stars
        # 6.7

        movie_box.Robin_Hood_Men_in_Tights.stars[0].name
        # 'Cary Elwes'


Box will automatically make otherwise inaccessible keys ("Robin Hood: Men in Tights") safe to access as an attribute.
You can always pass `conversion_box=False` to `Box` to disable that behavior.

Also, all new dict and lists added to a Box or BoxList object are converted automatically.

.. code:: python

        movie_box.Robin_Hood_Men_in_Tights.stars.append(
             {"name": "Roger Rees", "imdb": "nm0715953", "role": "Sheriff of Rottingham"})

        movie_box.Robin_Hood_Men_in_Tights.stars[-1].role
        # 'Sheriff of Rottingham'

Install
=======

.. code:: bash

        pip install --upgrade python-box

Box 4 is tested on python 3.6+

If you have any issues please open a github issue with the error you are experiencing!

Overview
========

Box 4 is out, check out the `changes and updates <https://github.com/cdgriffith/Box/blob/master/docs/4.x_changes.rst>`_!

`Box` is designed to be an easy drop in transparently replacements for
dictionaries, thanks to Python's
duck typing capabilities, which adds dot notation access. Any sub
dictionaries or ones set after initiation will be automatically converted to
a `Box` object. You can always run `.to_dict()` on it to return the object
and all sub objects back into a regular dictionary.


.. code:: python

         movie_box.movies.Spaceballs.to_dict()
         {'director': 'Mel Brooks',
          'imdb stars': 7.1,
          'length': 96,
          'personal thoughts': 'On second thought, it was hilarious!',
          'rating': 'PG',
          'stars': [{'imdb': 'nm0000316', 'name': 'Mel Brooks', 'role': 'President Skroob'},
                    {'imdb': 'nm0001006', 'name': 'John Candy', 'role': 'Barf'},
                    {'imdb': 'nm0001548', 'name': 'Rick Moranis', 'role': 'Dark Helmet'},
                    {'imdb': 'nm0000597', 'name': 'Bill Pullman', 'role': 'Lone Starr'}]}

Boxes
=====

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
as well as into `JSON` or `YAML` strings or files.

Limitations
-----------

`Box` is a subclass of `dict` and as such, certain keys cannot be accessed via dot notation.
This is because names such as `keys` and `pop` have already been declared as methods, so `Box` cannot
use it's special sauce to overwrite them. However it is still possible to have items with those names
in the `Box` and access them like a normal dictionary, such as `my_box['keys']`.

*This is as designed, and will not be changed.*

Common non-magic methods that exist in a `Box` are:
`clear, copy, from_json, fromkeys, get, items, keys, pop, popitem, setdefault, to_dict, to_json, update, merge_update, values`.
To view an entire list of what cannot be accessed via dot notation, run the command `dir(Box())`.


Box's parameters
----------------

.. table::

   ================ ========= ===========
   Keyword Argument Default   Description
   ================ ========= ===========
   conversion_box   True      Automagically make keys with spaces attribute accessible
   frozen_box       False     Make the box immutable, hashable (if all items are non-mutable)
   default_box      False     Act like a recursive default dict
   default_box_attr Box       Can overwrite with a different (non-recursive) default attribute to return
   camel_killer_box False     CamelCaseKeys become attribute accessible like snake case (camel_case_keys)
   box_safe_prefix  "x"       Character or prefix to prepend to otherwise invalid attributes
   box_duplicates   "ignore"  When conversion duplicates are spotted, either ignore, warn or error
   box_intact_types ()        Tuple of objects to preserve and not convert to a Box object
   box_recast       None      cast certain keys to a specified type
   box_dots         False     Allow access to nested dicts by dots in key names
   ================ ========= ===========

Box's functions
---------------

.. table::

   ================ ===========
   Function Name    Description
   ================ ===========
   to_dict          Recursively transform all Box (and BoxList) objects back into a dict (and lists)
   to_json          Save Box object as a JSON string or write to a file with the `filename` parameter
   to_yaml          Save Box object as a YAML string or write to a file with the `filename` parameter
   to_toml*         Save Box object as a TOML string or write to a file with the `filename` parameter
   from_json        Classmethod, Create a Box object from a JSON file or string (all Box parameters can be passed)
   from_yaml        Classmethod, Create a Box object from a YAML file or string (all Box parameters can be passed)
   from_toml*       Classmethod, Create a Box object from a TOML file or string (all Box parameters can be passed)
   merge_update     Recursively merge dictionaries or Boxes together instead of replacing
   ================ ===========

\* Do not work with BoxList, only Box

Conversion Box
--------------

By default, Box is now a `conversion_box`
that adds automagic attribute access for keys that could not normally be attributes.
It can of course be disabled with the keyword argument `conversion_box=False`.

.. code:: python

         movie_box.movies.Spaceballs["personal thoughts"] = "It was a good laugh"
         movie_box.movies.Spaceballs.personal_thoughts
         # 'It was a good laugh'

         movie_box.movies.Spaceballs.personal_thoughts = "On second thought, it was hilarious!"
         movie_box.movies.Spaceballs["personal thoughts"]
         # 'On second thought, it was hilarious!'

         # If a safe attribute matches a key exists, it will not create a new key
         movie_box.movies.Spaceballs["personal_thoughts"]
         # KeyError: 'personal_thoughts'

Keys are modified in the following steps to make sure they are attribute safe:

1. Convert to string (Will encode as UTF-8 with errors ignored)
2. Replaces any spaces with underscores
3. Remove anything other than ascii letters, numbers or underscores
4. If the first character is an integer, it will prepend a lowercase 'x' to it
5. If the string is a built-in that cannot be used, it will prepend a lowercase 'x'
6. Removes any duplicate underscores

This does not change the case of any of the keys.

.. code:: python

         bx = Box({"321 Is a terrible Key!": "yes, really"})
         bx.x321_Is_a_terrible_Key
         # 'yes, really'

These keys are not stored anywhere, and trying to modify them as an
attribute will actually modify the underlying regular key's value.

**Warning: duplicate attributes possible**

If you have two keys that evaluate to the same attribute, such as "a!b" and "a?b" would become `.ab`,
there is no way to discern between them,
only reference or update them via standard dictionary modification.


Frozen Box
----------

Want to show off your box without worrying about others messing it up? Freeze it!

.. code:: python

      frigid = Box(data={'Python': 'Rocks', 'inferior': ['java', 'cobol']}, frozen_box=True)

      frigid.data.Python = "Stinks"
      # box.BoxError: Box is frozen

      frigid.data.Python
      # 'Rocks'

      hash(frigid)
      # 4021666719083772260

      frigid.data.inferior
      # ('java', 'cobol')


It's hashing ability is the same as the humble `tuple`, it will not be hashable
if it has mutable objects. Speaking of `tuple`, that's what all the lists
becomes now.

Default Box
-----------

It's boxes all the way down. At least, when you specify `default_box=True` it can be.

.. code:: python

      empty_box = Box(default_box=True)

      empty_box.a.b.c.d.e.f.g
      # <Box: {}>

      # BOX 4.1 change, on lookup the sub boxes are created
      print(empty_box)
      # <Box: {'a': {'b': {'c': {'d': {'e': {'f': {'g': {}}}}}}}}>

      empty_box.a.b.c.d.e.f.g = "h"
      empty_box
      # <Box: {'a': {'b': {'c': {'d': {'e': {'f': {'g': 'h'}}}}}}}>

Unless you want it to be something else.

.. code:: python

      evil_box = Box(default_box=True, default_box_attr="Something Something Something Dark Side")

      evil_box.not_defined
      # 'Something Something Something Dark Side'

      # Keep in mind it will no longer be possible to go down multiple levels
      evil_box.not_defined.something_else
      # AttributeError: 'str' object has no attribute 'something_else'

`default_box_attr` will first check if it is callable, and will call the object
if it is, otherwise it will see if has the `copy` attribute and will call that,
lastly, will just use the provided item as is.

4.1 Update: Previous versions had an error when something that evaluated to None would
also return a box, such as an empty string or empty list. This behavior has been fixed.

Camel Killer Box
----------------

Similar to how conversion box works, allow CamelCaseKeys to be found as
snake_case_attributes.

.. code:: python

      cameled = Box(BadHabit="I just can't stop!", camel_killer_box=True)

      cameled.bad_habit
      # "I just can't stop!"

Box Recast Values
-----------------

Automatically convert all incoming values of a particular key (at root or any sub box)
to a different type.

For example, if you wanted to make sure any field labeled 'id' was an integer:

.. code:: python

    my_box = Box(box_recast={'id': int})

    my_box.new_key = {'id': '55', 'example': 'value'}

    print(type(my_box.new_key.id))
    # 55

If it cannot be converted, it will raise a `BoxValueError` (catachable with either `BoxError` or `ValueError` as well)

.. code:: python

    my_box = Box(box_recast={'id': int})

    my_box.id = 'Harry'

    # box.exceptions.BoxValueError: Cannot convert Harry to <class 'int'>

Box Intact Types
----------------

Do you not want box to convert lists or tuples or incoming dictionaries for some reasonn?
That's totally fine, we got you covered!

.. code:: python

    my_box = Box(box_intact_types=[list, tuple])

    # Don't automatically convert lists into #BoxList
    my_box.new_data = [{'test': 'data'}]

    print(type(my_box.new_data))
    # <class 'list'>


Box Dots
--------

A new way to traverse the Box!

.. code:: python

    my_box = Box(box_dots=True)

    my_box.incoming = {'new': {'source 1': {'$$$': 'money'}}}

    print(my_box['incoming.new.source 1.$$$'])
    # money

    my_box['incoming.new.source 1.$$$'] = 'spent'
    print(my_box)
    # {'incoming': {'new': {'source 1': {'$$$': 'spent'}}}}

Be aware, if those sub boxes didn't exist as planned, a new key with that value would be created instead

.. code:: python

    del my_box['incoming']
    my_box['incoming.new.source 1.$$$'] = 'test'
    print(my_box)

    # {'incoming.new.source 1.$$$': 'test'}

4.1 Update: Support for traversing box lists as well!

.. code:: python

        my_box = Box({'data': [ {'rabbit': 'hole'} ] }, box_dots=True)
        print(data.data[0].rabbit)
        # hole

This does only work for keys that are already strings as of version 4.1.

BoxList
=======

To make sure all items added to lists in the box are also converted, all lists
are covered into `BoxList`. It's possible to
initiate these directly and use them just like a `Box`.

.. code:: python

      from box import BoxList

      my_boxlist = BoxList({'item': x} for x in range(10))
      #  <BoxList: [<Box: {'item': 0}>, <Box: {'item': 1}>, ...

      my_boxlist[5].item
      # 5


**to_list**

Transform a `BoxList` and all components back into regular `list` and `dict` items.

.. code:: python

      my_boxlist.to_list()
      # [{'item': 0},
      #  {'item': 1},
      #  ...

SBox
====

Shorthand Box, aka SBox for short(hand), has the properties `json`, `yaml` and
`dict` for faster access than the regular `to_dict()` and so on.

.. code:: python

      from box import SBox

      sb = SBox(test=True)
      sb.json
      # '{"test": true}'

Note that in this case, `json` has no default indent, unlike `to_json`.

ConfigBox
=========

A Box with additional handling of string manipulation generally found in
config files.

test_config.ini

.. code:: ini

        [General]
        example=A regular string

        [Examples]
        my_bool=yes
        anint=234
        exampleList=234,123,234,543
        floatly=4.4


With the combination of `reusables` and `ConfigBox` you can easily read python
config values into python types. It supports `list`, `bool`, `int` and `float`.

.. code:: python

    import reusables
    from box import ConfigBox

    config = ConfigBox(reusables.config_dict("test_config.ini"))
    # <ConfigBox: {'General': {'example': 'A regular string'},
    # 'Examples': {'my_bool': 'yes', 'anint': '234', 'examplelist': '234,123,234,543', 'floatly': '4.4'}}>

    config.Examples.list('examplelist')
    # ['234', '123', '234', '543']

    config.Examples.float('floatly')
    # 4.4

Thoughts
========

"Awesome time (and finger!) saver." - Zenlc2000

"no thanks." - burnbabyburn



"I just prefer plain dictionaries." - falcolas

Thanks
======

A huge thank you to everyone that has given features and feedback over the years to Box!

Check out everyone that has contributed_.

A special thanks to Python Software Foundation, and PSF-Trademarks Committee, for official approval to use the Python logo on the `Box` logo!

Also special shout-out to PythonBytes_, who featured Box on their podcast.

History
=======

Feb 2014: Inception
-------------------

`Box` was first created_ under the name `Namespace` in the reusables_ package.
Years of usage and suggestions helped mold it into the largest section of
the reusables library.

Mar 2017: Box 1.0
-----------------

After years of upgrades it became clear it was used more than most other parts of
the reusables library of tools. `Box` become its own package.

Mar 2017: BoxLists
------------------

2.0 quickly followed 1.0, adding BoxList to allow for further dot notations
while down in lists. Also added the handy `to_json` and `to_yaml` functionality.

May 2017: Options
-----------------

Box 3.0 brought a lot of options to the table for maximum customization. From
allowing you to freeze the box or just help you find your attributes when
accessing them by dot notation.

Dec 2019: 2.7 EOL
-----------------

Box 4.0 was made with python 2.x out of mind. Everything from f-strings to
type-hinting was added to update the package. The modules grew large enough
to separate the different objects into their own files and test files.


License
=======

MIT License, Copyright (c) 2017-2020 Chris Griffith. See LICENSE file.


.. |BoxImage| image:: https://raw.githubusercontent.com/cdgriffith/Box/master/box_logo.png
   :target: https://github.com/cdgriffith/Box
.. |BuildStatus| image:: https://travis-ci.org/cdgriffith/Box.png?branch=master
   :target: https://travis-ci.org/cdgriffith/Box
.. |CoverageStatus| image:: https://img.shields.io/coveralls/cdgriffith/Box/master.svg?maxAge=2592000
   :target: https://coveralls.io/r/cdgriffith/Box?branch=master
.. |DocStatus| image:: https://readthedocs.org/projects/box/badge/?version=latest
   :target: http://box.readthedocs.org/en/latest/index.html
.. |PyPi| image:: https://img.shields.io/pypi/v/python-box.svg?maxAge=2592000
   :target: https://pypi.python.org/pypi/python-box/
.. |License| image:: https://img.shields.io/pypi/l/python-box.svg
   :target: https://pypi.python.org/pypi/python-box/

.. _PythonBytes: https://pythonbytes.fm/episodes/show/19/put-your-python-dictionaries-in-a-box-and-apparently-python-is-really-wanted
.. _contributed: AUTHORS.rst
.. _`Wrapt Documentation`: https://wrapt.readthedocs.io/en/latest
.. _reusables: https://github.com/cdgriffith/reusables#reusables
.. _created: https://github.com/cdgriffith/Reusables/commit/df20de4db74371c2fedf1578096f3e29c93ccdf3#diff-e9a0f470ef3e8afb4384dc2824943048R51
