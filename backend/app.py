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
import time
from datetime import datetime, timezone, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import config, DevelopmentConfig
from models.db_models import init_db, alerts_collection
from services.packet_sniffer import PacketSniffer
from services.analyzer import PacketAnalyzer
from services.logger import DatabaseLogger, normalize_protocol
from routes.alerts import alerts_bp, init_logger as init_alerts_logger
from routes.stats import stats_bp, init_logger as init_stats_logger
from routes.analyze import analyze_bp, init_services as init_analyze_services
from routes.pcap import pcap_bp, init_pcap_services
from routes.training import training_bp, init_services as init_training_services
from datetime import timedelta

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
    
    # Initialize rate limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per hour", "50 per minute"],
        storage_uri=os.environ.get('RATE_LIMIT_STORAGE_URI') or "memory://",
        strategy="fixed-window"
    )
    
    # Store limiter in app context
    app.limiter = limiter
    
    # Initialize SocketIO for real-time communication
    # Use threading mode for better compatibility
    socketio = SocketIO(
        app, 
        cors_allowed_origins=['http://localhost:3000', 'http://127.0.0.1:3000'],
        async_mode='threading',
        logger=False,
        engineio_logger=False
    )
    
    # Initialize database
    init_db(app)
    
    # Initialize services
    analyzer = PacketAnalyzer(app.config)
    logger_service = DatabaseLogger(app.config)
    
    # Initialize packet sniffer with auto-start enabled
    # Scapy will automatically load and start collecting logs when backend starts
    packet_sniffer = PacketSniffer(app.config, packet_callback=None, auto_start=getattr(app.config, 'SCAPY_AUTO_START', True))
    
    # Initialize route services
    init_alerts_logger(logger_service)
    init_stats_logger(logger_service)
    init_analyze_services(analyzer, logger_service)
    init_pcap_services(app.config, packet_analyzer=analyzer)
    
    # Initialize training services if classification is enabled (SecIDS-CNN only needs FeatureExtractor)
    training_data_collector = None
    training_feature_extractor = None
    if getattr(app.config, 'CLASSIFICATION_ENABLED', False):
        try:
            from services.feature_extractor import FeatureExtractor
            training_feature_extractor = FeatureExtractor(app.config)
            use_secids = getattr(app.config, 'CLASSIFICATION_MODEL_TYPE', None) == 'secids_cnn'
            if not use_secids:
                from services.data_collector import DataCollector
                training_data_collector = DataCollector(app.config)
            else:
                try:
                    from services.data_collector import DataCollector
                    training_data_collector = DataCollector(app.config)
                except Exception:
                    training_data_collector = None
            init_training_services(training_data_collector, training_feature_extractor, app.config)
        except Exception as e:
            logger.warning(f"Could not initialize training services: {e}")
    
    # Register blueprints
    app.register_blueprint(alerts_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(analyze_bp)
    app.register_blueprint(training_bp)
    app.register_blueprint(pcap_bp)
    
    # Apply rate limits to specific endpoints after blueprint registration
    # Use .get() to safely access view_functions (handles missing functions gracefully)
    if 'delete_alert' in alerts_bp.view_functions:
        limiter.limit("10 per minute")(alerts_bp.view_functions['delete_alert'])
    if 'bulk_delete_alerts' in alerts_bp.view_functions:
        limiter.limit("5 per minute")(alerts_bp.view_functions['bulk_delete_alerts'])
    if 'bulk_resolve_alerts' in alerts_bp.view_functions:
        limiter.limit("10 per minute")(alerts_bp.view_functions['bulk_resolve_alerts'])
    if 'analyze_packet' in analyze_bp.view_functions:
        limiter.limit("30 per minute")(analyze_bp.view_functions['analyze_packet'])
    if 'analyze_bulk_packets' in analyze_bp.view_functions:
        limiter.limit("10 per minute")(analyze_bp.view_functions['analyze_bulk_packets'])
    if 'train_model' in training_bp.view_functions:
        limiter.limit("20 per minute")(training_bp.view_functions['train_model'])
    if 'label_sample' in training_bp.view_functions:
        limiter.limit("20 per minute")(training_bp.view_functions['label_sample'])
    if 'analyze_pcap' in pcap_bp.view_functions:
        limiter.limit("8 per minute")(pcap_bp.view_functions['analyze_pcap'])
    if 'get_last_result' in pcap_bp.view_functions:
        limiter.limit("20 per minute")(pcap_bp.view_functions['get_last_result'])
    
    # Store services in app context for access in routes
    app.analyzer = analyzer
    app.logger_service = logger_service
    app.packet_sniffer = packet_sniffer
    app.socketio = socketio
    
    # WebSocket event handlers
    @socketio.on('connect')
    def handle_connect():
        try:
            logger.info(f"Client connected: {request.sid}")
            emit('connected', {'message': 'Connected to IDS backend'})
        except Exception as e:
            logger.error(f"Error handling WebSocket connect: {e}")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        try:
            logger.info(f"Client disconnected: {request.sid}")
        except Exception as e:
            logger.error(f"Error handling WebSocket disconnect: {e}")
    
    @socketio.on_error_default
    def default_error_handler(e):
        """Default error handler for SocketIO events"""
        logger.error(f"SocketIO error: {e}")
        return False
    
    @socketio.on('join_room')
    def handle_join_room(data):
        try:
            room = data.get('room', 'dashboard')
            join_room(room)
            logger.info(f"Client {request.sid} joined room: {room}")
            emit('joined_room', {'room': room})
        except Exception as e:
            logger.error(f"Error handling join_room: {e}")
    
    @socketio.on('leave_room')
    def handle_leave_room(data):
        try:
            room = data.get('room', 'dashboard')
            leave_room(room)
            logger.info(f"Client {request.sid} left room: {room}")
            emit('left_room', {'room': room})
        except Exception as e:
            logger.error(f"Error handling leave_room: {e}")
    
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
            from models.db_models import get_client
            client = get_client(app.config)
            client.admin.command('ping')
            db_status = 'connected'
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            db_status = 'disconnected'
        
        # Check packet sniffer status with detailed diagnostics
        sniffer_stats = app.packet_sniffer.get_stats()
        # Check both running flag and thread status for accurate reporting
        is_running = sniffer_stats.get('running', False)
        has_capture_thread = app.packet_sniffer.capture_thread is not None and app.packet_sniffer.capture_thread.is_alive()
        sniffer_status = 'running' if (is_running or has_capture_thread) else 'stopped'
        logger.debug(f"[HealthCheck] Sniffer status: running={is_running}, thread_alive={has_capture_thread}, status={sniffer_status}")
        
        # Capture health diagnostics
        capture_healthy = sniffer_stats.get('capture_healthy')
        capture_warning = sniffer_stats.get('capture_warning')
        last_packet_age = sniffer_stats.get('last_packet_age_seconds')
        total_packets = sniffer_stats.get('total_packets', 0)
        
        # Determine overall health status
        if capture_healthy is False:
            sniffer_status = 'degraded'
        elif capture_healthy is None and total_packets == 0 and is_running:
            # Running but no packets yet - might be starting up or no traffic
            if last_packet_age and last_packet_age > 30:
                sniffer_status = 'warning'  # Been running but no packets
        
        # Check analyzer status
        analyzer_stats = app.analyzer.get_model_stats()
        analyzer_status = 'active' if analyzer_stats.get('is_trained', False) else 'training'
        classification = analyzer_stats.get('classification', {})
        secids_active = (
            classification.get('enabled') and
            classification.get('is_trained', False) and
            classification.get('model_type') == 'secids_cnn'
        )
        
        # Overall system status: when SecIDS is active and trained, report healthy even if MongoDB is down (SecIDS-only mode)
        overall_status = 'healthy'
        secids_only_note = None
        if db_status != 'connected':
            if secids_active:
                overall_status = 'healthy'
                secids_only_note = 'SecIDS-only mode: MongoDB unavailable; classification and PCAP analysis still operational.'
            else:
                overall_status = 'degraded'
        elif sniffer_status in ['degraded', 'warning']:
            overall_status = 'degraded'
        
        response = {
            'status': overall_status,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': '1.0.0',
            'services': {
                'database': db_status,
                'packet_sniffer': sniffer_status,
                'analyzer': analyzer_status
            },
            'uptime': 'N/A',  # Could be implemented with process start time
            'sniffer_stats': {
                'total_packets': total_packets,
                'packet_rate': sniffer_stats.get('packet_rate', 0),
                'queue_size': sniffer_stats.get('queue_size', 0),
                'active_connections': sniffer_stats.get('active_connections', 0),
                'capture_healthy': capture_healthy,
                'last_packet_age_seconds': last_packet_age,
                'capture_warning': capture_warning,
                'interface': app.packet_sniffer.interface,
                'thread_alive': has_capture_thread
            },
            'analyzer_stats': {
                'is_trained': analyzer_stats.get('is_trained', False),
                'training_samples': analyzer_stats.get('training_samples', 0)
            },
            'recommendations': _get_health_recommendations(db_status, sniffer_status, capture_healthy, capture_warning, total_packets, has_capture_thread)
        }
        if secids_only_note:
            response['note'] = secids_only_note
        return jsonify(response)
    
    def _get_health_recommendations(db_status, sniffer_status, capture_healthy, capture_warning, total_packets, has_capture_thread):
        """Generate actionable recommendations based on health status"""
        recommendations = []
        
        if db_status != 'connected':
            recommendations.append("Database connection failed. Check MongoDB connection string and ensure MongoDB is running.")
        
        if sniffer_status == 'stopped':
            import platform
            is_windows = platform.system() == 'Windows'
            if is_windows:
                recommendations.append("Packet capture is stopped. Run as Administrator or use start_backend_admin.ps1")
            else:
                recommendations.append("Packet capture is stopped. Run with sudo: sudo python app.py")
        
        if capture_healthy is False:
            if capture_warning:
                recommendations.append(capture_warning)
            import platform
            is_windows = platform.system() == 'Windows'
            if is_windows:
                recommendations.append("If no packets are being captured, ensure you're running as Administrator.")
            else:
                recommendations.append("If no packets are being captured, ensure you're running with sudo privileges.")
                recommendations.append("Check interface permissions: sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/python3")
        
        if not has_capture_thread and sniffer_status == 'running':
            recommendations.append("Packet capture thread is not alive. Restart the backend.")
        
        if total_packets == 0 and has_capture_thread:
            recommendations.append("Packet capture appears to be running but no packets received. Verify network interface and permissions.")
        
        return recommendations if recommendations else ["All systems operational"]
    
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
    
    # Test endpoint to manually trigger an alert
    @app.route('/api/test/trigger-alert', methods=['POST'])
    def trigger_test_alert():
        """
        Manually trigger a test alert to verify WebSocket broadcasting
        
        Request Body (optional):
        {
            "severity": "high",
            "alert_type": "test",
            "description": "Test alert for verification",
            "source_ip": "192.168.1.100",
            "dest_ip": "10.0.0.1"
        }
        
        Returns:
        JSON response with alert creation status
        """
        try:
            data = request.get_json() or {}
            
            # Create test detection
            test_detection = {
                'type': data.get('alert_type', 'test'),
                'signature_id': 'test_alert',
                'severity': data.get('severity', 'medium'),
                'description': data.get('description', 'Test alert triggered manually for verification'),
                'confidence': 1.0,
                'matched_pattern': 'manual_test',
                'source': 'test_endpoint'
            }
            
            # Create test packet data
            test_packet = {
                'src_ip': data.get('source_ip', '192.168.1.100'),
                'dst_ip': data.get('dest_ip', '10.0.0.1'),
                'protocol': 'TCP',
                'dst_port': 80,
                'src_port': 54321,
                'payload_size': 0,
                'raw_size': 0,
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Log the alert
            alert = app.logger_service.log_alert(test_detection, test_packet)
            
            if alert:
                # Broadcast alert via WebSocket
                alert_broadcast = {
                    'type': 'new_alert',
                    'alert_id': str(alert.get('_id', '')),
                    'severity': alert.get('severity', 'medium'),
                    'alert_type': test_detection.get('type', 'test'),
                    'description': alert.get('description', 'Test alert'),
                    'source_ip': alert.get('source_ip', '192.168.1.100'),
                    'dest_ip': alert.get('dest_ip', '10.0.0.1'),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                try:
                    app._socketio.emit('new_alert', alert_broadcast, room='dashboard')
                    logger.info(f"Test alert broadcast via WebSocket: {alert_broadcast['alert_id']}")
                except Exception as e:
                    logger.error(f"Error broadcasting test alert via WebSocket: {e}")
                    return jsonify({
                        'success': False,
                        'error': f'Alert created but WebSocket broadcast failed: {str(e)}',
                        'alert_id': str(alert.get('_id', ''))
                    }), 500
                
                return jsonify({
                    'success': True,
                    'message': 'Test alert created and broadcast successfully',
                    'alert_id': str(alert.get('_id', '')),
                    'alert': alert_broadcast
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Alert was deduplicated or creation failed',
                    'message': 'This may happen if a similar alert was recently created'
                }), 400
                
        except Exception as e:
            logger.error(f"Error triggering test alert: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # Test endpoint to manually inject a packet for testing
    @app.route('/api/test/inject-packet', methods=['POST'])
    def inject_test_packet():
        """
        Manually inject a packet into the processing pipeline for testing
        
        This allows testing the entire analysis pipeline without requiring packet capture.
        Useful for debugging and verifying the system works end-to-end.
        
        Request Body (optional):
        {
            "src_ip": "192.168.1.100",
            "dst_ip": "8.8.8.8",
            "src_port": 54321,
            "dst_port": 80,
            "protocol": "TCP",
            "payload_size": 100,
            "raw_size": 150
        }
        
        Returns:
        JSON response with packet processing status
        """
        try:
            data = request.get_json() or {}
            
            # Create test packet data
            test_packet = {
                'src_ip': data.get('src_ip', '192.168.1.100'),
                'dst_ip': data.get('dst_ip', '8.8.8.8'),
                'src_port': data.get('src_port', 54321),
                'dst_port': data.get('dst_port', 80),
                'protocol': data.get('protocol', 'TCP'),
                'payload_size': data.get('payload_size', 100),
                'raw_size': data.get('raw_size', 150),
                'timestamp': datetime.now(timezone.utc),
                'flags': None,
                'payload_preview': None
            }
            
            # Update packet sniffer statistics to reflect injected packet
            app.packet_sniffer.stats['total_packets'] += 1
            app.packet_sniffer.stats['total_bytes'] += test_packet['raw_size']
            app.packet_sniffer.stats['last_packet_time'] = datetime.now(timezone.utc)
            app.packet_sniffer.recent_packet_timestamps.append(datetime.now(timezone.utc))
            
            # Update connection tracking
            app.packet_sniffer._update_connection_tracking(test_packet)
            
            # Process packet through analyzer
            detections = app.analyzer.analyze_packet(test_packet)
            
            # Log detections and broadcast alerts
            alerts_created = []
            for detection in detections:
                alert = app.logger_service.log_alert(detection, test_packet)
                if alert:
                    alerts_created.append(str(alert.get('_id', '')))
                    # Broadcast alert via WebSocket
                    alert_broadcast = {
                        'type': 'new_alert',
                        'alert_id': str(alert.get('_id', '')),
                        'severity': alert.get('severity', 'medium'),
                        'alert_type': detection.get('type', 'unknown'),
                        'description': alert.get('description', ''),
                        'source_ip': alert.get('source_ip', test_packet['src_ip']),
                        'dest_ip': alert.get('dest_ip', test_packet['dst_ip']),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    try:
                        app._socketio.emit('new_alert', alert_broadcast, room='dashboard')
                    except Exception as e:
                        logger.error(f"Error broadcasting test alert via WebSocket: {e}")
            
            # Log traffic statistics
            app.logger_service.log_traffic_stats(test_packet)
            
            return jsonify({
                'success': True,
                'message': 'Test packet injected and processed successfully',
                'packet': test_packet,
                'detections': len(detections),
                'alerts_created': alerts_created,
                'stats': {
                    'total_packets': app.packet_sniffer.stats['total_packets'],
                    'active_connections': len(app.packet_sniffer.connections)
                }
            })
                
        except Exception as e:
            logger.error(f"Error injecting test packet: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # Helper function to get recent threats count
    def _get_recent_threats_count(since_time: datetime) -> int:
        """
        Get count of recent threats/alerts detected since given time
        
        Args:
            since_time: Datetime to count threats since
            
        Returns:
            Number of threats detected since since_time
        """
        try:
            with app.app_context():
                # Ensure since_time is timezone-aware
                if since_time.tzinfo is None:
                    since_time = since_time.replace(tzinfo=timezone.utc)
                
                # Query alerts created since the given time
                if alerts_collection is not None:
                    recent_alerts_count = alerts_collection.count_documents({
                        'timestamp': {'$gte': since_time}
                    })
                    return recent_alerts_count
                else:
                    return 0
        except Exception as e:
            logger.debug(f"Error getting recent threats count: {e}")
            return 0
    
    # Periodic broadcast function for real-time updates
    def periodic_broadcast():
        """Send periodic updates via WebSocket even when no packets are captured"""
        broadcast_interval = getattr(app.config, 'WEBSOCKET_BROADCAST_INTERVAL', 5)
        last_broadcast_time = datetime.now(timezone.utc)
        logger.info(f"[PeriodicBroadcast] Thread started, broadcasting every {broadcast_interval} seconds")
        
        while True:
            try:
                time.sleep(broadcast_interval)
                
                with app.app_context():
                    try:
                        # Force connection cleanup before getting stats
                        app.packet_sniffer._cleanup_stale_connections()
                        
                        # Get real-time stats from cache
                        realtime_stats = app.logger_service.get_realtime_stats()
                        sniffer_stats = app.packet_sniffer.get_stats()
                        
                        # Get recent threats count since last broadcast
                        current_time = datetime.now(timezone.utc)
                        # Ensure last_broadcast_time is timezone-aware
                        if last_broadcast_time.tzinfo is None:
                            last_broadcast_time = last_broadcast_time.replace(tzinfo=timezone.utc)
                        recent_threats = _get_recent_threats_count(last_broadcast_time)
                        last_broadcast_time = current_time
                        
                        # Format stats for frontend
                        packet_rate = sniffer_stats.get('packet_rate', 0)
                        traffic_stats = {
                            'type': 'traffic_update',
                            'packets_per_second': packet_rate,
                            'threats_detected': recent_threats,
                            'active_connections': sniffer_stats.get('active_connections', 0),
                            'bandwidth_mbps': (sniffer_stats.get('byte_rate', 0) / (1024 * 1024)) if sniffer_stats.get('byte_rate') else 0,
                            'total_packets': sniffer_stats.get('total_packets', 0),
                            'total_bytes': sniffer_stats.get('total_bytes', 0),
                            'protocol_distribution': realtime_stats.get('protocol_distribution', {}),
                            'timestamp': current_time.isoformat()
                        }
                        # Debug logging for packet rate - log even when 0 to confirm broadcasts are happening
                        logger.debug(f"[PeriodicBroadcast] Sending traffic_update: packets_per_second={packet_rate:.2f}, total_packets={sniffer_stats.get('total_packets', 0)}, sniffer_running={sniffer_stats.get('running', False)}, active_connections={sniffer_stats.get('active_connections', 0)}")
                        app._socketio.emit('traffic_update', traffic_stats, room='dashboard')
                    except Exception as e:
                        logger.warning(f"[PeriodicBroadcast] Error in periodic broadcast: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"[PeriodicBroadcast] Error in periodic broadcast loop: {e}", exc_info=True)
                time.sleep(5)
    
    # Start packet processing thread
    def start_packet_processing():
        """Start packet processing in background thread with enhanced WebSocket broadcasting"""
        logger.info("Starting packet processing thread")
        
        last_broadcast_time = datetime.now(timezone.utc)
        last_connection_count = 0
        packet_count_since_broadcast = 0
        broadcast_interval = getattr(app.config, 'WEBSOCKET_BROADCAST_INTERVAL', 5)
        packet_threshold = getattr(app.config, 'WEBSOCKET_BROADCAST_PACKET_THRESHOLD', 5)
        
        while True:
            try:
                # Get packet from sniffer queue
                packet_data = app.packet_sniffer.get_packet(timeout=1.0)
                if packet_data:
                    # Analyze packet
                    detections = app.analyzer.analyze_packet(packet_data)
                    
                    # Diagnostic logging for detections
                    if detections:
                        logger.info(f"Detections found: {len(detections)} - Types: {[d.get('type', 'unknown') for d in detections]}")
                    else:
                        logger.debug(f"No detections for packet from {packet_data.get('src_ip', 'unknown')}")
                    
                    # Log detections and broadcast alerts
                    for detection in detections:
                        logger.debug(f"Processing detection: type={detection.get('type')}, severity={detection.get('severity')}, signature_id={detection.get('signature_id')}")
                        alert = app.logger_service.log_alert(detection, packet_data)
                        if alert:
                            logger.info(f"Alert created and will be broadcast: ID={alert.get('_id', 'unknown')}, Type={detection.get('type')}, Severity={detection.get('severity')}")
                            # Broadcast new alert to all connected clients immediately
                            with app.app_context():
                                alert_broadcast = {
                                    'type': 'new_alert',
                                    'alert_id': str(alert.get('_id', '')),
                                    'severity': alert.get('severity', detection.get('severity', 'medium')),
                                    'alert_type': detection.get('type', 'unknown'),
                                    'description': alert.get('description', detection.get('description', '')),
                                    'source_ip': alert.get('source_ip', packet_data.get('src_ip', 'unknown')),
                                    'dest_ip': alert.get('dest_ip', packet_data.get('dst_ip', 'unknown')),
                                    'timestamp': datetime.now(timezone.utc).isoformat()
                                }
                                try:
                                    app._socketio.emit('new_alert', alert_broadcast, room='dashboard')
                                    logger.info(f"Alert broadcast via WebSocket: {alert_broadcast['alert_id']}")
                                except Exception as e:
                                    logger.error(f"Error broadcasting alert via WebSocket: {e}")
                        else:
                            logger.debug(f"Alert deduplicated or failed: type={detection.get('type')}, src_ip={packet_data.get('src_ip', 'unknown')}")
                    
                    # Log traffic statistics
                    app.logger_service.log_traffic_stats(packet_data)
                    
                    packet_count_since_broadcast += 1
                    
                    # Check if we need to broadcast (every 5 seconds OR every 5 packets, whichever comes first)
                    current_time = datetime.now(timezone.utc)
                    time_since_broadcast = (current_time - last_broadcast_time).total_seconds()
                    current_connection_count = len(app.packet_sniffer.connections)
                    
                    should_broadcast = False
                    connection_changed = (current_connection_count != last_connection_count)
                    
                    # Broadcast if time threshold or packet threshold reached, or connection count changed
                    if (time_since_broadcast >= broadcast_interval or 
                        packet_count_since_broadcast >= packet_threshold or
                        connection_changed):
                        should_broadcast = True
                    
                    if should_broadcast:
                        with app.app_context():
                            sniffer_stats = app.packet_sniffer.get_stats()
                            protocol_dist = {}
                            
                            # Get protocol distribution from traffic stats cache
                            for key, count in app.logger_service.traffic_stats_cache.items():
                                if key.startswith('protocol_'):
                                    protocol = key.replace('protocol_', '')
                                    # Normalize protocol name before sending
                                    normalized_protocol = normalize_protocol(protocol)
                                    if normalized_protocol and normalized_protocol != 'Other':
                                        # Aggregate counts for the same normalized protocol
                                        if normalized_protocol in protocol_dist:
                                            protocol_dist[normalized_protocol] += count
                                        else:
                                            protocol_dist[normalized_protocol] = count
                            
                            # Format stats for frontend
                            packet_rate = sniffer_stats.get('packet_rate', 0)
                            traffic_stats = {
                                'type': 'traffic_update',
                                'packets_per_second': packet_rate,
                                'threats_detected': len(detections) if detections else 0,
                                'active_connections': sniffer_stats.get('active_connections', 0),
                                'bandwidth_mbps': (sniffer_stats.get('byte_rate', 0) / (1024 * 1024)) if sniffer_stats.get('byte_rate') else 0,
                                'total_packets': sniffer_stats.get('total_packets', 0),
                                'total_bytes': sniffer_stats.get('total_bytes', 0),
                                'protocol_distribution': protocol_dist,
                                'timestamp': current_time.isoformat()
                            }
                            # Debug logging for packet rate
                            logger.debug(f"[PacketProcessing] Sending traffic_update: packets_per_second={packet_rate}, total_packets={sniffer_stats.get('total_packets', 0)}, sniffer_running={sniffer_stats.get('running', False)}")
                            app._socketio.emit('traffic_update', traffic_stats, room='dashboard')
                            
                            # Broadcast connection state change if it changed
                            if connection_changed:
                                app._socketio.emit('connection_update', {
                                    'active_connections': current_connection_count,
                                    'timestamp': current_time.isoformat()
                                }, room='dashboard')
                                last_connection_count = current_connection_count
                            
                            last_broadcast_time = current_time
                            packet_count_since_broadcast = 0
                    
            except Exception as e:
                logger.error(f"Error in packet processing: {e}")
    
    # Start packet sniffer
    def start_services():
        """Start all background services"""
        try:
            # Scapy auto-starts during initialization, but verify it's running
            logger.info("🚀 Auto-starting Scapy packet capture...")
            
            # If auto-start didn't happen in __init__, start it now
            if not app.packet_sniffer.running:
                app.packet_sniffer.start_capture()
            
            # Wait up to 2 seconds to verify Scapy started
            import time
            for _ in range(20):  # Check 20 times over 2 seconds
                time.sleep(0.1)
                if app.packet_sniffer.running:
                    break
            
            # Check if packet sniffer is actually running
            if app.packet_sniffer.running:
                logger.info("✅ Packet sniffer started successfully!")
                logger.info("📡 Scapy packet capture is now active - collecting logs")
                logger.info(f"📝 Monitoring interface: {app.packet_sniffer.interface}")
            else:
                logger.warning("⚠️  Packet sniffer failed to start")
                logger.info("This usually means insufficient privileges")
                import platform
                if platform.system() == 'Windows':
                    logger.info("SOLUTION: Run as Administrator or use start_backend_admin.ps1")
                else:
                    logger.info("SOLUTION: Run with sudo to enable packet capture")
                logger.info("NOTE: Backend running but packet capture unavailable - check permissions")
                logger.info("The system will continue in analysis-only mode")
            
            # Start packet processing thread
            processing_thread = threading.Thread(
                target=start_packet_processing,
                name="PacketProcessing",
                daemon=True
            )
            processing_thread.start()
            logger.info("Packet processing thread started")
            
            # Start periodic broadcast thread for real-time updates
            broadcast_thread = threading.Thread(
                target=periodic_broadcast,
                name="PeriodicBroadcast",
                daemon=True
            )
            broadcast_thread.start()
            logger.info("Periodic broadcast thread started (updates every 5 seconds)")
            
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
