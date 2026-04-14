import collections.abc
from typing import Dict, Iterable, List, Callable


def subset_dict(input: Dict, keys_to_include: List):
    """
        Returns the input dict but only includes the
        keys present in the key_to_include list
    """
    return dict(filter(lambda item: item[0] in keys_to_include, input.items()))

def subset_dict_inv(input: Dict, keys_to_include: List):
    """
        Returns the input dict but only includes the
        keys not present in the key_to_include list
    """
    return dict(filter(lambda item: item[0] not in keys_to_include, input.items()))

def subset_dict_lambda(input: Dict, func: Callable):
    """
        Returns the input dict but only includes the
        keys present in the key_to_include list
    """
    return dict(filter(func, input.items()))

def sentence_from_list(item_list: Iterable[str], use_or=False, only_commas=False):
    """
        Builds a string from a list of items, for example:

        input: [Fentanyl, Hydrocodone]

        output: "fentanyl, and hydrocodone"

        use_or: when set to true, the items will be join with 'or' instead of 'and'
    """
    output = ""
    for idx, item in enumerate(item_list):
        name = item
        if len(item_list) - 1 == 0:
            output += name
        elif idx >= len(item_list) - 1:
            if not only_commas:
                output = output.removesuffix(", ")
                output += f" {'and' if not use_or else 'or'} {name}"
            else:
                output += name
        else:
            output += f"{name}, "
    return output



class FrozenDict(collections.abc.Mapping):
    """
        Frozen (immutable) dictionary that supports hashing
        Source: https://stackoverflow.com/a/2705638
    """

    def __init__(self, *args, **kwargs):
        self._d = dict(*args, **kwargs)

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)

    def __getitem__(self, key):
        return self._d[key]

    def __hash__(self):
        return hash(tuple(sorted(self._d.items())))
