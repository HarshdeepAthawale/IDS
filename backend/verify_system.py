#!/usr/bin/env python3
"""
System verification script for IDS Backend
Checks if all services initialize correctly and model loads properly
"""

import sys
import os
import traceback

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_imports():
    """Check if all required modules can be imported"""
    print("=" * 60)
    print("Checking Imports...")
    print("=" * 60)
    
    try:
        from config import config, DevelopmentConfig
        print("✓ Config module imported")
    except Exception as e:
        print(f"✗ Failed to import config: {e}")
        return False
    
    try:
        from models.db_models import init_db
        print("✓ Database models imported")
    except Exception as e:
        print(f"✗ Failed to import db_models: {e}")
        return False
    
    try:
        from services.packet_sniffer import PacketSniffer
        print("✓ Packet sniffer imported")
    except Exception as e:
        print(f"✗ Failed to import packet_sniffer: {e}")
        return False
    
    try:
        from services.analyzer import PacketAnalyzer
        print("✓ Packet analyzer imported")
    except Exception as e:
        print(f"✗ Failed to import analyzer: {e}")
        return False
    
    try:
        from services.logger import DatabaseLogger
        print("✓ Database logger imported")
    except Exception as e:
        print(f"✗ Failed to import logger: {e}")
        return False
    
    try:
        from services.classifier import get_classification_detector
        print("✓ Classification detector imported")
    except Exception as e:
        print(f"✗ Failed to import classifier: {e}")
        return False
    
    try:
        from routes.alerts import alerts_bp
        from routes.stats import stats_bp
        from routes.analyze import analyze_bp
        from routes.training import training_bp
        print("✓ All route blueprints imported")
    except Exception as e:
        print(f"✗ Failed to import routes: {e}")
        return False
    
    return True

def check_app_creation():
    """Check if Flask app can be created"""
    print("\n" + "=" * 60)
    print("Checking App Creation...")
    print("=" * 60)
    
    try:
        from app import create_app
        app = create_app('development')
        print("✓ Flask app created successfully")
        
        # Check if all blueprints are registered
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        expected_blueprints = ['alerts', 'stats', 'analyze', 'training', 'pcap']
        
        for bp_name in expected_blueprints:
            if bp_name in blueprint_names:
                print(f"✓ Blueprint '{bp_name}' registered")
            else:
                print(f"✗ Blueprint '{bp_name}' not registered")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Failed to create app: {e}")
        traceback.print_exc()
        return False

def check_model_loading():
    """Check if model can be loaded"""
    print("\n" + "=" * 60)
    print("Checking Model Loading...")
    print("=" * 60)
    
    try:
        from config import DevelopmentConfig
        from services.classifier import get_classification_detector
        
        config = DevelopmentConfig()
        classifier = get_classification_detector(config)
        
        if getattr(classifier, 'model_type', None) == 'secids_cnn':
            if classifier.is_trained:
                print("✓ SecIDS-CNN pre-trained model loaded successfully")
                print(f"  Model path: {getattr(classifier, 'model_path', 'N/A')}")
                return True
            print("⚠ SecIDS-CNN model not loaded.")
            print("  1. Install TensorFlow: pip install tensorflow")
            print("  2. Place SecIDS-CNN.h5 at SecIDS-CNN/SecIDS-CNN.h5 (repo root) or set SECIDS_MODEL_PATH.")
            return True
        if classifier.model is not None:
            print("✓ Model loaded successfully")
            print(f"  Model type: {classifier.model_type}")
            print(f"  Is trained: {classifier.is_trained}")
            if classifier.feature_names:
                print(f"  Features: {len(classifier.feature_names)}")
            return True
        else:
            print("⚠ Model not loaded (this is OK if model hasn't been trained yet)")
            print("  Model will be created on first training")
            return True
    except Exception as e:
        print(f"✗ Failed to load model: {e}")
        traceback.print_exc()
        return False

def check_services():
    """Check if services can be initialized"""
    print("\n" + "=" * 60)
    print("Checking Services...")
    print("=" * 60)
    
    try:
        from config import DevelopmentConfig
        from services.analyzer import PacketAnalyzer
        from services.logger import DatabaseLogger
        from services.packet_sniffer import PacketSniffer
        
        config = DevelopmentConfig()
        
        analyzer = PacketAnalyzer(config)
        print("✓ Packet analyzer initialized")
        
        logger = DatabaseLogger(config)
        print("✓ Database logger initialized")
        
        sniffer = PacketSniffer(config, packet_callback=None)
        print("✓ Packet sniffer initialized")
        
        return True
    except Exception as e:
        print(f"✗ Failed to initialize services: {e}")
        traceback.print_exc()
        return False

def check_training_services():
    """Check if training services can be initialized"""
    print("\n" + "=" * 60)
    print("Checking Training Services...")
    print("=" * 60)
    
    try:
        from config import DevelopmentConfig
        config = DevelopmentConfig()
        
        if not getattr(config, 'CLASSIFICATION_ENABLED', False):
            print("⚠ Classification is disabled in config")
            print("  Set CLASSIFICATION_ENABLED=true in .env to enable")
            return True
        
        from services.data_collector import DataCollector
        from services.feature_extractor import FeatureExtractor
        
        collector = DataCollector(config)
        print("✓ Data collector initialized")
        
        extractor = FeatureExtractor(config)
        print("✓ Feature extractor initialized")
        
        return True
    except Exception as e:
        print(f"✗ Failed to initialize training services: {e}")
        traceback.print_exc()
        return False

def check_model_file():
    """Check if model file exists"""
    print("\n" + "=" * 60)
    print("Checking Model File...")
    print("=" * 60)
    
    model_path = 'classification_model.pkl'
    if os.path.exists(model_path):
        size = os.path.getsize(model_path)
        print(f"✓ Model file exists: {model_path}")
        print(f"  Size: {size / (1024*1024):.2f} MB")
        return True
    else:
        print(f"⚠ Model file not found: {model_path}")
        print("  This is OK if model hasn't been trained yet")
        return True

def main():
    """Run all verification checks"""
    print("\n" + "=" * 60)
    print("IDS Backend System Verification")
    print("=" * 60 + "\n")
    
    checks = [
        ("Imports", check_imports),
        ("App Creation", check_app_creation),
        ("Services", check_services),
        ("Training Services", check_training_services),
        ("Model Loading", check_model_loading),
        ("Model File", check_model_file),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} check failed with exception: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All checks passed! System is ready.")
        return 0
    else:
        print("✗ Some checks failed. Please review the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
