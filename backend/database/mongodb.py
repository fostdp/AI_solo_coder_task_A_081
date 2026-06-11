from pymongo import MongoClient
from config import get_settings

settings = get_settings()

_client = None
_db = None


def get_mongo_db():
    global _client, _db
    if _client is None:
        _client = MongoClient(settings.mongodb_url)
        _db = _client[settings.mongodb_db_name]
    return _db


def get_collection(name):
    db = get_mongo_db()
    return db[name]


def close_mongo():
    global _client
    if _client:
        _client.close()
        _client = None
