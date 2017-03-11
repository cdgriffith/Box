# Box

Python dictionaries with dot notation access. 

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
pip install box
```


## Competition

**Bunch**

Bunch is similar in functionality, but does not work recursively. 

**EasyDict**

Both str and repr print a dictionary look alike, box makes it clear in repr 
that it is a unique object. Does not have a way to make sub items recursively 
back to dictionary. 

**addict**

Is a default dictionary and goes into lists and makes those into sub objects. 


