import os
import sys
import json

from box import Box
from addict import Dict
from dotmap import DotMap
from reusables import time_it
from memory_profiler import profile


if sys.version_info < (3, 0):
    from io import open

test_root = os.path.dirname(__file__)
hearth = os.path.join(test_root, "data", "hearthstone_cards.json")


@time_it(message="addict took {seconds:.5f} seconds to load")
def load_addict():
    with open(hearth, encoding="utf-8") as f:
        return Dict(json.load(f))


@time_it(message="DotMap took {seconds:.5f} seconds to load")
def load_dotmap():
    with open(hearth, encoding="utf-8") as f:
        return DotMap(json.load(f))


@time_it(message="Box    took {seconds:.5f} seconds to load")
def load_box():
    return Box.from_json(filename=hearth, encoding="utf-8")


@time_it(message="dict   took {seconds:.5f} seconds to load")
def load_dict():
    with open(hearth, encoding="utf-8") as f:
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


@profile()
def memory_test():
    ad = load_addict()
    dm = load_dotmap()
    bx = load_box()
    dt = load_dict()

    lookup(ad)
    lookup(ad)

    lookup(dm)
    lookup(dm)

    lookup(bx)
    lookup(bx)

    lookup(dt)
    lookup(dt)

    addict_insert(ad)
    dotmap_insert(dm)
    box_insert(bx)
    dict_insert(dt)


if __name__ == '__main__':
    memory_test()
    """
        Line #    Mem usage    Increment   Line Contents
    ================================================
        85     28.9 MiB      0.0 MiB   @profile()
        86                             def memory_test():
        87     41.9 MiB     13.0 MiB       ad = load_addict()
        88     57.1 MiB     15.2 MiB       dm = load_dotmap()
        89     64.5 MiB      7.4 MiB       bx = load_box()
        90     74.6 MiB     10.1 MiB       dt = load_dict()
        91                             
        92     74.6 MiB      0.0 MiB       lookup(ad)
        93     74.6 MiB      0.0 MiB       lookup(ad)
        94                             
        95     74.6 MiB      0.0 MiB       lookup(dm)
        96     74.6 MiB      0.0 MiB       lookup(dm)
        97                             
        98     75.6 MiB      1.0 MiB       lookup(bx)
        99     75.6 MiB      0.0 MiB       lookup(bx)
       100                             
       101     75.6 MiB      0.0 MiB       lookup(dt)
       102     75.6 MiB      0.0 MiB       lookup(dt)
       103                             
       104     76.0 MiB      0.3 MiB       addict_insert(ad)
       105     76.6 MiB      0.6 MiB       dotmap_insert(dm)
       106     76.8 MiB      0.2 MiB       box_insert(bx)
       107     76.9 MiB      0.2 MiB       dict_insert(dt)
   
    """

    print("Python {}\n".format(sys.version.split(" ")[0]))

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