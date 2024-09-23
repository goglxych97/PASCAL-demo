# utils/cache_utils/cache_decorators.py
from functools import wraps


def slice_cache(maxsize=100):
    def decorator(func):
        cache = {}

        @wraps(func)
        def wrapper(self, slice_index, *args):
            key = (slice_index, args, self.canvas_view)
            if key not in cache:
                if len(cache) >= maxsize:
                    cache.pop(next(iter(cache)))
                cache[key] = func(self, slice_index, *args)
            return cache[key]

        def cache_clear():
            cache.clear()

        def cache_invalidate(slice_index):
            keys_to_remove = [key for key in cache if key[0] == slice_index]
            for key in keys_to_remove:
                del cache[key]

        wrapper.cache_clear = cache_clear
        wrapper.cache_invalidate = cache_invalidate
        return wrapper

    return decorator
