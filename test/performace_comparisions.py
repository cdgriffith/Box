import sys
import json

from box import Box
from addict import Dict
from dotmap import DotMap
from reusables import time_it


if sys.version_info < (3, 0):
    from io import open


@time_it(message="addict took {seconds:.5f} seconds to load")
def load_addict():
    with open("hearthstone_cards.json", encoding="utf-8") as f:
        return Dict(json.load(f))


@time_it(message="DotMap took {seconds:.5f} seconds to load")
def load_dotmap():
    with open("hearthstone_cards.json", encoding="utf-8") as f:
        return DotMap(json.load(f))


@time_it(message="Box    took {seconds:.5f} seconds to load")
def load_box():
    return Box.from_json(filename="hearthstone_cards.json", encoding="utf-8")


@time_it(message="dict   took {seconds:.5f} seconds to load")
def load_dict():
    with open("hearthstone_cards.json", encoding="utf-8") as f:
        return json.load(f)


@time_it(message="lookup took {seconds:.5f} seconds")
def lookup(obj):
    for k in obj:
        obj[k]


@time_it(message="Box to_dict    took {seconds:.5f} seconds")
def box_to_dict(bx):
    return bx.to_dict()


@time_it(message="addict to_dict took {seconds:.5f} seconds")
def addict_to_dict(ad):
    return ad.to_dict()


@time_it(message="DotMap toDict  took {seconds:.5f} seconds")
def dotmap_to_dict(dm):
    return dm.toDict()


@time_it(message="Box insert    took {seconds:.5f} seconds")
def box_insert(bx):
    for i in range(1000):
        bx["new {}".format(i)] = {'a': i}


@time_it(message="addict insert took {seconds:.5f} seconds")
def addict_insert(ad):
    for i in range(1000):
        ad["new {}".format(i)] = Dict(a=i)


@time_it(message="DotMap insert took {seconds:.5f} seconds")
def dotmap_insert(dm):
    for i in range(1000):
        dm["new {}".format(i)]['a'] = i


@time_it(message="dict insert   took {seconds:.5f} seconds")
def dict_insert(dt):
    for i in range(1000):
        dt["new {}".format(i)] = {'a': i}


if __name__ == '__main__':

    ad = load_addict()
    dm = load_dotmap()
    bx = load_box()
    dt = load_dict()

    """
    Python 3.6.0 
    
    addict took 0.24437 seconds to load
    DotMap took 0.17551 seconds to load
    Box    took 0.06552 seconds to load
    dict   took 0.06283 seconds to load
    """

    print("addict lookups")
    lookup(ad)
    lookup(ad)
    lookup(ad)
    print("DotMap lookups")
    lookup(dm)
    lookup(dm)
    lookup(dm)
    print("Box    lookups")
    lookup(bx)
    lookup(bx)
    lookup(bx)
    print("dict   lookups")
    lookup(dt)
    lookup(dt)
    lookup(dt)
    """
    addict lookups
    lookup took 0.00214 seconds
    lookup took 0.00111 seconds
    lookup took 0.00111 seconds
    DotMap lookups
    lookup took 0.00171 seconds
    lookup took 0.00123 seconds
    lookup took 0.00081 seconds
    Box    lookups
    lookup took 0.05007 seconds
    lookup took 0.00166 seconds
    lookup took 0.00154 seconds
    dict   lookups
    lookup took 0.00023 seconds
    lookup took 0.00011 seconds
    lookup took 0.00011 seconds
    
    """
    addict_to_dict(ad)
    dotmap_to_dict(dm)
    box_to_dict(bx)

    """
    addict to_dict took 0.05971 seconds
    DotMap toDict  took 0.05370 seconds
    Box to_dict    took 0.02280 seconds
    """

    addict_insert(ad)
    dotmap_insert(dm)
    box_insert(bx)
    dict_insert(dt)

    """
    addict insert took 0.00369 seconds
    DotMap insert took 0.00353 seconds
    Box insert    took 0.00128 seconds
    dict insert   took 0.00046 seconds
    """