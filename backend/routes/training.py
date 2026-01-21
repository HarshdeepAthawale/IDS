"""
Training data management API routes
Provides endpoints for labeling, retrieving, and managing training data
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from services.data_collector import DataCollector
from services.feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)

# Create blueprint
training_bp = Blueprint('training', __name__)

# Initialize services (will be injected from main app)
data_collector = None
feature_extractor = None
app_config = None

def init_services(collector_instance, extractor_instance, config=None):
    """Initialize data collector and feature extractor services"""
    global data_collector, feature_extractor, app_config
    data_collector = collector_instance
    feature_extractor = extractor_instance
    app_config = config


@training_bp.route('/api/training/label', methods=['POST'])
def label_sample():
    """
    Manually label a training sample
    
    Request Body:
    {
        "sample_id": "507f1f77bcf86cd799439011",
        "label": "malicious",
        "confidence": 0.95,
        "labeled_by": "user"
    }
    
    Returns:
    JSON response with success status
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        sample_id = data.get('sample_id')
        label = data.get('label')
        
        if not sample_id:
            return jsonify({'error': 'sample_id is required'}), 400
        
        if not label:
            return jsonify({'error': 'label is required'}), 400
        
        if label not in ['benign', 'malicious']:
            return jsonify({'error': 'label must be "benign" or "malicious"'}), 400
        
        confidence = data.get('confidence', 1.0)
        labeled_by = data.get('labeled_by', 'user')
        
        success = data_collector.label_sample(sample_id, label, labeled_by, confidence)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Sample {sample_id} labeled as {label}',
                'sample_id': sample_id,
                'label': label
            })
        else:
            return jsonify({'error': 'Failed to label sample'}), 400
        
    except Exception as e:
        logger.error(f"Error labeling sample: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@training_bp.route('/api/training/data', methods=['GET'])
def get_training_data():
    """
    Retrieve labeled training data
    
    Query Parameters:
    - label: Filter by label ("benign" or "malicious")
    - limit: Maximum number of samples (default 1000)
    - start_date: Start date filter (ISO format)
    - end_date: End date filter (ISO format)
    
    Returns:
    JSON response with training samples
    """
    try:
        label = request.args.get('label')
        limit = int(request.args.get('limit', 1000))
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Parse dates if provided
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid start_date format'}), 400
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid end_date format'}), 400
        
        samples = data_collector.get_labeled_samples(
            label=label,
            limit=limit,
            start_date=start_dt,
            end_date=end_dt
        )
        
        # Convert ObjectId to string for JSON serialization
        for sample in samples:
            sample['id'] = str(sample.pop('_id'))
            if 'timestamp' in sample and isinstance(sample['timestamp'], datetime):
                sample['timestamp'] = sample['timestamp'].isoformat()
            if 'labeled_at' in sample and isinstance(sample['labeled_at'], datetime):
                sample['labeled_at'] = sample['labeled_at'].isoformat()
        
        return jsonify({
            'samples': samples,
            'count': len(samples),
            'label': label,
            'limit': limit
        })
        
    except Exception as e:
        logger.error(f"Error getting training data: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@training_bp.route('/api/training/data/unlabeled', methods=['GET'])
def get_unlabeled_data():
    """
    Retrieve unlabeled training samples
    
    Query Parameters:
    - limit: Maximum number of samples (default 100)
    
    Returns:
    JSON response with unlabeled samples
    """
    try:
        limit = int(request.args.get('limit', 100))
        
        samples = data_collector.get_unlabeled_samples(limit=limit)
        
        # Convert ObjectId to string
        for sample in samples:
            sample['id'] = str(sample.pop('_id'))
            if 'timestamp' in sample and isinstance(sample['timestamp'], datetime):
                sample['timestamp'] = sample['timestamp'].isoformat()
        
        return jsonify({
            'samples': samples,
            'count': len(samples),
            'limit': limit
        })
        
    except Exception as e:
        logger.error(f"Error getting unlabeled data: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@training_bp.route('/api/training/import', methods=['POST'])
def import_dataset():
    """
    Import external labeled dataset
    
    Request Body:
    {
        "samples": [
            {
                "features": {
                    "packet_size": 1024,
                    "protocol_type": 1,
                    "connection_duration": 5.5,
                    "failed_login_attempts": 0,
                    "data_transfer_rate": 204.8,
                    "access_frequency": 2.5
                },
                "label": "benign",
                "source_ip": "192.168.1.100",
                "dest_ip": "10.0.0.1",
                "protocol": "TCP",
                "dst_port": 80,
                "confidence": 1.0
            }
        ],
        "labeled_by": "import"
    }
    
    Returns:
    JSON response with import results
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        samples = data.get('samples', [])
        if not samples or not isinstance(samples, list):
            return jsonify({'error': 'samples must be a non-empty array'}), 400
        
        labeled_by = data.get('labeled_by', 'import')
        
        imported_count = data_collector.import_dataset(samples, labeled_by)
        
        return jsonify({
            'success': True,
            'imported_count': imported_count,
            'total_samples': len(samples),
            'labeled_by': labeled_by
        })
        
    except Exception as e:
        logger.error(f"Error importing dataset: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@training_bp.route('/api/training/data/<sample_id>', methods=['DELETE'])
def delete_sample(sample_id):
    """
    Delete a training sample
    
    Args:
        sample_id: Sample ID
    
    Returns:
        JSON response with success status
    """
    try:
        success = data_collector.delete_sample(sample_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Sample {sample_id} deleted',
                'sample_id': sample_id
            })
        else:
            return jsonify({'error': 'Sample not found or deletion failed'}), 404
        
    except Exception as e:
        logger.error(f"Error deleting sample: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@training_bp.route('/api/training/statistics', methods=['GET'])
def get_statistics():
    """
    Get training data statistics
    
    Returns:
    JSON response with statistics
    """
    try:
        stats = data_collector.get_statistics()
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@training_bp.route('/api/training/train', methods=['POST'])
def train_model():
    """
    Trigger model training
    
    Request Body (optional):
    {
        "hyperparameter_tuning": false
    }
    
    Returns:
    JSON response with training results
    """
    try:
        from services.classifier import ClassificationDetector
        from services.preprocessor import DataPreprocessor
        from services.model_trainer import ModelTrainer
        
        data = request.get_json() or {}
        hyperparameter_tuning = data.get('hyperparameter_tuning', False)
        
        # Get config
        from flask import current_app
        config = app_config or current_app.config
        
        classifier = ClassificationDetector(config)
        preprocessor = DataPreprocessor(config)
        trainer = ModelTrainer(config, classifier, preprocessor, data_collector)
        
        # Train model
        training_result = trainer.train_model(hyperparameter_tuning=hyperparameter_tuning)
        
        return jsonify({
            'success': True,
            'training_result': training_result
        })
        
    except Exception as e:
        logger.error(f"Error training model: {e}")
        return jsonify({'error': str(e)}), 500


@training_bp.route('/api/training/evaluate', methods=['GET'])
def evaluate_model():
    """
    Evaluate the current model
    
    Returns:
    JSON response with evaluation metrics
    """
    try:
        from services.classifier import ClassificationDetector
        from services.preprocessor import DataPreprocessor
        from services.model_evaluator import ModelEvaluator
        
        # Get config
        from flask import current_app
        config = app_config or current_app.config
        
        classifier = ClassificationDetector(config)
        preprocessor = DataPreprocessor(config)
        
        # Load test data
        from services.model_trainer import ModelTrainer
        trainer = ModelTrainer(config, classifier, preprocessor, data_collector)
        df, _ = trainer.load_training_data()
        
        # Clean and prepare
        df_clean = preprocessor.clean_data(df)
        df_eng = preprocessor.engineer_features(df_clean)
        
        # Split data
        train_df, val_df, test_df = preprocessor.split_data(df_eng, test_size=0.15, val_size=0.15)
        
        # Prepare test features and labels
        X_test = preprocessor.prepare_features(test_df)
        y_test = preprocessor.prepare_labels(test_df)
        
        # Evaluate
        evaluator = ModelEvaluator(classifier)
        metrics = evaluator.generate_report(X_test, y_test)
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error evaluating model: {e}")
        return jsonify({'error': str(e)}), 500


@training_bp.route('/api/training/metrics', methods=['GET'])
def get_metrics():
    """
    Get latest model metrics
    
    Returns:
    JSON response with metrics
    """
    try:
        from services.classifier import ClassificationDetector
        
        config = request.environ.get('app_config')
        if not config:
            from flask import current_app
            config = current_app.config
        
        classifier = ClassificationDetector(config)
        model_info = classifier.get_model_info()
        
        return jsonify({
            'model_info': model_info,
            'feature_importance': classifier.get_feature_importance()
        })
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({'error': str(e)}), 500


@training_bp.route('/api/training/model-info', methods=['GET'])
def get_ml_model_info():
    """
    Get ML model information in format expected by frontend
    
    Returns:
    JSON response with model information
    """
    try:
        from services.classifier import ClassificationDetector
        
        config = request.environ.get('app_config')
        if not config:
            from flask import current_app
            config = current_app.config
        
        classifier = ClassificationDetector(config)
        model_info = classifier.get_model_info()
        
        # Format response for frontend
        metadata = model_info.get('metadata', {})
        feature_names = classifier.feature_names or []
        
        response = {
            'model_name': model_info.get('model_type', 'random_forest'),
            'version': '1.0.0',
            'accuracy': metadata.get('test_accuracy', metadata.get('validation_accuracy', 0.0)),
            'last_trained': metadata.get('timestamp', ''),
            'features': feature_names[:20] if len(feature_names) > 20 else feature_names,  # Limit to 20 for display
            'is_trained': model_info.get('is_trained', False),
            'model_type': model_info.get('model_type', 'random_forest')
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting ML model info: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@training_bp.route('/api/training/confusion-matrix', methods=['GET'])
def get_confusion_matrix():
    """
    Get confusion matrix for current model
    
    Returns:
    JSON response with confusion matrix
    """
    try:
        from services.classifier import ClassificationDetector
        from services.preprocessor import DataPreprocessor
        from services.model_evaluator import ModelEvaluator
        
        config = request.environ.get('app_config')
        if not config:
            from flask import current_app
            config = current_app.config
        
        classifier = ClassificationDetector(config)
        preprocessor = DataPreprocessor(config)
        
        # Load test data
        from services.model_trainer import ModelTrainer
        trainer = ModelTrainer(config, classifier, preprocessor, data_collector)
        df, _ = trainer.load_training_data()
        
        df_clean = preprocessor.clean_data(df)
        df_eng = preprocessor.engineer_features(df_clean)
        train_df, val_df, test_df = preprocessor.split_data(df_eng, test_size=0.15, val_size=0.15)
        
        X_test = preprocessor.prepare_features(test_df)
        y_test = preprocessor.prepare_labels(test_df)
        
        evaluator = ModelEvaluator(classifier)
        cm = evaluator.get_confusion_matrix(X_test, y_test)
        
        return jsonify(cm)
        
    except Exception as e:
        logger.error(f"Error getting confusion matrix: {e}")
        return jsonify({'error': str(e)}), 500


@training_bp.route('/api/training/history', methods=['GET'])
def get_training_history():
    """
    Get training history
    
    Returns:
    JSON response with training history
    """
    try:
        from services.classifier import ClassificationDetector
        from services.preprocessor import DataPreprocessor
        from services.model_trainer import ModelTrainer
        
        config = request.environ.get('app_config')
        if not config:
            from flask import current_app
            config = current_app.config
        
        classifier = ClassificationDetector(config)
        preprocessor = DataPreprocessor(config)
        trainer = ModelTrainer(config, classifier, preprocessor, data_collector)
        
        history = trainer.get_training_history()
        
        return jsonify({
            'history': history,
            'count': len(history)
        })
        
    except Exception as e:
        logger.error(f"Error getting training history: {e}")
        return jsonify({'error': str(e)}), 500