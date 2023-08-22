import asyncio
import base64
import datetime
import os
import random
from collections import defaultdict
from typing import Dict, List
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
from fastapi.responses import HTMLResponse, ORJSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from starlette.websockets import WebSocket, WebSocketDisconnect
from reference import WithLock
from encrypt import Encryptor

BASE_DIR = Path(__file__).parent.absolute()
Template = Jinja2Templates(directory=BASE_DIR.joinpath("templates"))

# 用户的 ws 连接映射表
PERSONAL_WS_MAP = WithLock()
PERSONAL_WS_MAP.collections = defaultdict(dict)

# 用户的 密钥 映射表
PERSONAL_EC_MAP = WithLock()

# 房间的 密钥 映射表
ROOM_EC_MAP = WithLock()
# 房间用户表
ROOM_USER_MAP = WithLock()

app = FastAPI(docs_url=None, redoc_url="/docs", default_response_class=ORJSONResponse)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


def str_now():
    return datetime.datetime.now().strftime('%Y-%d-%m %H:%M:%S')


def try_to_do(func):
    def inner(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return True, result
        except Exception as e:
            print(e)
            return False, str(e)

    return inner


@try_to_do
def has_pem(request: Request):
    return request.cookies.get("pem")


@app.middleware("http")
async def process_before_response(request: Request, call_next):
    status, token = has_pem(request)
    if request.url.path not in ("/join", "/favicon.ico", "/random"):
        if not status or token is None:
            return RedirectResponse(url="/join", headers={"Context-Type": "text/html"})

    return await call_next(request)


@app.get("/join", response_class=HTMLResponse)
async def login(request: Request):
    return Template.TemplateResponse("join.html", {"request": request})


@app.post("/join")
async def join(request: Request):
    body = await request.json()
    key = body["key"]
    sec = os.urandom(random.randint(5, 10)).hex()

    async with ROOM_EC_MAP:
        if key not in ROOM_EC_MAP.collections:
            ROOM_EC_MAP.collections[key] = Encryptor()

        rsa0 = ROOM_EC_MAP.collections[key].private

    async with PERSONAL_EC_MAP:
        PERSONAL_EC_MAP.collections[sec] = Encryptor()
        rsa1 = PERSONAL_EC_MAP.collections[sec].public

    return {
        "rsa0": rsa0,
        "rsa1": rsa1,
        "sec": sec
    }


@app.get("/random")
async def random_key(request: Request):
    return os.urandom(32).hex()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return Template.TemplateResponse("index.html", {"request": request})


async def broadcast(key, msg):
    for ws in PERSONAL_WS_MAP.collections[key].values():
        await ws.send_text(msg)


async def ws_handler(websocket: WebSocket):
    try:
        await websocket.accept()

        while True:
            data = await websocket.receive_json()
            key = data["key"]
            sec = data["sec"]
            op = data["op"]

            async with ROOM_EC_MAP:
                room_encryptor = ROOM_EC_MAP.collections[key]

            async with PERSONAL_WS_MAP:
                if op == "join":
                    PERSONAL_WS_MAP.collections[key][sec] = websocket
                    websocket.sec = sec
                    websocket.room = key

                    text = room_encryptor.encrypt(f"[{str_now()}] 【系统消息】\n有人加入")
                    await broadcast(key, text)

                if op == "tolk":
                    async with PERSONAL_EC_MAP:
                        encryptor = PERSONAL_EC_MAP.collections[sec]

                    text = encryptor.decrypt(data["msg"])
                    encrypt_text = room_encryptor.encrypt(f"[{str_now()}] 【{sec}】\n{text}")

                    await broadcast(key, encrypt_text)
    except Exception as e:
        is_empty = False

        async with PERSONAL_WS_MAP:
            del PERSONAL_WS_MAP.collections[websocket.sec]

        async with ROOM_EC_MAP:
            room_encryptor = ROOM_EC_MAP.collections[websocket.room]
            text = room_encryptor.encrypt(f"[{str_now()}] 【系统消息】\n有人离开")
            await broadcast(websocket.room, text)

        print(e)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_handler(websocket)
