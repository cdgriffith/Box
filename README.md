# Box

Python dictionaries with recursive dot notation access.

```python
from box import Box

my_box = Box({"owner": "Mr. Powers",
              "contents": ["blue crushed-velvet suit",
                           "frilly lace crava",
                           "gold medallion with peace symbol",
                           "Italian shoes",
                           "tie-dyed socks"],
              "affiliates": {
                  "Vanessa": "Sexy",
                  "Dr Evil": "Not groovy",
                  "Scott Evil": "Doesn't want to take over family business"
              }})

my_box.affiliates.Vanessa == my_box['affiliates']['Vanessa'] 

my_box.funny_line = "They tried to steal my lucky charms!"

my_box['funny_line']
# 'They tried to steal my luck charms!'

my_box.credits = {'Austin Powers': "Mike Myers", "Vanessa Kensington": "Elizabeth Hurley"}
# <Box: {'Austin Powers': 'Mike Myers', 'Vanessa Kensington': 'Elizabeth Hurley'}>
```

## Install 

```
pip install boxing
```

(Don't see a box package, but alas, can't claim the name for some reason.)

Box is tested on python 2.6+, 3.3+ and PyPy2, and should work on other 
interpreters as well. If  it does not install with this command, please
open a ticket with the error you are experiencing!

## Overview

This module provides two main classes `Box` and `ConfigBox`. 
They are designed to be easy drop in replacements for dictionaries, 
with the latter having tools for dealing with config files. 

`Box` is designed to transparently act as a dictionary, thanks to Python's
duck typing capabilities, but add dot notation access like classes do. Any sub
dictionaries or ones set after initiation will be automatically converted to 
a `Box` object. You can always run `.to_dict()` on it to return the object 
and all sub objects back into a regular dictionary. 

```python
# Will only convert outermost object
dict(my_box)
# {'owner': 'Mr. Powers', 'affiliates': <Box: {'Vanessa': 'Sexy', 
# 'Dr Evil': 'Not groovy', 'Scott Evil': "Doesn't want to take over family business"}>, 
# 'credits': <Box: {'Austin Powers': 'Mike Myers', 'Vanessa Kensington': 'Elizabeth Hurley'}>}

my_box.to_dict()
# {'owner': 'Mr. Powers', 'affiliates': {'Vanessa': 'Sexy', 
# 'Dr Evil': 'Not groovy', 'Scott Evil': "Doesn't want to take over family business"}, 
# 'credits': {'Austin Powers': 'Mike Myers', 'Vanessa Kensington': 'Elizabeth Hurley'}}
```

This module was pulled from my other project, reusables, so it has support for
a `ConfigBox`.

test_config.ini
```ini
[General]
example=A regular string

[Section 2]
my_bool=yes
anint=234
exampleList=234,123,234,543
floatly=4.4
```

With the combination of reusables and ConfigBox you can easily read python 
config values into python types. It supports `list`, `bool`, `int` and `float`.

```python
import reusables
from box import ConfigBox

config = ConfigBox(reusables.config_dict("test_config.ini"))
# <ConfigBox: {'General': {'example': 'A regular string'},
# 'Examples': {'my_bool': 'yes', 'anint': '234', 'examplelist': '234,123,234,543', 'floatly': '4.4'}}>

config.Examples.list('examplelist')
# ['234', '123', '234', '543']

config.Examples.float('floatly')
# 4.4
```


## Competition

**Bunch**

Bunch is similar in functionality, but does not work recursively. 

**EasyDict**

EasyDicts `str` and `repr` print a dictionary look alike, `Box` makes it clear in repr 
that it is a unique object. EasyDict not have a way to make sub items recursively 
back to dictionary. 

**addict**

Is a default dictionary and goes into lists and makes those into sub objects. 


