"""工具调用的内存缓存装饰器。"""
import time
from functools import wraps

_cache = {}
_CACHE_TTL = 600   # 10 分钟


def cached(ttl=_CACHE_TTL):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = (func.__name__, str(args), str(sorted(kwargs.items())))
            now = time.monotonic()

            if key in _cache:
                value, expire_at = _cache[key]
                if now < expire_at:
                    return value

            result = await func(*args, **kwargs)
            _cache[key] = (result, now + ttl)
            return result
        return wrapper
    return decorator