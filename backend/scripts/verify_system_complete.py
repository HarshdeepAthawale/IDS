"""
Comprehensive system verification script
Tests all components of the IDS system to ensure everything works correctly
"""

import sys
import os
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import DevelopmentConfig
    from services.analyzer import PacketAnalyzer, AnomalyDetector
    from services.classifier import get_classification_detector
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


def test_classification_model():
    """Test classification model loading and prediction"""
    logger.info("=" * 60)
    logger.info("Testing Classification Model")
    logger.info("=" * 60)
    
    try:
        config = DevelopmentConfig()
        classifier = get_classification_detector(config)
        
        if not classifier.is_trained:
            logger.warning("⚠ Classification model is not trained!")
            return False
        
        logger.info(f"✓ Model loaded: {classifier.model_type}")
        n_feat = getattr(classifier, 'n_features_in_', None) or getattr(getattr(classifier, 'model', None), 'n_features_in_', None)
        if n_feat is not None:
            logger.info(f"✓ Model expects {n_feat} features")
        
        # Test classification with sample features
        test_features = {
            'packet_size': 1024.0,
            'protocol_type': 1.0,
            'connection_duration': 10.5,
            'failed_login_attempts': 0.0,
            'data_transfer_rate': 100.0,
            'access_frequency': 5.0
        }
        
        result = classifier.classify(test_features)
        logger.info(f"✓ Classification test result: {result['label']} (confidence: {result['confidence']:.2f})")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Classification model test failed: {e}")
        return False


def test_anomaly_detector():
    """Test anomaly detection model"""
    logger.info("=" * 60)
    logger.info("Testing Anomaly Detection Model")
    logger.info("=" * 60)
    
    try:
        config = DevelopmentConfig()
        detector = AnomalyDetector(config)
        
        if not detector.is_trained:
            logger.warning("⚠ Anomaly detection model is not trained!")
            logger.info("  Run: python scripts/train_anomaly_model.py")
            return False
        
        logger.info("✓ Anomaly detection model loaded")
        
        # Test with sample packet
        from datetime import datetime, timezone
        test_packet = {
            'payload_size': 64,
            'raw_size': 74,
            'protocol': 'TCP',
            'src_port': 12345,
            'dst_port': 80,
            'flags': 2,  # Use integer instead of hex
            'timestamp': datetime.now(timezone.utc),
            'payload_preview': '474554202f'
        }
        
        result = detector.detect_anomaly(test_packet)
        if result:
            logger.info(f"✓ Anomaly detection works (detected anomaly with confidence: {result.get('confidence', 0):.2f})")
        else:
            logger.info("✓ Anomaly detection works (no anomaly detected for test packet)")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Anomaly detector test failed: {e}")
        return False


def test_packet_analyzer():
    """Test packet analyzer with all detection methods"""
    logger.info("=" * 60)
    logger.info("Testing Packet Analyzer")
    logger.info("=" * 60)
    
    try:
        config = DevelopmentConfig()
        analyzer = PacketAnalyzer(config)
        
        logger.info("✓ Packet analyzer initialized")
        
        # Test packet with SQL injection attempt
        from datetime import datetime, timezone
        test_packet = {
            'src_ip': '192.168.1.100',
            'dst_ip': '10.0.0.1',
            'protocol': 'TCP',
            'src_port': 12345,
            'dst_port': 80,
            'payload_size': 512,
            'raw_size': 522,
            'flags': 2,  # Use integer flag value
            'uri': "/api/users?id=1' OR 1=1--",
            'http_method': 'GET',
            'user_agent': 'Mozilla/5.0',
            'payload_preview': '474554202f6170692f7573657273',
            'timestamp': datetime.now(timezone.utc)
        }
        
        results = analyzer.analyze_packet(test_packet)
        
        logger.info(f"✓ Packet analysis completed: {len(results)} detection(s)")
        for result in results:
            logger.info(f"  - {result['type']}: {result['description']} (severity: {result['severity']})")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Packet analyzer test failed: {e}")
        return False


def test_model_files():
    """Check if required model files exist"""
    logger.info("=" * 60)
    logger.info("Checking Model Files")
    logger.info("=" * 60)
    
    classification_model = Path(__file__).parent.parent / 'classification_model.pkl'
    anomaly_model = Path(__file__).parent.parent / 'anomaly_model.pkl'
    
    results = []
    
    if classification_model.exists():
        size_mb = classification_model.stat().st_size / (1024 * 1024)
        logger.info(f"✓ Classification model exists: {size_mb:.2f} MB")
        results.append(True)
    else:
        logger.warning("⚠ Classification model not found!")
        results.append(False)
    
    if anomaly_model.exists():
        size_mb = anomaly_model.stat().st_size / (1024 * 1024)
        logger.info(f"✓ Anomaly model exists: {size_mb:.2f} MB")
        results.append(True)
    else:
        logger.warning("⚠ Anomaly model not found (run train_anomaly_model.py)")
        results.append(False)
    
    return all(results)


def main():
    """Run all verification tests"""
    logger.info("=" * 60)
    logger.info("IDS System Complete Verification")
    logger.info("=" * 60)
    logger.info("")
    
    results = {
        'Model Files': test_model_files(),
        'Classification Model': test_classification_model(),
        'Anomaly Detector': test_anomaly_detector(),
        'Packet Analyzer': test_packet_analyzer(),
    }
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("Verification Summary")
    logger.info("=" * 60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    logger.info("")
    if all_passed:
        logger.info("✓ All tests passed! System is ready.")
        return 0
    else:
        logger.warning("⚠ Some tests failed. Please review the output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
