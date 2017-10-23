from collections import defaultdict
import itertools


class BiMap(object):
    def __init__(self, items):
        key_by_unique_name = {}
        unique_names = []
        first_index = defaultdict(lambda: itertools.count(1))
        for key, name in items:
            if name in key_by_unique_name:
                for index in first_index[name]:
                    unique_name = u'{} ({})'.format(name, index)
                    if unique_name not in key_by_unique_name:
                        break
            else:
                unique_name = name
            unique_names.append(unique_name)
            key_by_unique_name[unique_name] = key
        self.key_by_unique_name = key_by_unique_name
        self.unique_names = unique_names
