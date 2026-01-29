"""
MongoDB database models and utilities for IDS Backend.
Provides connection, collections, and serialization for alerts, traffic stats, and user activities.
"""

import logging
from typing import Any, Dict, Optional

from bson import ObjectId
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

logger = logging.getLogger(__name__)

# Module-level client and db (set by init_db)
_client: Optional[MongoClient] = None
_db: Optional[Database] = None

# Collections (set after init_db; accessed as properties to allow lazy init)
alerts_collection: Optional[Collection] = None
traffic_stats_collection: Optional[Collection] = None
user_activities_collection: Optional[Collection] = None
pcap_analyses_collection: Optional[Collection] = None


def _get_config_value(config: Any, key: str, default: str = "") -> str:
    """Get config value from object or dict."""
    if hasattr(config, key):
        return getattr(config, key) or default
    if isinstance(config, dict):
        return config.get(key, default) or default
    return default


def get_client(config: Any) -> MongoClient:
    """Return a MongoClient for the given config (does not use module-level client)."""
    uri = _get_config_value(config, "MONGODB_URI", "mongodb://localhost:27017/")
    return MongoClient(uri)


def get_db(config: Any) -> Database:
    """Return the MongoDB database for the given config."""
    client = get_client(config)
    db_name = _get_config_value(config, "MONGODB_DATABASE_NAME", "ids_db")
    return client.get_database(db_name)


def init_db(app: Any) -> None:
    """
    Initialize MongoDB connection and collections from Flask app config.
    Called at application startup.
    """
    global _client, _db, alerts_collection, traffic_stats_collection, user_activities_collection, pcap_analyses_collection
    try:
        config = app.config if hasattr(app, "config") else app
        uri = _get_config_value(config, "MONGODB_URI", "mongodb://localhost:27017/")
        db_name = _get_config_value(config, "MONGODB_DATABASE_NAME", "ids_db")
        _client = MongoClient(uri)
        _db = _client.get_database(db_name)
        alerts_collection = _db["alerts"]
        traffic_stats_collection = _db["traffic_stats"]
        user_activities_collection = _db["user_activities"]
        pcap_analyses_collection = _db["pcap_analyses"]
        # Verify connection
        _client.admin.command("ping")
        logger.info("MongoDB connection initialized: database=%s", db_name)
    except Exception as e:
        logger.warning("MongoDB init failed (some features may be disabled): %s", e)
        _client = None
        _db = None
        alerts_collection = None
        traffic_stats_collection = None
        user_activities_collection = None
        pcap_analyses_collection = None


def to_object_id(value: Any) -> ObjectId:
    """Convert string or value to ObjectId; raise ValueError if invalid."""
    if value is None:
        raise ValueError("Cannot convert None to ObjectId")
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(str(value))
    except Exception as e:
        raise ValueError(f"Invalid ObjectId: {value}") from e


def _doc_to_dict(doc: Optional[Dict], id_key: str = "id") -> Dict[str, Any]:
    """Convert a MongoDB document to a JSON-serializable dict, with _id as id_key."""
    if doc is None:
        return {}
    out = dict(doc)
    if "_id" in out:
        out[id_key] = str(out.pop("_id"))
    return out


def alert_to_dict(alert: Optional[Dict]) -> Dict[str, Any]:
    """Convert alert document to JSON-serializable dict."""
    return _doc_to_dict(alert, "id")


def traffic_stat_to_dict(stat: Optional[Dict]) -> Dict[str, Any]:
    """Convert traffic stat document to JSON-serializable dict."""
    return _doc_to_dict(stat, "id")


def user_activity_to_dict(activity: Optional[Dict]) -> Dict[str, Any]:
    """Convert user activity document to JSON-serializable dict."""
    return _doc_to_dict(activity, "id")


def pcap_analysis_to_dict(doc: Optional[Dict]) -> Dict[str, Any]:
    """Convert PCAP analysis document to JSON-serializable dict (id instead of _id)."""
    return _doc_to_dict(doc, "id")
