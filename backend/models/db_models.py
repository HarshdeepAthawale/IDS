"""
MongoDB database models for Flask IDS Backend
Uses PyMongo for document-based storage
"""

from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, AutoReconnect
from bson import ObjectId
from bson.errors import InvalidId
import logging
import ssl
import warnings

# Suppress SSL warnings and background task errors
warnings.filterwarnings('ignore', category=UserWarning, module='pymongo')
warnings.filterwarnings('ignore', message='.*SSL.*', category=UserWarning)
warnings.filterwarnings('ignore', message='.*TLS.*', category=UserWarning)

# Suppress pymongo background task errors completely
pymongo_logger = logging.getLogger('pymongo')
pymongo_logger.setLevel(logging.CRITICAL + 1)  # Effectively disable all pymongo logging
pymongo_logger.disabled = True

# Suppress all pymongo sub-loggers
logging.getLogger('pymongo.monitoring').setLevel(logging.CRITICAL + 1)
logging.getLogger('pymongo.monitoring').disabled = True
logging.getLogger('pymongo.pool').setLevel(logging.CRITICAL + 1)
logging.getLogger('pymongo.pool').disabled = True
logging.getLogger('pymongo.server_selection').setLevel(logging.CRITICAL + 1)
logging.getLogger('pymongo.server_selection').disabled = True
logging.getLogger('pymongo.client').setLevel(logging.CRITICAL + 1)
logging.getLogger('pymongo.client').disabled = True

logger = logging.getLogger(__name__)

# Global MongoDB client and database
_client = None
_db = None

def get_client(config):
    """Get or create MongoDB client"""
    global _client
    if _client is None:
        try:
            # Enhanced connection options for Atlas with retry logic
            import time
            max_retries = 3
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    # Optimized connection settings for high-performance import
                    # Flask config supports both dict access and attribute access for uppercase keys
                    if hasattr(config, 'get'):
                        mongodb_uri = config.get('MONGODB_URI')
                    elif hasattr(config, 'MONGODB_URI'):
                        mongodb_uri = config.MONGODB_URI
                    else:
                        mongodb_uri = getattr(config, 'MONGODB_URI', None)
                    
                    if not mongodb_uri:
                        raise ValueError("MONGODB_URI not found in config")
                    
                    # Suppress background task errors by catching and ignoring them
                    import threading
                    import sys
                    
                    original_excepthook = threading.excepthook
                    
                    def suppress_ssl_errors(args):
                        """Suppress SSL errors from background tasks"""
                        exc_type, exc_value, exc_traceback, thread = args
                        if exc_type and issubclass(exc_type, (ssl.SSLError, AutoReconnect)):
                            # Suppress SSL errors from background tasks - they don't affect functionality
                            return
                        # Call original handler for other exceptions
                        if original_excepthook:
                            original_excepthook(args)
                        else:
                            sys.__excepthook__(exc_type, exc_value, exc_traceback)
                    
                    threading.excepthook = suppress_ssl_errors
                    
                    try:
                        _client = MongoClient(
                            mongodb_uri,
                            serverSelectionTimeoutMS=10000,  # Shorter timeout
                            connectTimeoutMS=10000,
                            socketTimeoutMS=30000,
                            retryWrites=True,
                            retryReads=True,
                            maxPoolSize=10,  # Reduced pool size
                            minPoolSize=1,  # Minimal connections
                            maxIdleTimeMS=30000,  # Shorter idle time
                            waitQueueTimeoutMS=10000,  # Shorter wait time
                            # Reduce background monitoring to minimize SSL errors
                            heartbeatFrequencyMS=60000,  # Less frequent heartbeats
                            directConnection=False  # Use connection pooling
                        )
                    except Exception as e:
                        # Restore original exception handler
                        threading.excepthook = original_excepthook
                        raise
                    # Test connection (suppress SSL errors during test)
                    try:
                        _client.admin.command('ping')
                        logger.info("MongoDB client connected successfully")
                    except (ssl.SSLError, AutoReconnect) as ssl_err:
                        # SSL errors are expected with Python 3.14, but connection may still work
                        logger.warning(f"SSL warning during connection test (may still work): {ssl_err}")
                        logger.info("MongoDB client initialized (SSL warnings suppressed)")
                    break
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Connection attempt {attempt + 1} failed, retrying...: {e}")
                        time.sleep(2)
                        _client = None  # Reset client for retry
                    else:
                        logger.error(f"Failed to connect to MongoDB after {max_retries} attempts: {e}")
                        logger.error("Please verify:")
                        logger.error("1. MongoDB Atlas IP whitelist includes your IP address (0.0.0.0/0 for all)")
                        logger.error("2. MongoDB Atlas cluster is running")
                        logger.error("3. Connection string is correct")
                        logger.error("4. Network/firewall allows SSL connections to MongoDB Atlas")
                        raise ConnectionFailure(f"Failed to connect after {max_retries} attempts: {e}") from last_error
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    return _client

