"""令牌桶限流器。全局单例，所有请求共享。"""
import asyncio
import time


class TokenBucket:
    def __init__(self, rate: float):
        self.rate = rate
        self.capacity = rate
        self.tokens = rate
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self.last_refill
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_refill = now

                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                
                # 锁内只计算需要等待的时间
                wait = (1 - self.tokens) / self.rate

            # 释放锁之后再去 sleep，防止阻塞其他协程，睡醒后回到 while 顶部重试
            await asyncio.sleep(wait)


amap_limiter = TokenBucket(rate=2)   # 高德QPS上限 3，留点余量设为 2