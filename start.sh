#!/usr/bin/env bash

DIR=`pwd`
PORT=3333

kill -9 `lsof -i:3333 -t`

cd $DIR

source venv/bin/activate

uvicorn server:app --host 0.0.0.0 --port 3333
