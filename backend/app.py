"""
Main Flask application for IDS Backend
Integrates all services and provides REST API endpoints
"""

import logging
import threading
import signal
import sys
import json
import os
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from config import config, DevelopmentConfig
from models.db_models import init_db
from services.packet_sniffer import PacketSniffer
from services.analyzer import PacketAnalyzer
from services.logger import DatabaseLogger
from routes.alerts import alerts_bp, init_logger as init_alerts_logger
from routes.stats import stats_bp, init_logger as init_stats_logger
from routes.analyze import analyze_bp, init_services as init_analyze_services
from routes.insider import insider_bp, init_logger as init_insider_logger

# Configure logging
logging.basicConfig(
    level=getattr(logging, DevelopmentConfig.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ids_backend.log')
    ]
)

logger = logging.getLogger(__name__)

def create_app(config_name='default'):
    """
    Create and configure Flask application
    
    Args:
        config_name: Configuration name (development, production, testing)
        
    Returns:
        Configured Flask application
    """
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize configuration
    config[config_name].init_app(app)
    
    # Enable CORS for Next.js frontend
    CORS(app, origins=['http://localhost:3000', 'http://127.0.0.1:3000'])
    
    # Initialize SocketIO for real-time communication
    socketio = SocketIO(app, cors_allowed_origins=['http://localhost:3000', 'http://127.0.0.1:3000'])
    
    # Initialize database
    init_db(app)
    
    # Initialize services
    analyzer = PacketAnalyzer(app.config)
    logger_service = DatabaseLogger(app.config)
    
    # Initialize packet sniffer (but don't start yet)
    packet_sniffer = PacketSniffer(app.config, packet_callback=None)
    
    # Initialize route services
    init_alerts_logger(logger_service)
    init_stats_logger(logger_service)
    init_analyze_services(analyzer, logger_service)
    init_insider_logger(logger_service)
    
    # Register blueprints
    app.register_blueprint(alerts_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(analyze_bp)
    app.register_blueprint(insider_bp)
    
    # Store services in app context for access in routes
    app.analyzer = analyzer
    app.logger_service = logger_service
    app.packet_sniffer = packet_sniffer
    app.socketio = socketio
    
    # WebSocket event handlers
    @socketio.on('connect')
    def handle_connect():
        logger.info(f"Client connected: {request.sid}")
        emit('connected', {'message': 'Connected to IDS backend'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info(f"Client disconnected: {request.sid}")
    
    @socketio.on('join_room')
    def handle_join_room(data):
        room = data.get('room', 'dashboard')
        join_room(room)
        logger.info(f"Client {request.sid} joined room: {room}")
        emit('joined_room', {'room': room})
    
    @socketio.on('leave_room')
    def handle_leave_room(data):
        room = data.get('room', 'dashboard')
        leave_room(room)
        logger.info(f"Client {request.sid} left room: {room}")
        emit('left_room', {'room': room})
    
    # Store socketio instance globally for broadcasting
    app._socketio = socketio
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad request'}), 400
    
    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """
        Health check endpoint
        
        Returns:
        JSON response with system status
            
        Example Response:
        {
            "status": "healthy",
            "timestamp": "2024-01-15T10:30:00Z",
            "version": "1.0.0",
            "services": {
                "database": "connected",
                "packet_sniffer": "running",
                "analyzer": "active"
            },
            "uptime": "2h 15m 30s"
        }
        """
        try:
            # Check database connection
            from models.db_models import db
            db.session.execute('SELECT 1')
            db_status = 'connected'
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            db_status = 'disconnected'
        
        # Check packet sniffer status
        sniffer_stats = app.packet_sniffer.get_stats()
        sniffer_status = 'running' if sniffer_stats.get('running', False) else 'stopped'
        
        # Check analyzer status
        analyzer_stats = app.analyzer.get_model_stats()
        analyzer_status = 'active' if analyzer_stats.get('is_trained', False) else 'training'
        
        return jsonify({
            'status': 'healthy' if db_status == 'connected' else 'degraded',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'services': {
                'database': db_status,
                'packet_sniffer': sniffer_status,
                'analyzer': analyzer_status
            },
            'uptime': 'N/A',  # Could be implemented with process start time
            'sniffer_stats': {
                'total_packets': sniffer_stats.get('total_packets', 0),
                'packet_rate': sniffer_stats.get('packet_rate', 0),
                'queue_size': sniffer_stats.get('queue_size', 0)
            },
            'analyzer_stats': {
                'is_trained': analyzer_stats.get('is_trained', False),
                'training_samples': analyzer_stats.get('training_samples', 0)
            }
        })
    
    # System info endpoint
    @app.route('/api/system/info', methods=['GET'])
    def system_info():
        """
        Get system information and configuration
        
        Returns:
        JSON response with system information
            
        Example Response:
        {
            "system_info": {
                "python_version": "3.9.0",
                "flask_version": "3.0.0",
                "scapy_version": "2.5.0"
            },
            "configuration": {
                "capture_interface": "any",
                "packet_rate_threshold": 1000,
                "anomaly_score_threshold": 0.5,
                "whitelist_ips": ["127.0.0.1", "10.0.0.0/8"]
            },
            "database_info": {
                "type": "sqlite",
                "url": "sqlite:///ids.db"
            }
        }
        """
        import sys
        import flask
        import scapy
        
        return jsonify({
            'system_info': {
                'python_version': sys.version,
                'flask_version': flask.__version__,
                'scapy_version': scapy.__version__
            },
            'configuration': {
                'capture_interface': app.config.get('CAPTURE_INTERFACE', 'any'),
                'packet_rate_threshold': app.config.get('PACKET_RATE_THRESHOLD', 1000),
                'connection_limit': app.config.get('CONNECTION_LIMIT', 100),
                'anomaly_score_threshold': app.config.get('ANOMALY_SCORE_THRESHOLD', 0.5),
                'whitelist_ips': app.config.get('WHITELIST_IPS', []),
                'alert_dedup_window': app.config.get('ALERT_DEDUP_WINDOW', 300)
            },
            'database_info': {
                'type': 'sqlite' if 'sqlite' in app.config.get('DATABASE_URL', '') else 'postgresql',
                'url': app.config.get('DATABASE_URL', '').replace(app.config.get('SECRET_KEY', ''), '***')
            }
        })
    
    # Start packet processing thread
    def start_packet_processing():
        """Start packet processing in background thread"""
        logger.info("Starting packet processing thread")
        
        while True:
            try:
                # Get packet from sniffer queue
                packet_data = app.packet_sniffer.get_packet(timeout=1.0)
                if packet_data:
                    # Analyze packet
                    detections = app.analyzer.analyze_packet(packet_data)
                    
                    # Log detections and broadcast alerts
                    for detection in detections:
                        alert = app.logger_service.log_alert(detection, packet_data)
                        if alert:
                            # Broadcast new alert to all connected clients
                            with app.app_context():
                                app._socketio.emit('new_alert', {
                                    'type': 'alert',
                                    'data': alert.to_dict()
                                }, room='dashboard')
                    
                    # Log traffic statistics
                    app.logger_service.log_traffic_stats(packet_data)
                    
                    # Broadcast traffic update every 10 packets
                    if app.packet_sniffer.stats['total_packets'] % 10 == 0:
                        with app.app_context():
                            app._socketio.emit('traffic_update', {
                                'type': 'traffic_stats',
                                'data': app.packet_sniffer.get_stats()
                            }, room='dashboard')
                    
            except Exception as e:
                logger.error(f"Error in packet processing: {e}")
    
    # Start packet sniffer
    def start_services():
        """Start all background services"""
        try:
            # Start packet sniffer
            logger.info("Starting packet capture service...")
            app.packet_sniffer.start_capture()
            
            # Check if packet sniffer is actually running
            if app.packet_sniffer.running:
                logger.info("Packet sniffer started successfully!")
                logger.info("Real-time packet capture is now active")
            else:
                logger.warning("Packet sniffer failed to start")
                logger.info("This usually means insufficient privileges")
                logger.info("Run as Administrator or use start_backend_admin.ps1")
                logger.info("The system will continue in analysis-only mode")
            
            # Start packet processing thread
            processing_thread = threading.Thread(
                target=start_packet_processing,
                name="PacketProcessing",
                daemon=True
            )
            processing_thread.start()
            logger.info("Packet processing thread started")
            
        except Exception as e:
            logger.error(f"Error starting services: {e}")
            logger.info("Services will run in degraded mode (manual analysis only)")
            logger.info("Try running with Administrator privileges for full functionality")
    
    # Signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        
        # Stop packet sniffer
        app.packet_sniffer.stop_capture()
        logger.info("Packet sniffer stopped")
        
        # Flush any remaining traffic stats
        app.logger_service._flush_traffic_stats()
        logger.info("Traffic stats flushed")
        
        logger.info("Shutdown complete")
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start services immediately
    with app.app_context():
        try:
            start_services()
        except Exception as e:
            logger.error(f"Error starting services: {e}")
    
    return app

def main():
    """Main entry point for the application"""
    # Get configuration from environment
    config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Create application
    app = create_app(config_name)
    
    # Run application
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 3002))
    debug = config_name == 'development'
    
    logger.info(f"Starting Flask IDS Backend on {host}:{port}")
    logger.info(f"Configuration: {config_name}")
    logger.info(f"Debug mode: {debug}")
    
    try:
        # Run with SocketIO instead of regular Flask
        app.socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error running application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    import os
    main()
