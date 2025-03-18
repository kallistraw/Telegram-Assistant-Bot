# Multi functional Telegram assistant bot.
# Copyright (c) 2025, Kallistra <kallistraw@gmail.com>
#
# This file is a part of <https://github.com/kallistraw/Telegram-Bot-Assistant>
# and is released under the "BSD-3-Clause License". Please read the full license in
# <https://github.com/kallistraw/Telegram-Assistant-Bot/blob/main/LICENSE>


class TempCache:
    def __init__(self, cache_dict=None):
        self.cache = cache_dict if cache_dict is not None else {}

    def set(self, key, value):
        self.cache[key] = value

    def get(self, key, default=None):
        return self.cache.get(key, default)

    def delete(self, key):
        self.cache.pop(key, None)

    def add_to_list2(self, key, item):
        if key not in self.cache:
            self.cache[key] = []

        if isinstance(item, list):
            self.cache[key].extend(x for x in item if x not in self.cache[key])
        elif item not in self.cache[key]:
            self.cache[key].append(item)

    def add_to_list(self, key, item):
        if key not in self.cache:
            self.cache[key] = []
        if isinstance(self.cache[key], list) and item not in self.cache[key]:
            self.cache[key].append(item)

    def remove_from_list(self, key, item):
        if key in self.cache and isinstance(self.cache[key], list):
            self.cache[key].remove(item)
            if not self.cache[key]:
                del self.cache[key]

    def set_dict_key(self, dict_key, sub_key, value):
        if dict_key not in self.cache:
            self.cache[dict_key] = {}
        if isinstance(self.cache[dict_key], dict):
            self.cache[dict_key][sub_key] = value

    def get_dict_key(self, dict_key, sub_key, default=None):
        return self.cache.get(dict_key, {}).get(sub_key, default)

    def delete_dict_key(self, dict_key, sub_key):
        if dict_key in self.cache and isinstance(self.cache[dict_key], dict):
            self.cache[dict_key].pop(sub_key, None)
            if not self.cache[dict_key]:
                del self.cache[dict_key]

    def add_to_tuple(self, key, item):
        if key not in self.cache:
            self.cache[key] = (item,)
        elif isinstance(self.cache[key], tuple) and item not in self.cache[key]:
            self.cache[key] += (item,)

    def remove_from_tuple(self, key, item):
        if key in self.cache and isinstance(self.cache[key], tuple):
            new_tuple = tuple(x for x in self.cache[key] if x != item)
            self.cache[key] = new_tuple
            if not new_tuple:
                del self.cache[key]

    def keys(self, iter: bool = False):
        keys = []
        if iter:
            for key in self.cache:
                keys.append(key)
        else:
            return list(self.cache.keys())
        # welp, i'm so dum, it's just the same thing...

    def clear(self):
        """Clear the entire cache."""
        self.cache.clear()