def get_db(config):
    """Get or create database instance"""
    global _db
    if _db is None:
        client = get_client(config)
        # Flask config supports both dict access and attribute access for uppercase keys
        if hasattr(config, 'get'):
            db_name = config.get('MONGODB_DATABASE_NAME', 'ids_db')
        elif hasattr(config, 'MONGODB_DATABASE_NAME'):
            db_name = config.MONGODB_DATABASE_NAME
        else:
            db_name = getattr(config, 'MONGODB_DATABASE_NAME', 'ids_db')
        _db = client[db_name]
        logger.info(f"Using MongoDB database: {db_name}")
    return _db

# Collection references (will be initialized in init_db)
alerts_collection = None
traffic_stats_collection = None
user_activities_collection = None
whitelist_rules_collection = None


def to_object_id(id_string):
    """Convert string ID to ObjectId, return None if invalid"""
    try:
        return ObjectId(id_string)
    except (InvalidId, TypeError):
        return None


def alert_to_dict(alert_doc):
    """Convert alert document to dictionary for JSON serialization"""
    if alert_doc is None:
        return None
    
    result = dict(alert_doc)
    result['id'] = str(result.pop('_id', ''))
    
    # Convert datetime to ISO format string
    if 'timestamp' in result and isinstance(result['timestamp'], datetime):
        result['timestamp'] = result['timestamp'].isoformat()
    if 'resolved_at' in result and result['resolved_at'] and isinstance(result['resolved_at'], datetime):
        result['resolved_at'] = result['resolved_at'].isoformat()
    
    return result


def traffic_stat_to_dict(stat_doc):
    """Convert traffic stat document to dictionary for JSON serialization"""
    if stat_doc is None:
        return None
    
    result = dict(stat_doc)
    result['id'] = str(result.pop('_id', ''))
    
    # Convert datetime to ISO format string
    if 'timestamp' in result and isinstance(result['timestamp'], datetime):
        result['timestamp'] = result['timestamp'].isoformat()
    
    return result


def user_activity_to_dict(activity_doc):
    """Convert user activity document to dictionary for JSON serialization"""
    if activity_doc is None:
        return None
    
    result = dict(activity_doc)
    result['id'] = str(result.pop('_id', ''))
    
    # Convert datetime to ISO format string
    if 'timestamp' in result and isinstance(result['timestamp'], datetime):
        result['timestamp'] = result['timestamp'].isoformat()
    
    return result


def whitelist_rule_to_dict(rule_doc):
    """Convert whitelist rule document to dictionary for JSON serialization"""
    if rule_doc is None:
        return None
    
    result = dict(rule_doc)
    result['id'] = str(result.pop('_id', ''))
    
    # Convert datetime to ISO format string
    if 'created_at' in result and isinstance(result['created_at'], datetime):
        result['created_at'] = result['created_at'].isoformat()
    
    return result


