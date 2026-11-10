"""
All interaction with MongoDB should be through this file!
We may be required to use a new database at any point.
"""
import os
from functools import wraps

import pymongo as pm

LOCAL = "0"
CLOUD = "1"

# Tests set GEODATA_DB to a test database (see common.mk):
DB_ENV = 'GEODATA_DB'
DEFAULT_DB = 'geodata2026'
SE_DB = os.environ.get(DB_ENV, DEFAULT_DB)

# Local MongoDB (e.g. the Docker container started with
# `docker run -d --name mongodb -p 27017:27017 mongo`).
# Set MONGO_URI to point somewhere else, e.g. mongodb://mongo:27017
# when the server itself runs in Docker Compose.
MONGO_URI_ENV = 'MONGO_URI'
DEFAULT_LOCAL_URI = 'mongodb://localhost:27017'

# Give up quickly if MongoDB is not running, instead of pymongo's
# default 30 seconds:
DB_TIMEOUT_MS = 2000

client = None

MONGO_ID = '_id'


def connect_db():
    """
    This provides a uniform way to connect to the DB across all uses.
    Returns a mongo client object... maybe we shouldn't?
    Also set global client variable.
    We should probably either return a client OR set a
    client global.
    """
    global client
    if client is None:  # not connected yet!
        print('Setting client because it is None.')
        if os.environ.get('CLOUD_MONGO', LOCAL) == CLOUD:
            password = os.environ.get('MONGO_PASSWD')
            if not password:
                raise ValueError('You must set your password '
                                 + 'to use Mongo in the cloud.')
            print('Connecting to Mongo in the cloud.')
            client = pm.MongoClient(f'mongodb+srv://gcallah:{password}'
                                    + '@koukoumongo1.yud9b.mongodb.net/'
                                    + '?retryWrites=true&w=majority')
        else:
            uri = os.environ.get(MONGO_URI_ENV, DEFAULT_LOCAL_URI)
            print(f"Connecting to Mongo locally at {uri}.")
            client = pm.MongoClient(uri,
                                    serverSelectionTimeoutMS=DB_TIMEOUT_MS)
    return client


def needs_connection(fn):
    """
    Decorate every function that uses the client: make sure we are
    connected to the DB first, then call the function.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        connect_db()
        return fn(*args, **kwargs)
    return wrapper


def is_db_up():
    """
    Returns True if the DB is up and running: we can connect and it
    answers a ping. Returns False (instead of raising) if it does not.
    """
    try:
        connect_db()
        client.admin.command('ping')
        return True
    except pm.errors.PyMongoError as err:
        print(f'Error connecting to MongoDB: {err}')
        return False


@needs_connection
def count(collection, filt=None, db=SE_DB) -> int:
    """
    Return how many docs in collection match the filter (all docs if
    no filter), without reading the docs themselves.
    """
    return client[db][collection].count_documents(filt or {})


def db_info() -> dict:
    """
    Describe which MongoDB we are set up to use and whether it is up.
    Never include the cloud password.
    """
    cloud = os.environ.get('CLOUD_MONGO', LOCAL) == CLOUD
    uri = None if cloud else os.environ.get(MONGO_URI_ENV,
                                            DEFAULT_LOCAL_URI)
    return {
        'location': 'cloud' if cloud else 'local',
        'uri': uri,
        'db': SE_DB,
        'up': is_db_up(),
    }


def convert_mongo_id(doc: dict):
    if MONGO_ID in doc:
        # Convert mongo ID to a string so it works as JSON
        doc[MONGO_ID] = str(doc[MONGO_ID])


@needs_connection
def create(collection, doc, db=SE_DB):
    """
    Insert a single doc into collection.
    """
    print(f'{db=}')
    return client[db][collection].insert_one(doc)


@needs_connection
def drop(collection, db=SE_DB):
    """
    Drop the whole collection, if it exists.
    """
    client[db][collection].drop()


@needs_connection
def read_one(collection, filt, db=SE_DB):
    """
    Find with a filter and return on the first doc found.
    Return None if not found.
    """
    for doc in client[db][collection].find(filt):
        convert_mongo_id(doc)
        return doc


@needs_connection
def delete(collection: str, filt: dict, db=SE_DB):
    """
    Find with a filter and return on the first doc found.
    """
    print(f'{filt=}')
    del_result = client[db][collection].delete_one(filt)
    return del_result.deleted_count


@needs_connection
def delete_many(collection: str, filt: dict, db=SE_DB):
    """
    Delete every doc matching the filter; return how many were deleted.
    """
    return client[db][collection].delete_many(filt).deleted_count


@needs_connection
def update(collection, filters, update_dict, db=SE_DB):
    return client[db][collection].update_one(filters, {'$set': update_dict})


@needs_connection
def read(collection, db=SE_DB, no_id=True) -> list:
    """
    Returns a list from the db.
    """
    ret = []
    for doc in client[db][collection].find():
        if no_id:
            del doc[MONGO_ID]
        else:
            convert_mongo_id(doc)
        ret.append(doc)
    return ret


def read_dict(collection, key, db=SE_DB, no_id=True) -> dict:
    recs = read(collection, db=db, no_id=no_id)
    recs_as_dict = {}
    for rec in recs:
        recs_as_dict[rec[key]] = rec
    return recs_as_dict


@needs_connection
def fetch_all_as_dict(key, collection, db=SE_DB):
    ret = {}
    for doc in client[db][collection].find():
        del doc[MONGO_ID]
        ret[doc[key]] = doc
    return ret
