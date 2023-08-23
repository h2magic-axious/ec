import asyncio
import datetime
from typing import List

from starlette.websockets import WebSocket


def str_now():
    return datetime.datetime.now().strftime('%Y-%d-%m %H:%M:%S')


class WithLock(asyncio.Lock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collections = dict()


class User:
    def __init__(self, sec):
        self.sec = sec
        self.websocket: WebSocket | None = None
        self.room: Room | None = None

    async def send(self, message):
        text = f"[{str_now()}] {message}\n"
        if self.websocket and self.room:
            await self.websocket.send_text(text)


class Room:
    def __init__(self, key):
        self.key = key
        self.users: List[User] = list()

    async def broadcast(self, message):
        for user in self.users:
            await user.send(message)

    def is_empty(self):
        return len(self.users) == 0
