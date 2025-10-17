"""
Configuration settings for Flask IDS Backend
Supports both local development and AWS deployment
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # Database configuration
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///ids.db'
    
    # Detection thresholds
    PACKET_RATE_THRESHOLD = int(os.environ.get('PACKET_RATE_THRESHOLD', '1000'))
    CONNECTION_LIMIT = int(os.environ.get('CONNECTION_LIMIT', '100'))
    ANOMALY_SCORE_THRESHOLD = float(os.environ.get('ANOMALY_SCORE_THRESHOLD', '0.5'))
    
    # Packet capture settings
    CAPTURE_INTERFACE = os.environ.get('CAPTURE_INTERFACE', 'any')
    CAPTURE_TIMEOUT = int(os.environ.get('CAPTURE_TIMEOUT', '1'))
    
    # Alert settings
    ALERT_DEDUP_WINDOW = int(os.environ.get('ALERT_DEDUP_WINDOW', '300'))  # 5 minutes
    MAX_ALERTS_PER_HOUR = int(os.environ.get('MAX_ALERTS_PER_HOUR', '100'))
    
    # ML model settings
    MODEL_RETRAIN_INTERVAL = int(os.environ.get('MODEL_RETRAIN_INTERVAL', '3600'))  # 1 hour
    MIN_SAMPLES_FOR_TRAINING = int(os.environ.get('MIN_SAMPLES_FOR_TRAINING', '100'))
    
    # Whitelist IPs (comma-separated)
    WHITELIST_IPS = os.environ.get('WHITELIST_IPS', '127.0.0.1,10.0.0.0/8,192.168.0.0/16').split(',')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # AWS specific settings
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
    
    @staticmethod
    def init_app(app):
        """Initialize app-specific configurations"""
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    DATABASE_URL = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///ids_dev.db'

class ProductionConfig(Config):
    """Production configuration for AWS deployment"""
    DEBUG = False
    
    # Ensure we have required environment variables for production
    if not os.environ.get('SECRET_KEY'):
        raise ValueError("SECRET_KEY environment variable must be set in production")
    
    if not os.environ.get('DATABASE_URL'):
        raise ValueError("DATABASE_URL environment variable must be set in production")

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
