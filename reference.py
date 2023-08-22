import asyncio


class WithLock(asyncio.Lock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collections = dict()
