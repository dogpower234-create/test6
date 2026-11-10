#!/bin/bash

export FLASK_ENV=development
export PROJ_DIR=$PWD
export DEBUG=1

# Use the local MongoDB unless told otherwise
# (set CLOUD_MONGO=1 and MONGO_PASSWD to use the cloud one;
# set MONGO_URI if the local one is not at mongodb://localhost:27017):
export CLOUD_MONGO=${CLOUD_MONGO:-0}

export PYTHONPATH=$(pwd):$PYTHONPATH

# Make sure MongoDB is up before starting the server:
if ! python -c 'import sys, data.db_connect as dbc; sys.exit(0 if dbc.is_db_up() else 1)'; then
    echo "MongoDB is not reachable. To start a local one with Docker:" >&2
    echo "    docker run -d --name mongodb -p 27017:27017 mongo" >&2
    echo "(or 'docker start mongodb' if you created it before)." >&2
    exit 1
fi

# run our server locally:
FLASK_APP=server.endpoints flask run --debug --host=127.0.0.1 --port=8000
