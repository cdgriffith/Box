|Box|

Python dictionaries with recursive dot notation access.

.. code:: python

        from box import Box

        my_box = Box(
            {"owner": "Mr. Powers",
             "contents": [{"qty": 1, "item": "blue crushed-velvet suit"},
                          {"qty": 1, "item": "frilly lace crava"},
                          {"qty": 1, "item": "gold medallion with peace symbol"},
                          {"qty": 1, "item": "Swedish-made enlarger pump"},
                          {"qty": 1, "item": "credit card receipt for Swedish-made enlarger pump, "
                                             "signed Austin Powers."},
                          {"qty": 1, "item": "warranty card for Swedish-made enlarger pump, "
                                             "filled out by Austin Powers."},
                          {"qty": 1, "item": "book, Swedish-Made Enlarger Pumps and Me"}],
             "affiliates": {
                 "Vanessa": "Sexy",
                 "Dr Evil": "Not groovy",
                 "Scott Evil": "Doesn't want to take over family business"}
            })

        my_box.affiliates.Vanessa == my_box['affiliates']['Vanessa']

        my_box.contents[0].item
        'blue crushed-velvet suit'

        # Here's something that no other library supports (that I know of)
        # Automatic creation of Boxes in sub-lists
        my_box.contents.append({"qty": 1, "item": "tie-dyed socks"})
        my_box.contents[-1].item
        'tie-dyed socks'

        # Box object is callable, and returns a tuple of available keys
        my_box()
        ('owner', 'contents', 'affiliates')

        my_box.funny_line = "They tried to steal my lucky charms!"

        my_box['funny_line']
        'They tried to steal my luck charms!'

        my_box.credits = {'Austin Powers': "Mike Myers", "Vanessa Kensington": "Elizabeth Hurley"}
        # <Box: {'Austin Powers': 'Mike Myers', 'Vanessa Kensington': 'Elizabeth Hurley'}>

        my_box.to_yaml()  # .to_json() also available
        # owner: Mr. Powers
        # affiliates:
        #   Dr Evil: Not groovy
        #   Scott Evil: Doesn't want to take over family business
        #   Vanessa: Sexy
        # contents:
        # - item: blue crushed-velvet suit
        #   qty: 1
        # - item: frilly lace crava
        #   qty: 1
        # - item: gold medallion with peace symbol
        #   qty: 1
        # ...


Install
-------

|BuildStatus| |CoverageStatus|

.. code:: bash

        pip install python-box

Box is tested on python 2.6+, 3.3+ and PyPy2, and should work on other 
interpreters as well. If  it does not install with this command, please
open a ticket with the error you are experiencing!

If you want to be able to use the `to_yaml` functionality make sure to
install `PyYAML` as well.

Overview
--------

`Box` is designed to be easy drop in replacements for dictionaries,
with the latter having tools for dealing with config files. 

`Box` is designed to transparently act as a dictionary, thanks to Python's
duck typing capabilities, but add dot notation access like classes do. Any sub
dictionaries or ones set after initiation will be automatically converted to 
a `Box` object. You can always run `.to_dict()` on it to return the object 
and all sub objects back into a regular dictionary. 


.. code:: python

        del my_box.contents # Lets keep this short

        my_box.to_dict()
        {'affiliates':
                {'Dr Evil': 'Not groovy',
                 'Scott Evil': "Doesn't want to take over family business",
                 'Vanessa': 'Sexy'},
         'owner': 'Mr. Powers'}

        # Will only convert outermost object
        dict(my_box)
        # {'owner': 'Mr. Powers',
        #  'affiliates': <Box: {'Vanessa': 'Sexy',
        #                      'Dr Evil': 'Not groovy',
        #                      'Scott Evil': "Doesn't want to take over family business"}>}}


`Box` was originally named `Namespaces` in the `reusables` project, created
over three years ago. `LightBox` is the direct dependant of `Namespace`, and
should operate as a near drop in replacement if you are switching over.

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

Any time a list or dict is added to a `Box`, it is converted into a `BoxList`
or `Box` respectively.

`Box` includes helper functions to transform it back into `dict`,
and into `JSON` or `YAML` strings.

**to_dict**

Return the `Box` object and all sub `Box` and `BoxList`
objects into regular dicts and list.


.. code:: python

        my_box.to_dict()
        {'owner': 'Mr. Powers',
         'affiliates': {'Vanessa': 'Sexy',
                        'Dr Evil': 'Not groovy',
                        'Scott Evil': "Doesn't want to take over family business"}}


**to_json**

Available on all systems that support the default `json` library.::

   to_json(filename=None, indent=4, **json_kwargs)
       Transform the Box object into a JSON string.

       :param filename: If provided will save to file
       :param indent: Automatic formatting by indent size in spaces
       :param json_kwargs: additional arguments to pass to json.dump(s)
       :return: string of JSON or return of `json.dump`

.. code:: python

        my_box.to_json()
        {
            "owner": "Mr. Powers",
            "affiliates": {
                "Vanessa": "Sexy",
                "Dr Evil": "Not groovy",
                "Scott Evil": "Doesn't want to take over family business"
            }
        }


**to_yaml**

Only available if `PyYAML` or `ruamel.yaml` is installed (not automatically installed via pip or `setup.py`)::

   to_yaml(filename=None, default_flow_style=False, **yaml_kwargs)
       Transform the Box object into a YAML string.

       :param filename:  If provided will save to file
       :param default_flow_style: False will recursively dump dicts
       :param yaml_kwargs: additional arguments to pass to yaml.dump
       :return: string of YAML or return of `yaml.dump`


.. code::

        my_box.to_yaml()
        affiliates:
          Dr Evil: Not groovy
          Scott Evil: Doesn't want to take over family business
          Vanessa: Sexy
        owner: Mr. Powers

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



Similar Libraries
-----------------

**EasyDict**

* EasyDict not have a way to make sub items recursively back into a regular dictionary.
* Adding new dicts to lists in the dictionary does not make them into EasyDicts.
* Both EasyDicts `str` and `repr` print a dictionary look alike, `Box` makes it clear in `repr` that it is a Box object.

**addict**

* Adding new dicts or lists does not make them into `addict.Dict` objects.
* Is a default dictionary, as in it will never fail on lookup.
* Both `addict.Dict`'s `str` and `repr` print a dictionary look alike, `Box` makes it clear in `repr` that it is a Box object.


License
-------

MIT License, Copyright (c) 2017 Chris Griffith. See LICENSE file.


.. |Box| image:: https://raw.githubusercontent.com/cdgriffith/Box/development/box_logo.png
   :target: https://github.com/cdgriffith/Box
.. |BuildStatus| image:: https://travis-ci.org/cdgriffith/Box.png?branch=master
   :target: https://travis-ci.org/cdgriffith/Box
.. |CoverageStatus| image:: https://img.shields.io/coveralls/cdgriffith/Box/master.svg?maxAge=2592000
   :target: https://coveralls.io/r/cdgriffith/Box?branch=master
