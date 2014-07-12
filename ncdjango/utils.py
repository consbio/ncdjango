from bisect import bisect_left
from functools import wraps


def auto_memoize(func):
    """
    Based on django.util.functional.memoize. Automatically memoizes instace methods for the lifespan of an object.
    Only works with methods taking non-keword arguments. Note that the args to the function must be usable as
    dictionary keys. Also, the first argument MUST be self. This decorator will not work for functions or class
    methods, only object methods.
    """

    @wraps(func)
    def wrapper(*args):
        inst = args[0]
        inst._memoized_values = getattr(inst, '_memoized_values', {})
        key = (func, args[1:])
        if key not in inst._memoized_values:
            inst._memoized_values[key] = func(*args)
        return inst._memoized_values[key]
    return wrapper


def best_fit(li, value):
    """For a sorted list li, returns the closest item to value"""

    index = bisect_left(li, value)

    if index in (0, len(li)):
        return index

    if li[index] - value < value - li[index-1]:
        return index
    else:
        return index-1