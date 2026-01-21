"""
Script to train the Isolation Forest anomaly detection model
Creates synthetic packet data to train the model if no real packets are available
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add parent directory to path to import services
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import DevelopmentConfig
    from services.analyzer import AnomalyDetector
except ImportError as e:
    print(f"Error: Missing required dependencies. Please install them:")
    print(f"  pip install -r requirements.txt")
    print(f"")
    print(f"Import error: {e}")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_synthetic_packet_data(num_samples=200):
    """
    Generate synthetic packet data for training the anomaly detection model
    
    Args:
        num_samples: Number of synthetic packets to generate
        
    Returns:
        List of packet data dictionaries
    """
    packets = []
    protocols = ['TCP', 'UDP', 'ICMP']
    
    for i in range(num_samples):
        # Generate normal traffic (90% of samples)
        is_normal = random.random() < 0.9
        
        if is_normal:
            # Normal traffic patterns
            packet = {
                'payload_size': random.randint(64, 1500),
                'raw_size': random.randint(74, 1514),
                'protocol': random.choice(protocols),
                'src_port': random.randint(1024, 65535),
                'dst_port': random.choice([80, 443, 22, 53, 8080]),
                'flags': random.randint(0, 255),
                'timestamp': datetime.now() - timedelta(seconds=random.randint(0, 3600)),
                'payload_preview': ''.join([format(random.randint(0, 255), '02x') for _ in range(32)])
            }
        else:
            # Anomalous traffic patterns (10% of samples)
            packet = {
                'payload_size': random.randint(5000, 10000),  # Very large packets
                'raw_size': random.randint(5014, 10014),
                'protocol': random.choice(protocols),
                'src_port': random.randint(1, 1023),  # Privileged ports (unusual source)
                'dst_port': random.randint(20000, 65535),  # Unusual destination ports
                'flags': random.randint(200, 255),  # Unusual flag combinations
                'timestamp': datetime.now() - timedelta(seconds=random.randint(0, 3600)),
                'payload_preview': ''.join([format(random.randint(0, 255), '02x') for _ in range(128)])  # Large payload
            }
        
        packets.append(packet)
    
    return packets


def train_anomaly_model():
    """Train the anomaly detection model with synthetic data"""
    try:
        logger.info("Initializing anomaly detector...")
        config = DevelopmentConfig()
        detector = AnomalyDetector(config)
        
        # Check if model already exists and is trained
        if detector.is_trained:
            logger.info("Anomaly detection model is already trained!")
            logger.info(f"Model path: {detector.model_path}")
            # Auto-retrain to ensure model is up-to-date (non-interactive)
            logger.info("Retraining model with fresh data...")
        
        logger.info(f"Generating {config.MIN_SAMPLES_FOR_TRAINING + 50} synthetic packet samples for training...")
        synthetic_packets = generate_synthetic_packet_data(config.MIN_SAMPLES_FOR_TRAINING + 50)
        
        logger.info("Feeding packets to anomaly detector for training...")
        # Clear existing feature data if retraining
        detector.feature_data.clear()
        
        for i, packet in enumerate(synthetic_packets):
            # Extract features and add to training data
            features = detector._extract_features(packet)
            detector.feature_data.append(features)
            
            if (i + 1) % 50 == 0:
                logger.info(f"Processed {i + 1}/{len(synthetic_packets)} packets...")
        
        logger.info(f"Collected {len(detector.feature_data)} feature samples")
        logger.info(f"Minimum required: {config.MIN_SAMPLES_FOR_TRAINING}")
        
        if len(detector.feature_data) < config.MIN_SAMPLES_FOR_TRAINING:
            logger.error(f"Not enough samples! Got {len(detector.feature_data)}, need {config.MIN_SAMPLES_FOR_TRAINING}")
            return False
        
        logger.info("Training anomaly detection model...")
        success = detector.train_model()
        
        if success:
            logger.info("✓ Anomaly detection model trained successfully!")
            logger.info(f"Model saved to: {os.path.abspath(detector.model_path)}")
            logger.info(f"Model is now ready for anomaly detection")
            return True
        else:
            logger.error("Failed to train model")
            return False
            
    except Exception as e:
        logger.error(f"Error training anomaly model: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Anomaly Detection Model Training Script")
    logger.info("=" * 60)
    
    success = train_anomaly_model()
    
    if success:
        logger.info("\n✓ Training completed successfully!")
        sys.exit(0)
    else:
        logger.error("\n✗ Training failed!")
        sys.exit(1)
