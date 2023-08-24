import os
import random
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, ORJSONResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket

from reference import User, Room

BASE_DIR = Path(__file__).parent.absolute()
Template = Jinja2Templates(directory=BASE_DIR.joinpath("templates"))

# User Database
USER_DB: Dict[str, User] = dict()
# Room Database
ROOM_DB: Dict[str, Room] = dict()

app = FastAPI(docs_url=None, redoc_url="/docs", default_response_class=ORJSONResponse)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR.joinpath("static"))), name="static")


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


def check_whitelist(path):
    result = False
    if path in ("/join", "/favicon.ico", "/random", "/ws"):
        result = True

    if path.startswith("/static"):
        result = True

    return result


@app.middleware("http")
async def process_before_response(request: Request, call_next):
    status, token = has_pem(request)
    if check_whitelist(request.url.path):
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

    if key not in ROOM_DB:
        ROOM_DB[key] = Room(key)

    if sec not in USER_DB:
        USER_DB[sec] = User(sec)

    return {
        "sec": sec
    }


@app.get("/random")
async def random_key(request: Request):
    return os.urandom(32).hex()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return Template.TemplateResponse("index.html", {"request": request})


async def ws_handler(websocket: WebSocket):
    try:
        await websocket.accept()

        while True:
            data = await websocket.receive_json()

            key = data["key"]
            sec = data["sec"]
            op = data["op"]

            if not (room := ROOM_DB.get(key)):
                continue

            if not (user := USER_DB.get(sec)):
                continue

            if op == "join":
                user.websocket = websocket
                user.room = room

                room.users.append(user)
                await room.broadcast("【系统消息】\n有人加入")

            if op == "tolk":
                print(f"[{user.sec}]: {data['msg']}")
                await room.broadcast(f"【{user.sec}】\n{data['msg']}")

    except Exception as e:
        user = None
        for u in USER_DB.values():
            if u.websocket == websocket:
                user = u
                break

        if user:
            try:
                room = user.room
                room.users.remove(user)

                del USER_DB[user.sec]
                if room.is_empty():
                    del ROOM_DB[room.key]
                    del room
                else:
                    await room.broadcast("【系统消息】\n有人离开")

                del user
            except Exception as _e:
                print(_e)
        print(e)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_handler(websocket)
