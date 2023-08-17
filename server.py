import asyncio
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

from starlette.websockets import WebSocket

from encrypt import Encryptor

BASE_DIR = Path(__file__).parent.absolute()
Template = Jinja2Templates(directory=BASE_DIR.joinpath("templates"))

PEM_MAP: Dict[str, Dict[str, Encryptor]] = defaultdict(dict)
WS_MAP: Dict[str, Dict[str, WebSocket]] = defaultdict(dict)

WS_LOCK = asyncio.Lock()

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
    PEM_MAP[key][sec] = (e := Encryptor())
    return {
        "rsa": e.serialize(),
        "sec": sec
    }


@app.get("/random")
async def random_key(request: Request):
    return os.urandom(32).hex()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return Template.TemplateResponse("index.html", {"request": request})


async def broadcast(key, msg):
    for ws in WS_MAP[key].values():
        await ws.send_text(msg)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            k = data['key']
            op = data['op']

            async with WS_LOCK:
                if op == "join":
                    WS_MAP[k][data["sec"]] = websocket
                    await broadcast(k, f"[{str_now()}] 有人加入")

                if op == "tolk":
                    await broadcast(k, f"[{str_now()}] {data['msg']}")

    except Exception as e:
        print(e)
