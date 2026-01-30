"""
Packet analysis API routes for Flask IDS Backend
Provides endpoints for on-demand packet and flow analysis
"""

import logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from services.analyzer import PacketAnalyzer
from services.logger import DatabaseLogger

logger = logging.getLogger(__name__)

# Create blueprint
analyze_bp = Blueprint('analyze', __name__)

# Initialize services (will be injected from main app)
analyzer = None
logger_service = None

def init_services(analyzer_instance, logger_instance):
    """Initialize analyzer and logger services"""
    global analyzer, logger_service
    analyzer = analyzer_instance
    logger_service = logger_instance

@analyze_bp.route('/api/analyze', methods=['POST'])
def analyze_packet():
    """
    Analyze packet data for threats
    
    Request Body:
    {
        "packet_data": {
            "src_ip": "192.168.1.100",
            "dst_ip": "10.0.0.1",
            "protocol": "TCP",
            "src_port": 12345,
            "dst_port": 80,
            "payload_size": 1024,
            "payload_preview": "474554202f6170692f75736572733f69643d31...",
            "flags": "SYN",
            "user_agent": "Mozilla/5.0...",
            "uri": "/api/users?id=1' OR 1=1--",
            "http_method": "GET",
            "timestamp": "2024-01-15T10:30:00Z"
        },
        "save_results": true,
        "analysis_types": ["signature", "anomaly"]
    }
    
    Returns:
    JSON response with analysis results
    
    Example Response:
    {
        "analysis_results": [
            {
                "type": "signature",
                "signature_id": "sql_injection",
                "severity": "high",
                "description": "Potential SQL injection attempt detected",
                "confidence": 0.85,
                "matched_pattern": "union\\s+select",
                "source": "payload_analysis"
            }
        ],
        "packet_summary": {
            "src_ip": "192.168.1.100",
            "dst_ip": "10.0.0.1",
            "protocol": "TCP",
            "dst_port": 80,
            "timestamp": "2024-01-15T10:30:00Z",
            "threat_level": "high"
        },
        "saved_alerts": [1],
        "analysis_metadata": {
            "analysis_time": "2024-01-15T10:30:01Z",
            "processing_time_ms": 45,
            "model_version": "1.0",
            "analysis_types": ["signature", "anomaly"]
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        packet_data = data.get('packet_data')
        if not packet_data:
            return jsonify({'error': 'packet_data is required'}), 400
        
        save_results = data.get('save_results', False)
        analysis_types = data.get('analysis_types', ['signature', 'anomaly'])
        
        # Validate required fields
        required_fields = ['src_ip', 'dst_ip', 'protocol']
        missing_fields = [field for field in required_fields if not packet_data.get(field)]
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Add timestamp if not provided
        if not packet_data.get('timestamp'):
            packet_data['timestamp'] = datetime.now(timezone.utc)
        
        start_time = datetime.now(timezone.utc)
        
        # Perform analysis
        detections = analyzer.analyze_packet(packet_data)
        
        # Filter by analysis types if specified
        if analysis_types and analysis_types != ['all']:
            detections = [d for d in detections if d.get('type') in analysis_types]
        
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        # Determine overall threat level
        threat_level = 'low'
        if detections:
            severities = [d.get('severity', 'low') for d in detections]
            if 'critical' in severities:
                threat_level = 'critical'
            elif 'high' in severities:
                threat_level = 'high'
            elif 'medium' in severities:
                threat_level = 'medium'
        
        # Save results to database if requested
        saved_alerts = []
        if save_results and detections:
            for detection in detections:
                alert = logger_service.log_alert(detection, packet_data)
                if alert:
                    saved_alerts.append(alert.id)
        
        # Create packet summary
        packet_summary = {
            'src_ip': packet_data.get('src_ip'),
            'dst_ip': packet_data.get('dst_ip'),
            'protocol': packet_data.get('protocol'),
            'dst_port': packet_data.get('dst_port'),
            'timestamp': packet_data.get('timestamp'),
            'threat_level': threat_level
        }
        
        response = {
            'analysis_results': detections,
            'packet_summary': packet_summary,
            'saved_alerts': saved_alerts,
            'analysis_metadata': {
                'analysis_time': datetime.now(timezone.utc).isoformat(),
                'processing_time_ms': round(processing_time, 2),
                'model_version': '1.0',
                'analysis_types': analysis_types,
                'detections_count': len(detections)
            }
        }
        
        logger.info(f"Analyzed packet: {len(detections)} detections, threat_level: {threat_level}")
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error analyzing packet: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@analyze_bp.route('/api/analyze/bulk', methods=['POST'])
def analyze_bulk_packets():
    """
    Analyze multiple packets in bulk
    
    Request Body:
    {
        "packets": [
            {
                "src_ip": "192.168.1.100",
                "dst_ip": "10.0.0.1",
                "protocol": "TCP",
                "dst_port": 80,
                "payload_preview": "..."
            }
        ],
        "save_results": true,
        "analysis_types": ["signature", "anomaly"]
    }
    
    Returns:
    JSON response with bulk analysis results
    
    Example Response:
    {
        "results": [
            {
                "packet_index": 0,
                "analysis_results": [...],
                "threat_level": "medium",
                "saved_alerts": [1, 2]
            }
        ],
        "summary": {
            "total_packets": 5,
            "threats_detected": 3,
            "total_alerts_saved": 4,
            "processing_time_ms": 150.5
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        packets = data.get('packets', [])
        if not packets or not isinstance(packets, list):
            return jsonify({'error': 'packets must be a non-empty array'}), 400
        
        if len(packets) > 100:  # Limit bulk analysis
            return jsonify({'error': 'Maximum 100 packets allowed for bulk analysis'}), 400
        
        save_results = data.get('save_results', False)
        analysis_types = data.get('analysis_types', ['signature', 'anomaly'])
        
        start_time = datetime.now(timezone.utc)
        results = []
        total_threats = 0
        total_alerts_saved = 0
        
        for i, packet_data in enumerate(packets):
            try:
                # Add timestamp if not provided
                if not packet_data.get('timestamp'):
                    packet_data['timestamp'] = datetime.now(timezone.utc)
                
                # Perform analysis
                detections = analyzer.analyze_packet(packet_data)
                
                # Filter by analysis types if specified
                if analysis_types and analysis_types != ['all']:
                    detections = [d for d in detections if d.get('type') in analysis_types]
                
                # Determine threat level
                threat_level = 'low'
                if detections:
                    severities = [d.get('severity', 'low') for d in detections]
                    if 'critical' in severities:
                        threat_level = 'critical'
                    elif 'high' in severities:
                        threat_level = 'high'
                    elif 'medium' in severities:
                        threat_level = 'medium'
                    
                    total_threats += 1
                
                # Save results to database if requested
                saved_alerts = []
                if save_results and detections:
                    for detection in detections:
                        alert = logger_service.log_alert(detection, packet_data)
                        if alert:
                            saved_alerts.append(alert.id)
                    total_alerts_saved += len(saved_alerts)
                
                results.append({
                    'packet_index': i,
                    'analysis_results': detections,
                    'threat_level': threat_level,
                    'saved_alerts': saved_alerts,
                    'packet_summary': {
                        'src_ip': packet_data.get('src_ip'),
                        'dst_ip': packet_data.get('dst_ip'),
                        'protocol': packet_data.get('protocol'),
                        'dst_port': packet_data.get('dst_port')
                    }
                })
                
            except Exception as e:
                logger.error(f"Error analyzing packet {i}: {e}")
                results.append({
                    'packet_index': i,
                    'error': str(e),
                    'threat_level': 'unknown'
                })
        
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        response = {
            'results': results,
            'summary': {
                'total_packets': len(packets),
                'threats_detected': total_threats,
                'total_alerts_saved': total_alerts_saved,
                'processing_time_ms': round(processing_time, 2),
                'avg_processing_time_ms': round(processing_time / len(packets), 2)
            }
        }
        
        logger.info(f"Bulk analyzed {len(packets)} packets: {total_threats} threats, {total_alerts_saved} alerts saved")
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in bulk analysis: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@analyze_bp.route('/api/analyze/flow', methods=['POST'])
def analyze_flow():
    """
    Analyze network flow data
    
    Request Body:
    {
        "flow_data": {
            "src_ip": "192.168.1.100",
            "dst_ip": "10.0.0.1",
            "protocol": "TCP",
            "src_port": 12345,
            "dst_port": 80,
            "packet_count": 150,
            "byte_count": 153600,
            "duration": 30.5,
            "start_time": "2024-01-15T10:30:00Z",
            "end_time": "2024-01-15T10:30:30Z",
            "flags": "SYN,ACK,FIN"
        },
        "save_results": true
    }
    
    Returns:
    JSON response with flow analysis results
    
    Example Response:
    {
        "flow_analysis": {
            "flow_id": "192.168.1.100:12345->10.0.0.1:80",
            "threat_level": "medium",
            "anomalies_detected": [
                {
                    "type": "high_volume",
                    "description": "Unusually high packet count for single flow",
                    "severity": "medium",
                    "confidence": 0.75
                }
            ]
        },
        "flow_metrics": {
            "packet_rate": 4.92,
            "byte_rate": 5036.07,
            "avg_packet_size": 1024,
            "flow_duration": 30.5
        },
        "saved_alerts": [3],
        "analysis_metadata": {
            "analysis_time": "2024-01-15T10:30:31Z",
            "processing_time_ms": 25.3
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        flow_data = data.get('flow_data')
        if not flow_data:
            return jsonify({'error': 'flow_data is required'}), 400
        
        save_results = data.get('save_results', False)
        
        # Validate required fields
        required_fields = ['src_ip', 'dst_ip', 'protocol', 'packet_count', 'byte_count']
        missing_fields = [field for field in required_fields if not flow_data.get(field)]
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        start_time = datetime.now(timezone.utc)
        
        # Analyze flow for anomalies
        anomalies = _analyze_flow_anomalies(flow_data)
        
        # Calculate flow metrics
        duration = flow_data.get('duration', 1)  # Avoid division by zero
        packet_rate = flow_data.get('packet_count', 0) / duration
        byte_rate = flow_data.get('byte_count', 0) / duration
        avg_packet_size = flow_data.get('byte_count', 0) / flow_data.get('packet_count', 1)
        
        flow_metrics = {
            'packet_rate': round(packet_rate, 2),
            'byte_rate': round(byte_rate, 2),
            'avg_packet_size': round(avg_packet_size, 2),
            'flow_duration': duration
        }
        
        # Determine threat level
        threat_level = 'low'
        if anomalies:
            severities = [a.get('severity', 'low') for a in anomalies]
            if 'critical' in severities:
                threat_level = 'critical'
            elif 'high' in severities:
                threat_level = 'high'
            elif 'medium' in severities:
                threat_level = 'medium'
        
        # Create flow ID
        flow_id = f"{flow_data.get('src_ip')}:{flow_data.get('src_port', 0)}->{flow_data.get('dst_ip')}:{flow_data.get('dst_port', 0)}"
        
        # Save results to database if requested
        saved_alerts = []
        if save_results and anomalies:
            for anomaly in anomalies:
                # Convert flow data to packet-like format for logging
                packet_data = {
                    'src_ip': flow_data.get('src_ip'),
                    'dst_ip': flow_data.get('dst_ip'),
                    'protocol': flow_data.get('protocol'),
                    'src_port': flow_data.get('src_port'),
                    'dst_port': flow_data.get('dst_port'),
                    'payload_size': avg_packet_size,
                    'timestamp': flow_data.get('start_time', datetime.now(timezone.utc))
                }
                
                alert = logger_service.log_alert(anomaly, packet_data)
                if alert:
                    saved_alerts.append(alert.id)
        
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        response = {
            'flow_analysis': {
                'flow_id': flow_id,
                'threat_level': threat_level,
                'anomalies_detected': anomalies
            },
            'flow_metrics': flow_metrics,
            'saved_alerts': saved_alerts,
            'analysis_metadata': {
                'analysis_time': datetime.now(timezone.utc).isoformat(),
                'processing_time_ms': round(processing_time, 2)
            }
        }
        
        logger.info(f"Analyzed flow {flow_id}: {len(anomalies)} anomalies, threat_level: {threat_level}")
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error analyzing flow: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@analyze_bp.route('/api/analyze/model-info', methods=['GET'])
def get_model_info():
    """
    Get information about the analysis models
    
    Returns:
    JSON response with model information
    
    Example Response:
    {
        "signature_detector": {
            "signature_count": 7,
            "supported_attacks": [
                "sql_injection",
                "xss_attack",
                "port_scan",
                "dos_attack",
                "brute_force",
                "malware_communication",
                "data_exfiltration"
            ]
        },
        "anomaly_detector": {
            "is_trained": true,
            "training_samples": 1500,
            "last_training": "2024-01-15T09:00:00Z",
            "model_type": "IsolationForest",
            "contamination": 0.1
        },
        "model_stats": {
            "total_detections": 1250,
            "false_positive_rate": 0.05,
            "last_updated": "2024-01-15T10:30:00Z"
        }
    }
    """
    try:
        model_stats = analyzer.get_model_stats()
        
        response = {
            'signature_detector': {
                'signature_count': model_stats.get('signature_count', 0),
                'supported_attacks': [
                    'sql_injection',
                    'xss_attack',
                    'port_scan',
                    'dos_attack',
                    'brute_force',
                    'malware_communication',
                    'data_exfiltration'
                ]
            },
            'anomaly_detector': {
                'is_trained': model_stats.get('is_trained', False),
                'training_samples': model_stats.get('training_samples', 0),
                'last_training': model_stats.get('last_training', ''),
                'model_type': 'IsolationForest',
                'contamination': 0.1
            },
            'model_stats': {
                'total_detections': model_stats.get('total_detections', 0),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def _analyze_flow_anomalies(flow_data):
    """
    Analyze flow data for anomalies
    
    Args:
        flow_data: Flow data dictionary
        
    Returns:
        List of detected anomalies
    """
    anomalies = []
    
    try:
        packet_count = flow_data.get('packet_count', 0)
        byte_count = flow_data.get('byte_count', 0)
        duration = flow_data.get('duration', 1)
        
        # High volume anomaly
        if packet_count > 1000:  # Threshold for high packet count
            anomalies.append({
                'type': 'high_volume',
                'description': f'Unusually high packet count: {packet_count} packets',
                'severity': 'medium' if packet_count < 5000 else 'high',
                'confidence': min(0.9, packet_count / 10000),
                'matched_pattern': 'high_packet_count',
                'source': 'flow_analysis'
            })
        
        # High byte rate anomaly
        byte_rate = byte_count / duration
        if byte_rate > 1000000:  # 1MB/s threshold
            anomalies.append({
                'type': 'high_bandwidth',
                'description': f'Unusually high byte rate: {byte_rate:.2f} bytes/s',
                'severity': 'medium' if byte_rate < 5000000 else 'high',
                'confidence': min(0.9, byte_rate / 10000000),
                'matched_pattern': 'high_byte_rate',
                'source': 'flow_analysis'
            })
        
        # Suspicious protocol patterns
        protocol = flow_data.get('protocol', '').upper()
        dst_port = flow_data.get('dst_port', 0)
        
        if protocol == 'TCP' and dst_port in [21, 22, 23, 25, 53, 80, 443, 993, 995]:
            # Common ports - check for unusual patterns
            if packet_count > 100 and duration < 10:  # Many packets in short time
                anomalies.append({
                    'type': 'rapid_connections',
                    'description': f'Rapid connections to port {dst_port}',
                    'severity': 'medium',
                    'confidence': 0.7,
                    'matched_pattern': 'rapid_port_access',
                    'source': 'flow_analysis'
                })
        
        return anomalies
        
    except Exception as e:
        logger.error(f"Error analyzing flow anomalies: {e}")
        return []
