import sys
from pathlib import Path

from box import Box
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, Path(__file__).parent)

# from run_benchmarks import main
#
# report = main()

report = Box({'benchmarks': {'delete': 0.019694,
                'delete_attr': 0.038236,
                'insert': 0.587872,
                'load': 4.4412133,
                'lookup': 0.025484,
                'lookup_attr': 0.068396,
                'lookup_get': 0.039811,
                'pop': 0.027849,
                'set_attr': 0.415647,
                'set_item': 0.234755,
                'update': 0.199506,
                'update_merge': 0.224046},
 'machine_specs': {'arch': ('32bit', 'WindowsPE'),
                   'cpu_count': 16,
                   'processor': 'Intel64 Family 6 Model 158 Stepping 12, '
                                'GenuineIntel',
                   'python_compiler': 'MSC v.1916 32 bit (Intel)',
                   'python_implimentation': 'CPython',
                   'python_version': '3.8.0'},
 'settings': {'box_version': '4.2.2',
              'hearthstone_card_version': '25770',
              'iterations': 10000,
              'toml_version': '0.10.0',
              'yaml_library': 'ruamel.yaml',
              'yaml_version': '0.16.6'}})

benchmarks = ('lookup', 'lookup_get', 'lookup_attr', 'pop', 'delete', 'delete_attr')
y_pos = np.arange(len(benchmarks))

plt.bar(y_pos, [report.benchmarks[x] for x in benchmarks], align='center', color=['#236267', '#236267', '#236267', '#2C8437', '#2F4172', '#2F4172'])
plt.xticks(y_pos, benchmarks)
plt.ylabel('Seconds')
plt.title(f'{report.settings.iterations:,} Lookup and Delete Operations')
plt.show()

# benchmarks = ('set_item', 'set_attr', 'insert', 'update', 'update_merge')
# y_pos = np.arange(len(benchmarks))
#
# plt.bar(y_pos, [report.benchmarks[x] for x in benchmarks], align='center', color=['#403075', '#403075', '#403075', '#872D62', '#872D62'])
# plt.xticks(y_pos, benchmarks)
# plt.ylabel('Seconds')
# plt.title(f'{report.settings.iterations:,} Insert and Update Operations')
# plt.show()