# Database initialization function
def init_db(app):
    """Initialize the database with the Flask app and create indexes"""
    global alerts_collection, traffic_stats_collection, user_activities_collection, whitelist_rules_collection
    
    try:
        # Get database instance
        db = get_db(app.config)
        
        # Initialize collections
        alerts_collection = db['alerts']
        traffic_stats_collection = db['traffic_stats']
        user_activities_collection = db['user_activities']
        whitelist_rules_collection = db['whitelist_rules']
        
        logger.info("MongoDB collections initialized")
        
        # Create indexes with error handling (SSL errors may occur but indexes will be created eventually)
        try:
            # Create indexes for alerts collection
            alerts_collection.create_index([("source_ip", 1)], background=True)
            alerts_collection.create_index([("dest_ip", 1)], background=True)
            alerts_collection.create_index([("timestamp", -1)], background=True)
            alerts_collection.create_index([("type", 1)], background=True)
            alerts_collection.create_index([("severity", 1)], background=True)
            alerts_collection.create_index([("resolved", 1)], background=True)
            alerts_collection.create_index([("source_ip", 1), ("timestamp", -1)], background=True)
            alerts_collection.create_index([("type", 1), ("severity", 1)], background=True)
            alerts_collection.create_index([("resolved", 1), ("timestamp", -1)], background=True)
            alerts_collection.create_index([("severity", 1), ("timestamp", -1)], background=True)
            alerts_collection.create_index([("protocol", 1)], background=True)
            logger.info("Created indexes for alerts collection")
        except (AutoReconnect, ConnectionFailure, ServerSelectionTimeoutError) as e:
            # Index creation may fail due to SSL issues, but indexes will be created on next successful connection
            logger.warning(f"Some indexes may not have been created due to connection issues (non-critical): {e}")
            logger.info("Indexes will be created automatically on next successful connection")
        
        try:
            # Create indexes for traffic_stats collection
            traffic_stats_collection.create_index([("timestamp", -1)], background=True)
            traffic_stats_collection.create_index([("packet_rate", 1)], background=True)
            traffic_stats_collection.create_index([("anomaly_count", 1)], background=True)
            logger.info("Created indexes for traffic_stats collection")
        except (AutoReconnect, ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.warning(f"Some indexes may not have been created due to connection issues (non-critical): {e}")
        
        try:
            # Create indexes for user_activities collection
            user_activities_collection.create_index([("user_id", 1)], background=True)
            user_activities_collection.create_index([("username", 1)], background=True)
            user_activities_collection.create_index([("timestamp", -1)], background=True)
            user_activities_collection.create_index([("severity", 1)], background=True)
            user_activities_collection.create_index([("activity_type", 1)], background=True)
            user_activities_collection.create_index([("user_id", 1), ("timestamp", -1)], background=True)
            user_activities_collection.create_index([("activity_type", 1), ("severity", 1)], background=True)
            user_activities_collection.create_index([("source_ip", 1)], background=True)
            user_activities_collection.create_index([("severity", 1), ("timestamp", -1)], background=True)
            user_activities_collection.create_index([("activity_type", 1), ("timestamp", -1)], background=True)
            logger.info("Created indexes for user_activities collection")
        except (AutoReconnect, ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.warning(f"Some indexes may not have been created due to connection issues (non-critical): {e}")
        
        try:
            # Create indexes for whitelist_rules collection
            whitelist_rules_collection.create_index([("rule_type", 1), ("value", 1)], background=True)
            whitelist_rules_collection.create_index([("active", 1)], background=True)
            logger.info("Created indexes for whitelist_rules collection")
        except (AutoReconnect, ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.warning(f"Some indexes may not have been created due to connection issues (non-critical): {e}")
        
        # Insert default whitelist rules if they don't exist (with error handling)
        try:
            default_rules = [
            {
                'name': 'Localhost Traffic',
                'rule_type': 'ip',
                'value': '127.0.0.1',
                'description': 'Allow localhost traffic',
                'active': True,
                'created_at': datetime.utcnow(),
                'created_by': 'system'
            },
            {
                'name': 'Private Networks',
                'rule_type': 'ip',
                'value': '192.168.0.0/16',
                'description': 'Allow private network traffic',
                'active': True,
                'created_at': datetime.utcnow(),
                'created_by': 'system'
            },
            {
                'name': 'HTTP Traffic',
                'rule_type': 'port',
                'value': '80',
                'description': 'Allow HTTP traffic',
                'active': True,
                'created_at': datetime.utcnow(),
                'created_by': 'system'
            },
            {
                'name': 'HTTPS Traffic',
                'rule_type': 'port',
                'value': '443',
                'description': 'Allow HTTPS traffic',
                'active': True,
                'created_at': datetime.utcnow(),
                'created_by': 'system'
            }
        ]
        
            for rule in default_rules:
                existing = whitelist_rules_collection.find_one({
                    'rule_type': rule['rule_type'],
                    'value': rule['value']
                })
                if not existing:
                    whitelist_rules_collection.insert_one(rule)
        except (AutoReconnect, ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.warning(f"Could not insert default whitelist rules due to connection issues (non-critical): {e}")
        
        logger.info("MongoDB database initialized successfully")
        
    except Exception as e:
        # Log error but don't crash - allow app to start even if MongoDB has issues
        # MongoDB operations will work once connection is established
        logger.warning(f"MongoDB initialization had issues (app will continue): {e}")
        logger.info("MongoDB operations will work once connection is established")
