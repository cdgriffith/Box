|BoxImage|

Python dictionaries with recursive dot notation access.

.. code:: python

         from box import Box

         movie_data = {
           "movies": {
             "Spaceballs": {
               "imdb stars": 7.1,
               "rating": "PG",
               "length": 96,
               "director": "Mel Brooks",
               "stars": [{"name": "Mel Brooks", "imdb": "nm0000316", "role": "President Skroob"},
                         {"name": "John Candy","imdb": "nm0001006", "role": "Barf"},
                         {"name": "Rick Moranis", "imdb": "nm0001548", "role": "Dark Helmet"}
               ]
             },
             "Robin Hood: Men in Tights": {
               "imdb stars": 6.7,
               "rating": "PG-13",
               "length": 104,
               "director": "Mel Brooks",
               "stars": [
                         {"name": "Cary Elwes", "imdb": "nm0000144", "role": "Robin Hood"},
                         {"name": "Richard Lewis", "imdb": "nm0507659", "role": "Prince John"},
                         {"name": "Roger Rees", "imdb": "nm0715953", "role": "Sheriff of Rottingham"},
                         {"name": "Amy Yasbeck", "imdb": "nm0001865", "role": "Marian"}
               ]
             }
           }
         }

         movie_box = Box(movie_data)

         movie_box.movies.Robin_Hood_Men_in_Tights.imdb_stars
         # 6.7

         movie_box.movies.Spaceballs.stars[0].name
         # 'Mel Brooks'

         # All new dict and lists added to a Box or BoxList object are converted
         movie_box.movies.Spaceballs.stars.append({"name": "Bill Pullman", "imdb": "nm0000597", "role": "Lone Starr"})
         movie_box.movies.Spaceballs.stars[-1].role
         # 'Lone Starr'

Install
-------

|BuildStatus| |CoverageStatus| |License| |PyPi| |DocStatus|

.. code:: bash

        pip install python-box

Box is tested on python 2.7, 3.3+ and PyPy2.
If it does not install with this command, please
open a github issue with the error you are experiencing!

If you want to be able to use the `to_yaml` functionality make sure to
install `PyYAML` or `ruamel.yaml` as well.

Overview
--------

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

Box
~~~

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

#### Conversion Box

By default, Box is now a `conversion_box` (can be disabled with `Box(conversion_box=False)`
that adds automagic attribute access for keys that could not normally be attributes.

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


#### Frozen Box

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

#### Default Box

It's boxes all the way down.

.. code:: python

      empty_box = Box(default_box=True)

      empty_box.a.b.c.d.e.f.g
      # <Box: {}>

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



BoxList
~~~~~~~

To make sure all items added to lists in the box are also converted, all lists
are covered into `BoxList`. It's possible to
initiate these directly and use them just like a `Box`.

.. code:: python

      from box import BoxList

      my_boxlist = BoxList({'item': x} for x in range(10))
      #  <BoxList: [<Box: {'item': 0}>, <Box: {'item': 1}>, ...

      my_boxlist[5].item
      5


**to_list**

Transform a `BoxList` and all components back into regular `list` and `dict` items.

.. code:: python

      my_boxlist.to_list()
      # [{'item': 0},
      #  {'item': 1},
      #  ...


LightBox
~~~~~~~~

`LightBox` does not examine lists, but only converts dictionary objects.

.. code:: python

        from box import LightBox

        light_box = LightBox({'my_list': [{'item': 1}, {'item': 2}])

        light_box.my_list
        [{'item': 1}, {'item': 2}]


ConfigBox
~~~~~~~~~

This module has support for
a `ConfigBox`. It is based on top of `LightBox` as there are no lists of dicts
to dive into in a configuration file.

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




License
-------

MIT License, Copyright (c) 2017 Chris Griffith. See LICENSE file.


.. |BoxImage| image:: https://raw.githubusercontent.com/cdgriffith/Box/development/box_logo.png
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
