#!/usr/bin/env bash

DIR=`pwd`

cd $DIR

source venv/bin/activate

uvicorn server:app --host 0.0.0.0 --port 3333
