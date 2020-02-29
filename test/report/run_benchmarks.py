import time
import os
import json
from pathlib import Path
import random
import string
import sys
import platform
import multiprocessing
from datetime import datetime
from pprint import pprint

import requests

try:
    from ruamel import yaml

    yaml_lib = 'ruamel.yaml'
except ImportError:
    import yaml

    yaml_lib = 'PyYAML'
import toml

from box import Box, BoxError
import box

iterations = 10_000


def timer(func, *args, **kwargs):
    start_time = time.perf_counter()
    func(*args, **kwargs)
    return float(f'{time.perf_counter() - start_time:.6f}')


def lookup(obj):
    for k in obj:
        obj[k]


def get_lookup(obj):
    for k in obj:
        obj.get(k)


def box_insert(bx):
    for i in range(iterations):
        bx["new {}".format(i)] = {'a': i}


def attr_lookup(obj):
    for k in obj:
        getattr(obj, k)


def pop(obj, items):
    for k in items:
        obj.pop(k)


def delete(obj, items):
    for k in items:
        del obj[k]


def delete_attr(obj, items):
    for k in items:
        delattr(obj, k)


def set_item(obj, sl, il):
    for i, key in enumerate(sl):
        obj[key] = il[i]


def set_attr(obj, sl, il):
    for i, key in enumerate(sl):
        setattr(obj, key, il[i])


unique_random = set()


def random_string():
    key = ''.join(random.choices(string.printable + string.digits, k=random.randint(5, 40)))
    if key in unique_random:
        return random_string()
    unique_random.add(key)
    return key


test = dict((random_string(), 0) for i in range(iterations))
merge_update_dict = dict((random_string(), 0) for i in range(iterations))
update_dict = dict((random_string(), 0) for i in range(iterations))
set_list = [random_string() for _ in range(iterations)]
set_attr_list = [random_string() for _ in range(iterations)]
item_list = [random_string() for _ in range(iterations)]

card_version = '25770'
card_cache = Path(os.path.dirname(__file__), f'hearthstone_{card_version}.json')
report_name = f'box_{box.__version__}_report_{datetime.now().isoformat().replace(":", "-")}.json'
if not card_cache.exists():
    print("Downloading hearthstone card data")
    req = requests.get(f"https://api.hearthstonejson.com/v1/{card_version}/all/cards.json")
    print(f"Download complete, saving to cache file {card_cache}")
    data = {'cards': req.json()}
    card_cache.write_text(json.dumps(data))
    print("Data saved locally for faster")
else:
    data = json.loads(card_cache.read_text())
data.update(test)

start_time = time.perf_counter()
my_box = Box(data)
load_time = time.perf_counter() - start_time

if box.__version__.startswith('4'):
    mu = my_box.merge_update
else:
    mu = my_box.update

results = Box(
    settings=Box(
        box_version=box.__version__,
        hearthstone_card_version=card_version,
        yaml_library=yaml_lib,
        yaml_version=yaml.__version__,
        toml_version=toml.__version__,
        iterations=iterations
    ),
    machine_specs=Box(
        python_version=".".join(str(x) for x in list(sys.version_info)[:3]),
        python_compiler=platform.python_compiler(),
        python_implimentation=platform.python_implementation(),
        arch=platform.architecture(),
        processor=platform.processor(),
        cpu_count=multiprocessing.cpu_count()
    )
)

try:
    benchmarks = Box(
        load=load_time,
        insert=timer(box_insert, my_box),
        update_merge=timer(mu, merge_update_dict),
        update=timer(my_box.update, update_dict),
        lookup=timer(lookup, my_box),
        lookup_get=timer(get_lookup, my_box),
        lookup_atr=timer(attr_lookup, my_box),
        pop=timer(pop, my_box, merge_update_dict.keys()),
        delete=timer(delete, my_box, update_dict.keys()),
        delete_attr=timer(delete_attr, my_box, test.keys()),
        set_item=timer(set_item, my_box, set_list, item_list),
        set_attr=timer(set_attr, my_box, set_attr_list, item_list),
        # to_json=timer(my_box.to_json),
        # to_yaml=timer(my_box.to_yaml),
        # to_dict=timer(my_box.to_dict),
    )
    results.benchmarks = benchmarks
except BoxError as err:
    report = Path(os.path.dirname(__file__), f"failed-{report_name}.json")
    print(f"Error while running test: {err}")
    config = Box(test=test, item_list=item_list, update_dict=update_dict, merge_update_dict=merge_update_dict,
                 set_list=set_list, set_attr_list=set_attr_list)
    config.to_json(filename=Path(os.path.dirname(__file__), f"config-{report_name}.json"))
else:
    report = Path(os.path.dirname(__file__), report_name)

pprint(results)
results.to_json(filename=report, indent=2)

# KeyError: '\'!?\x0c"='
# '@^-+0'
# '\x0c,`[$'

