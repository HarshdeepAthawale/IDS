"""
Traffic statistics API routes for Flask IDS Backend
Provides endpoints for retrieving traffic metrics and protocol statistics
"""

import logging
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify, current_app
from models.db_models import traffic_stats_collection, traffic_stat_to_dict
from services.logger import DatabaseLogger, normalize_protocol

logger = logging.getLogger(__name__)

# Create blueprint
stats_bp = Blueprint('stats', __name__)

# Initialize logger (will be injected from main app)
logger_service = None

def init_logger(logger_instance):
    """Initialize logger service"""
    global logger_service
    logger_service = logger_instance

@stats_bp.route('/api/stats/traffic', methods=['GET'])
def get_traffic_stats():
    """
    Get current traffic statistics
    
    Query Parameters:
    - hours: Number of hours to look back (default: 24, max: 168)
    - limit: Number of data points to return (default: 24)
    
    Returns:
    JSON response with traffic statistics
    
    Example Response:
    {
        "current_stats": {
            "total_packets": 1250000,
            "total_bytes": 524288000,
            "active_connections": 45,
            "protocol_distribution": {
                "TCP": 850000,
                "UDP": 320000,
                "ICMP": 80000
            },
            "anomaly_count": 12,
            "packet_rate": 145.8,
            "byte_rate": 61440.0,
            "timestamp": "2024-01-15T10:30:00Z",
            "top_source_ips": [
                {"ip": "192.168.1.100", "count": 15000},
                {"ip": "10.0.0.5", "count": 12000}
            ],
            "top_dest_ports": [
                {"port": "80", "count": 25000},
                {"port": "443", "count": 18000}
            ],
            "avg_packet_size": 419.43,
            "connection_success_rate": 0.95
        },
        "historical_data": [
            {
                "timestamp": "2024-01-15T10:00:00Z",
                "total_packets": 1200000,
                "active_connections": 42,
                "packet_rate": 133.3
            }
        ],
        "summary": {
            "avg_packet_rate": 142.5,
            "peak_packet_rate": 185.2,
            "total_anomalies": 28,
            "most_active_protocol": "TCP"
        }
    }
    """
    try:
        # Parse query parameters
        hours = min(int(request.args.get('hours', 24)), 168)  # Max 1 week
        limit = min(int(request.args.get('limit', 24)), 168)  # Max 168 data points
        
        # Get current traffic stats (most recent)
        current_stats = traffic_stats_collection.find_one(
            sort=[('timestamp', -1)]
        )
        
        # Get historical data
        cutoff_time = datetime.now() - timedelta(hours=hours)
        historical_data = list(traffic_stats_collection.find(
            {'timestamp': {'$gte': cutoff_time}}
        ).sort('timestamp', -1).limit(limit))
        
        # Calculate summary statistics
        summary = _calculate_traffic_summary(historical_data)
        
        response = {
            'current_stats': traffic_stat_to_dict(current_stats) if current_stats else None,
            'historical_data': [traffic_stat_to_dict(stat) for stat in historical_data],
            'summary': summary,
            'time_range': {
                'hours': hours,
                'start_time': cutoff_time.isoformat(),
                'end_time': datetime.now().isoformat()
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting traffic stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@stats_bp.route('/api/stats/protocols', methods=['GET'])
def get_protocol_stats():
    """
    Get protocol distribution statistics
    
    Query Parameters:
    - hours: Number of hours to analyze (default: 24)
    - limit: Number of top protocols to return (default: 10)
    
    Returns:
    JSON response with protocol statistics
    
    Example Response:
    {
        "protocol_distribution": {
            "TCP": {
                "total_packets": 850000,
                "percentage": 68.0,
                "avg_packet_size": 512.5,
                "total_bytes": 435200000
            },
            "UDP": {
                "total_packets": 320000,
                "percentage": 25.6,
                "avg_packet_size": 128.3,
                "total_bytes": 41056000
            }
        },
        "top_protocols": [
            {
                "protocol": "TCP",
                "packet_count": 850000,
                "percentage": 68.0,
                "avg_packet_size": 512.5
            }
        ],
        "summary": {
            "total_protocols": 5,
            "most_common_protocol": "TCP",
            "most_common_percentage": 68.0
        }
    }
    """
    try:
        # Parse query parameters
        hours = min(int(request.args.get('hours', 24)), 168)
        limit = min(int(request.args.get('limit', 10)), 50)
        
        # Get protocol statistics from recent traffic data
        cutoff_time = datetime.now() - timedelta(hours=hours)
        traffic_stats = list(traffic_stats_collection.find(
            {'timestamp': {'$gte': cutoff_time}}
        ))
        
        # Aggregate protocol data
        protocol_data = {}
        total_packets = 0
        
        for stat in traffic_stats:
            protocol_dist = stat.get('protocol_distribution', {}) if isinstance(stat, dict) else (stat.protocol_distribution if hasattr(stat, 'protocol_distribution') else {}) or {}
            
            # Skip if protocol_distribution is empty or not a dict
            if not isinstance(protocol_dist, dict) or not protocol_dist:
                continue
            
            # Get average packet size from this traffic_stats document to estimate bytes per protocol
            stat_avg_packet_size = stat.get('avg_packet_size', 0)
            if not stat_avg_packet_size or stat_avg_packet_size == 0:
                # Calculate from total_bytes and total_packets if avg_packet_size not available
                stat_total_bytes = stat.get('total_bytes', 0)
                stat_total_packets = stat.get('total_packets', 1)
                stat_avg_packet_size = stat_total_bytes / stat_total_packets if stat_total_packets > 0 else 0
            
            for protocol, count in protocol_dist.items():
                # Normalize protocol name
                normalized_protocol = normalize_protocol(protocol)
                
                # Skip invalid protocols
                if not normalized_protocol or normalized_protocol == 'Other':
                    continue
                
                # Handle non-numeric count values
                if not isinstance(count, (int, float)):
                    try:
                        count = int(count)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid protocol count for {normalized_protocol}: {count}")
                        continue
                
                # Use normalized protocol name for aggregation
                if normalized_protocol not in protocol_data:
                    protocol_data[normalized_protocol] = {
                        'total_packets': 0,
                        'total_bytes': 0,
                        'count': 0
                    }
                
                protocol_data[normalized_protocol]['total_packets'] += count
                protocol_data[normalized_protocol]['count'] += 1
                
                # Estimate bytes per protocol using overall avg_packet_size from the document
                estimated_bytes = count * stat_avg_packet_size
                protocol_data[normalized_protocol]['total_bytes'] += estimated_bytes
                
                total_packets += count
        
        # Calculate percentages and averages
        protocol_distribution = {}
        top_protocols = []
        
        for protocol, data in protocol_data.items():
            percentage = (data['total_packets'] / total_packets * 100) if total_packets > 0 else 0
            avg_packet_size = (data['total_bytes'] / data['total_packets']) if data['total_packets'] > 0 else 0
            
            protocol_distribution[protocol] = {
                'total_packets': data['total_packets'],
                'percentage': round(percentage, 2),
                'avg_packet_size': round(avg_packet_size, 2),
                'total_bytes': data['total_bytes']
            }
            
            top_protocols.append({
                'protocol': protocol,
                'packet_count': data['total_packets'],
                'percentage': round(percentage, 2),
                'avg_packet_size': round(avg_packet_size, 2)
            })
        
        # Sort by packet count
        top_protocols.sort(key=lambda x: x['packet_count'], reverse=True)
        top_protocols = top_protocols[:limit]
        
        # Summary
        summary = {
            'total_protocols': len(protocol_data),
            'most_common_protocol': top_protocols[0]['protocol'] if top_protocols else None,
            'most_common_percentage': top_protocols[0]['percentage'] if top_protocols else 0
        }
        
        response = {
            'protocol_distribution': protocol_distribution,
            'top_protocols': top_protocols,
            'summary': summary,
            'time_range': {
                'hours': hours,
                'total_packets': total_packets
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting protocol stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@stats_bp.route('/api/stats/connections', methods=['GET'])
def get_connection_stats():
    """
    Get connection statistics and top talkers
    
    Query Parameters:
    - hours: Number of hours to analyze (default: 24)
    - limit: Number of top connections to return (default: 20)
    
    Returns:
    JSON response with connection statistics
    
    Example Response:
    {
        "connection_stats": {
            "total_connections": 1250,
            "avg_connections_per_hour": 52.1,
            "peak_connections": 89,
            "current_connections": 45
        },
        "top_source_ips": [
            {
                "ip": "192.168.1.100",
                "packet_count": 15000,
                "connection_count": 45,
                "percentage": 12.0
            }
        ],
        "top_dest_ports": [
            {
                "port": "80",
                "packet_count": 25000,
                "connection_count": 120,
                "percentage": 20.0
            }
        ],
        "connection_trend": [
            {
                "timestamp": "2024-01-15T10:00:00Z",
                "active_connections": 42
            }
        ]
    }
    """
    try:
        # Parse query parameters
        hours = min(int(request.args.get('hours', 24)), 168)
        limit = min(int(request.args.get('limit', 20)), 100)
        
        # Get connection data from recent traffic stats
        cutoff_time = datetime.now() - timedelta(hours=hours)
        traffic_stats = list(traffic_stats_collection.find(
            {'timestamp': {'$gte': cutoff_time}}
        ).sort('timestamp', -1))
        
        # Aggregate connection data
        source_ips = {}
        dest_ports = {}
        total_connections = 0
        connection_trend = []
        
        for stat in traffic_stats:
            total_connections += stat.active_connections
            timestamp = stat.get('timestamp')
            if isinstance(timestamp, datetime):
                timestamp_str = timestamp.isoformat()
            else:
                timestamp_str = str(timestamp)
            
            connection_trend.append({
                'timestamp': timestamp_str,
                'active_connections': stat.get('active_connections', 0)
            })
            
            # Aggregate source IPs
            top_ips = stat.top_source_ips or []
            for ip_data in top_ips:
                ip = ip_data.get('ip', '')
                count = ip_data.get('count', 0)
                if ip:
                    if ip not in source_ips:
                        source_ips[ip] = {'packet_count': 0, 'connection_count': 0}
                    source_ips[ip]['packet_count'] += count
                    source_ips[ip]['connection_count'] += 1
            
            # Aggregate destination ports
            top_ports = stat.top_dest_ports or []
            for port_data in top_ports:
                port = port_data.get('port', '')
                count = port_data.get('count', 0)
                if port:
                    if port not in dest_ports:
                        dest_ports[port] = {'packet_count': 0, 'connection_count': 0}
                    dest_ports[port]['packet_count'] += count
                    dest_ports[port]['connection_count'] += 1
        
        # Calculate statistics
        avg_connections = total_connections / len(traffic_stats) if traffic_stats else 0
        peak_connections = max((stat.get('active_connections', 0) for stat in traffic_stats), default=0)
        current_connections = traffic_stats[0].get('active_connections', 0) if traffic_stats else 0
        
        # Top source IPs
        top_source_ips = []
        total_packets = sum(data['packet_count'] for data in source_ips.values())
        for ip, data in sorted(source_ips.items(), key=lambda x: x[1]['packet_count'], reverse=True)[:limit]:
            percentage = (data['packet_count'] / total_packets * 100) if total_packets > 0 else 0
            top_source_ips.append({
                'ip': ip,
                'packet_count': data['packet_count'],
                'connection_count': data['connection_count'],
                'percentage': round(percentage, 2)
            })
        
        # Top destination ports
        top_dest_ports = []
        for port, data in sorted(dest_ports.items(), key=lambda x: x[1]['packet_count'], reverse=True)[:limit]:
            percentage = (data['packet_count'] / total_packets * 100) if total_packets > 0 else 0
            top_dest_ports.append({
                'port': port,
                'packet_count': data['packet_count'],
                'connection_count': data['connection_count'],
                'percentage': round(percentage, 2)
            })
        
        response = {
            'connection_stats': {
                'total_connections': total_connections,
                'avg_connections_per_hour': round(avg_connections, 2),
                'peak_connections': peak_connections,
                'current_connections': current_connections
            },
            'top_source_ips': top_source_ips,
            'top_dest_ports': top_dest_ports,
            'connection_trend': connection_trend[-24:]  # Last 24 data points
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting connection stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@stats_bp.route('/api/stats/anomalies', methods=['GET'])
def get_anomaly_stats():
    """
    Get anomaly detection statistics
    
    Query Parameters:
    - hours: Number of hours to analyze (default: 24)
    - severity: Filter by severity level
    
    Returns:
    JSON response with anomaly statistics
    
    Example Response:
    {
        "anomaly_stats": {
            "total_anomalies": 28,
            "anomalies_per_hour": 1.17,
            "peak_anomalies": 8,
            "current_anomaly_rate": 0.5
        },
        "anomaly_trend": [
            {
                "timestamp": "2024-01-15T10:00:00Z",
                "anomaly_count": 5
            }
        ],
        "severity_distribution": {
            "high": 8,
            "medium": 15,
            "low": 5
        }
    }
    """
    try:
        # Parse query parameters
        hours = min(int(request.args.get('hours', 24)), 168)
        severity = request.args.get('severity')
        
        # Get anomaly data from traffic stats
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        traffic_stats = list(traffic_stats_collection.find(
            {'timestamp': {'$gte': cutoff_time}}
        ).sort('timestamp', -1))
        
        # Calculate anomaly statistics
        total_anomalies = sum(stat.anomaly_count for stat in traffic_stats)
        anomalies_per_hour = total_anomalies / hours if hours > 0 else 0
        peak_anomalies = max((stat.anomaly_count for stat in traffic_stats), default=0)
        current_anomaly_rate = traffic_stats[0].anomaly_count if traffic_stats else 0
        
        # Anomaly trend
        anomaly_trend = []
        for stat in traffic_stats:
            timestamp = stat.get('timestamp')
            if isinstance(timestamp, datetime):
                timestamp_str = timestamp.isoformat()
            else:
                timestamp_str = str(timestamp)
            
            anomaly_trend.append({
                'timestamp': timestamp_str,
                'anomaly_count': stat.get('anomaly_count', 0)
            })
        
        response = {
            'anomaly_stats': {
                'total_anomalies': total_anomalies,
                'anomalies_per_hour': round(anomalies_per_hour, 2),
                'peak_anomalies': peak_anomalies,
                'current_anomaly_rate': current_anomaly_rate
            },
            'anomaly_trend': anomaly_trend[-24:],  # Last 24 data points
            'time_range': {
                'hours': hours,
                'start_time': cutoff_time.isoformat(),
                'end_time': datetime.now().isoformat()
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting anomaly stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@stats_bp.route('/api/stats/realtime', methods=['GET'])
def get_realtime_stats():
    """
    Get real-time traffic statistics from in-memory cache
    
    Returns current stats that haven't been flushed to database yet.
    This provides instant, real-time data without database query overhead.
    
    Returns:
    JSON response with real-time traffic statistics
    
    Example Response:
    {
        "total_packets": 1250,
        "total_bytes": 524288,
        "active_connections": 5,
        "protocol_distribution": {
            "TCP": 850,
            "UDP": 320,
            "ICMP": 80
        },
        "top_source_ips": [
            {"ip": "192.168.1.100", "count": 150}
        ],
        "top_dest_ports": [
            {"port": "80", "count": 250}
        ],
        "packet_rate": 41.67,
        "byte_rate": 17476.27,
        "avg_packet_size": 419.43,
        "timestamp": "2024-01-15T10:30:00Z",
        "cache_age_seconds": 15.5
    }
    """
    try:
        if not logger_service:
            return jsonify({'error': 'Logger service not initialized'}), 500
        
        realtime_stats = logger_service.get_realtime_stats()
        
        if not realtime_stats:
            return jsonify({
                'total_packets': 0,
                'total_bytes': 0,
                'active_connections': 0,
                'protocol_distribution': {},
                'top_source_ips': [],
                'top_dest_ports': [],
                'packet_rate': 0,
                'byte_rate': 0,
                'avg_packet_size': 0,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'cache_age_seconds': 0,
                'message': 'No packet data captured yet. Waiting for network traffic...'
            })
        
        return jsonify(realtime_stats)
        
    except Exception as e:
        logger.error(f"Error getting real-time stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def _calculate_traffic_summary(traffic_stats):
    """
    Calculate summary statistics from traffic data
    
    Args:
        traffic_stats: List of traffic stat documents
        
    Returns:
        Dictionary with summary statistics
    """
    if not traffic_stats:
        return {}
    
    # Calculate averages
    total_packets = sum(stat.get('total_packets', 0) for stat in traffic_stats)
    total_connections = sum(stat.get('active_connections', 0) for stat in traffic_stats)
    total_anomalies = sum(stat.get('anomaly_count', 0) for stat in traffic_stats)
    
    packet_rates = [stat.get('packet_rate', 0) for stat in traffic_stats]
    avg_packet_rate = sum(packet_rates) / len(packet_rates) if packet_rates else 0
    peak_packet_rate = max(packet_rates) if packet_rates else 0
    
    # Find most active protocol
    protocol_counts = {}
    for stat in traffic_stats:
        protocol_dist = stat.get('protocol_distribution', {})
        if protocol_dist:
            for protocol, count in protocol_dist.items():
                protocol_counts[protocol] = protocol_counts.get(protocol, 0) + count
    
    most_active_protocol = max(protocol_counts.items(), key=lambda x: x[1])[0] if protocol_counts else None
    
    return {
        'avg_packet_rate': round(avg_packet_rate, 2),
        'peak_packet_rate': round(peak_packet_rate, 2),
        'total_anomalies': total_anomalies,
        'most_active_protocol': most_active_protocol,
        'avg_connections': round(total_connections / len(traffic_stats), 2) if traffic_stats else 0
    }

@stats_bp.route('/api/stats/debug/active-connections', methods=['GET'])
def get_active_connections_debug():
    """
    Debug endpoint to show detailed information about active connections
    
    Returns:
    JSON response with detailed active connection information showing
    source IP, destination IP, port, protocol, last seen time, and age
    
    Example Response:
    {
        "total_connections": 4,
        "connections": [
            {
                "id": 1,
                "source_ip": "192.168.1.100",
                "destination_ip": "8.8.8.8",
                "destination_port": 53,
                "protocol": "DNS",
                "last_seen": "2026-01-21T04:37:45.123456",
                "age_seconds": 15.5,
                "connection_string": "192.168.1.100 -> 8.8.8.8:53"
            }
        ],
        "sniffer_status": {
            "running": true,
            "total_packets": 1250,
            "interface": "any",
            "packet_rate": 41.67,
            "byte_rate": 17476.27
        },
        "timestamp": "2026-01-21T04:37:50.000000"
    }
    """
    try:
        # Get packet sniffer from app context
        if not hasattr(current_app, 'packet_sniffer') or not current_app.packet_sniffer:
            return jsonify({
                'error': 'Packet sniffer not available',
                'total_connections': 0,
                'connections': [],
                'sniffer_status': {'running': False}
            }), 500
        
        packet_sniffer = current_app.packet_sniffer
        
        # Get connections dictionary: {(src_ip, dst_ip, dst_port): timestamp}
        connections_dict = packet_sniffer.get_connections()
        
        # Get sniffer stats
        sniffer_stats = packet_sniffer.get_stats()
        
        # Format connections
        connections_list = []
        current_time = datetime.now(timezone.utc)
        
        for idx, ((src_ip, dst_ip, dst_port), last_seen) in enumerate(connections_dict.items(), 1):
            age_seconds = (current_time - last_seen).total_seconds()
            
            # Try to determine protocol from port
            protocol = "Unknown"
            if dst_port:
                if dst_port in [80, 443]:
                    protocol = "HTTP/HTTPS"
                elif dst_port == 53:
                    protocol = "DNS"
                elif dst_port == 22:
                    protocol = "SSH"
                elif dst_port in [20, 21]:
                    protocol = "FTP"
                elif dst_port == 25:
                    protocol = "SMTP"
                elif dst_port == 3306:
                    protocol = "MySQL"
                elif dst_port == 5432:
                    protocol = "PostgreSQL"
                elif dst_port == 3389:
                    protocol = "RDP"
                elif dst_port == 1433:
                    protocol = "MSSQL"
                elif dst_port in [587, 465]:
                    protocol = "SMTP (secure)"
                else:
                    protocol = f"Port {dst_port}"
            
            connections_list.append({
                'id': idx,
                'source_ip': src_ip if src_ip else 'Unknown',
                'destination_ip': dst_ip if dst_ip else 'Unknown',
                'destination_port': dst_port if dst_port else 'Unknown',
                'protocol': protocol,
                'last_seen': last_seen.isoformat() if isinstance(last_seen, datetime) else str(last_seen),
                'age_seconds': round(age_seconds, 2),
                'connection_string': f"{src_ip or 'Unknown'} -> {dst_ip or 'Unknown'}:{dst_port or 'Unknown'}"
            })
        
        # Sort by last_seen (most recent first)
        connections_list.sort(key=lambda x: x['last_seen'], reverse=True)
        
        response = {
            'total_connections': len(connections_list),
            'connections': connections_list,
            'sniffer_status': {
                'running': sniffer_stats.get('running', False),
                'total_packets': sniffer_stats.get('total_packets', 0),
                'interface': packet_sniffer.interface if hasattr(packet_sniffer, 'interface') else 'unknown',
                'packet_rate': round(sniffer_stats.get('packet_rate', 0), 2),
                'byte_rate': round(sniffer_stats.get('byte_rate', 0), 2)
            },
            'timestamp': current_time.isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting active connections debug info: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'error': str(e),
            'total_connections': 0,
            'connections': []
        }), 500
