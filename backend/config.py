"""
Configuration settings for Flask IDS Backend
Supports both local development and AWS deployment
"""

import os

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    # Load environment variables from .env file (if it exists)
    try:
        load_dotenv()
    except Exception as e:
        print(f"Warning: Could not load .env file: {e}")
        print("Using default configuration values...")
except ImportError:
    # dotenv not installed - that's okay, we'll use environment variables directly
    pass

class Config:
    """Base configuration class"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # MongoDB configuration
    MONGODB_URI = os.environ.get('MONGODB_URI') or 'mongodb://localhost:27017/'
    MONGODB_DATABASE_NAME = os.environ.get('MONGODB_DATABASE_NAME', 'ids_db')
    
    # Detection thresholds
    PACKET_RATE_THRESHOLD = int(os.environ.get('PACKET_RATE_THRESHOLD', '1000'))
    CONNECTION_LIMIT = int(os.environ.get('CONNECTION_LIMIT', '100'))
    ANOMALY_SCORE_THRESHOLD = float(os.environ.get('ANOMALY_SCORE_THRESHOLD', '0.5'))
    
    # Packet capture settings
    CAPTURE_INTERFACE = os.environ.get('CAPTURE_INTERFACE', 'any')  # Use 'any' for automatic interface detection
    CAPTURE_TIMEOUT = int(os.environ.get('CAPTURE_TIMEOUT', '1'))
    
    # Alert settings
    ALERT_DEDUP_WINDOW = int(os.environ.get('ALERT_DEDUP_WINDOW', '300'))  # 5 minutes
    MAX_ALERTS_PER_HOUR = int(os.environ.get('MAX_ALERTS_PER_HOUR', '100'))
    
    # ML model settings
    MODEL_RETRAIN_INTERVAL = int(os.environ.get('MODEL_RETRAIN_INTERVAL', '3600'))  # 1 hour
    MIN_SAMPLES_FOR_TRAINING = int(os.environ.get('MIN_SAMPLES_FOR_TRAINING', '100'))
    
    # PCAP analysis settings (ML classification runs in batch; up to 100k packets per request)
    PCAP_MAX_PACKETS = int(os.environ.get('PCAP_MAX_PACKETS', '100000'))  # Default packet limit for PCAP analysis
    PCAP_ANALYSIS_TIMEOUT = int(os.environ.get('PCAP_ANALYSIS_TIMEOUT', '300'))  # 5 minutes timeout for analysis
    
    # Supervised ML classification settings (default: pre-trained SecIDS-CNN only; no internal dataset)
    CLASSIFICATION_ENABLED = os.environ.get('CLASSIFICATION_ENABLED', 'True').lower() == 'true'
    CLASSIFICATION_MODEL_TYPE = os.environ.get('CLASSIFICATION_MODEL_TYPE', 'secids_cnn')  # secids_cnn (default), random_forest, etc.
    # SecIDS-CNN pre-trained model (optional); used when CLASSIFICATION_MODEL_TYPE == 'secids_cnn'
    SECIDS_MODEL_PATH = os.environ.get('SECIDS_MODEL_PATH') or None  # None = resolve to project_root/SecIDS-CNN/SecIDS-CNN.h5
    MIN_TRAINING_SAMPLES_CLASSIFICATION = int(os.environ.get('MIN_TRAINING_SAMPLES_CLASSIFICATION', '1000'))
    TRAIN_TEST_SPLIT_RATIO = float(os.environ.get('TRAIN_TEST_SPLIT_RATIO', '0.7'))
    HYPERPARAMETER_TUNING_ENABLED = os.environ.get('HYPERPARAMETER_TUNING_ENABLED', 'False').lower() == 'true'
    HYPERPARAMETER_TUNING_N_ITER = int(os.environ.get('HYPERPARAMETER_TUNING_N_ITER', '50'))  # Number of iterations for RandomizedSearchCV (increased default)
    HYPERPARAMETER_TUNING_CV = int(os.environ.get('HYPERPARAMETER_TUNING_CV', '5'))  # Cross-validation folds (increased default)
    MAX_TRAINING_SAMPLES = int(os.environ.get('MAX_TRAINING_SAMPLES')) if os.environ.get('MAX_TRAINING_SAMPLES') else None  # None = use all samples
    BATCH_LOADING_ENABLED = os.environ.get('BATCH_LOADING_ENABLED', 'False').lower() == 'true'  # Enable if memory constrained
    CLASSIFICATION_CONFIDENCE_THRESHOLD = float(os.environ.get('CLASSIFICATION_CONFIDENCE_THRESHOLD', '0.7'))
    USE_SMOTE = os.environ.get('USE_SMOTE', 'True').lower() == 'true'  # Use SMOTE for class imbalance
    USE_ROBUST_SCALER = os.environ.get('USE_ROBUST_SCALER', 'True').lower() == 'true'  # Use RobustScaler instead of StandardScaler
    MAX_FEATURES = int(os.environ.get('MAX_FEATURES', '60'))  # Maximum number of features after selection
    USE_ENSEMBLE = os.environ.get('USE_ENSEMBLE', 'False').lower() == 'true'  # Use ensemble classifier
    
    # Whitelist IPs (comma-separated)
    WHITELIST_IPS = os.environ.get('WHITELIST_IPS', '127.0.0.1,10.0.0.0/8,192.168.0.0/16').split(',')
    
    # Whitelist ports (comma-separated) - packets on these ports will skip deep analysis but still be tracked
    # Default to empty list so all traffic is tracked and displayed in dashboard
    # Example: '80,443,53' to skip deep analysis for HTTP, HTTPS, DNS (but still track connections)
    WHITELIST_PORTS = os.environ.get('WHITELIST_PORTS', '').split(',') if os.environ.get('WHITELIST_PORTS') else []
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # AWS specific settings
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
    
    # Real-time stats flush interval (seconds)
    TRAFFIC_STATS_FLUSH_INTERVAL = int(os.environ.get('TRAFFIC_STATS_FLUSH_INTERVAL', '30'))
    
    # WebSocket broadcast interval (seconds)
    WEBSOCKET_BROADCAST_INTERVAL = int(os.environ.get('WEBSOCKET_BROADCAST_INTERVAL', '5'))
    
    # Minimum packet count for WebSocket broadcast
    WEBSOCKET_BROADCAST_PACKET_THRESHOLD = int(os.environ.get('WEBSOCKET_BROADCAST_PACKET_THRESHOLD', '5'))
    
    # Packet sniffer auto-retry settings
    SNIFFER_RETRY_ENABLED = os.environ.get('SNIFFER_RETRY_ENABLED', 'true').lower() == 'true'
    SNIFFER_RETRY_INTERVAL = int(os.environ.get('SNIFFER_RETRY_INTERVAL', '30'))
    SNIFFER_MAX_RETRIES = int(os.environ.get('SNIFFER_MAX_RETRIES', '10'))
    
    # Auto-start Scapy on backend startup (MUST be true)
    SCAPY_AUTO_START = os.environ.get('SCAPY_AUTO_START', 'true').lower() == 'true'
    SCAPY_AUTO_START_DELAY = int(os.environ.get('SCAPY_AUTO_START_DELAY', '0'))
    SCAPY_STATUS_CHECK_INTERVAL = int(os.environ.get('SCAPY_STATUS_CHECK_INTERVAL', '30'))
    
    # Capture health check interval (seconds) - how long to wait before warning about no packets
    CAPTURE_HEALTH_CHECK_INTERVAL = int(os.environ.get('CAPTURE_HEALTH_CHECK_INTERVAL', '30'))
    
    @staticmethod
    def init_app(app):
        """Initialize app-specific configurations"""
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    MONGODB_URI = os.environ.get('MONGODB_URI') or 'mongodb://localhost:27017/'
    MONGODB_DATABASE_NAME = os.environ.get('MONGODB_DATABASE_NAME', 'ids_db')

class ProductionConfig(Config):
    """Production configuration for AWS deployment"""
    DEBUG = False
    
    @staticmethod
    def init_app(app):
        """Initialize app-specific configurations"""
        # Ensure we have required environment variables for production
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("SECRET_KEY environment variable must be set in production")
        
        if not os.environ.get('MONGODB_URI'):
            raise ValueError("MONGODB_URI environment variable must be set in production")

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    MONGODB_URI = os.environ.get('MONGODB_URI') or 'mongodb://localhost:27017/'
    MONGODB_DATABASE_NAME = 'ids_test_db'
    WTF_CSRF_ENABLED = False
    # Do not start packet sniffer during tests
    SCAPY_AUTO_START = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
