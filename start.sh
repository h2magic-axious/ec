#!/usr/bin/env bash

DIR=`pwd`
HOST=0.0.0.0
PORT=3333

kill -9 `lsof -i:$PORT -t`

cd $DIR

source venv/bin/activate

uvicorn server:app --host $HOST --port $PORT --reload
