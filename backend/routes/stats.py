"""
Traffic statistics API routes for Flask IDS Backend
Provides endpoints for retrieving traffic metrics and protocol statistics
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from models.db_models import TrafficStat, db
from services.logger import DatabaseLogger
from sqlalchemy import func, desc

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
        current_stats = TrafficStat.query.order_by(desc(TrafficStat.timestamp)).first()
        
        # Get historical data
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        historical_data = TrafficStat.query.filter(
            TrafficStat.timestamp >= cutoff_time
        ).order_by(desc(TrafficStat.timestamp)).limit(limit).all()
        
        # Calculate summary statistics
        summary = _calculate_traffic_summary(historical_data)
        
        response = {
            'current_stats': current_stats.to_dict() if current_stats else None,
            'historical_data': [stat.to_dict() for stat in historical_data],
            'summary': summary,
            'time_range': {
                'hours': hours,
                'start_time': cutoff_time.isoformat(),
                'end_time': datetime.utcnow().isoformat()
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
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        traffic_stats = TrafficStat.query.filter(
            TrafficStat.timestamp >= cutoff_time
        ).all()
        
        # Aggregate protocol data
        protocol_data = {}
        total_packets = 0
        
        for stat in traffic_stats:
            protocol_dist = stat.protocol_distribution or {}
            for protocol, count in protocol_dist.items():
                if protocol not in protocol_data:
                    protocol_data[protocol] = {
                        'total_packets': 0,
                        'total_bytes': 0,
                        'count': 0
                    }
                protocol_data[protocol]['total_packets'] += count
                protocol_data[protocol]['count'] += 1
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
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        traffic_stats = TrafficStat.query.filter(
            TrafficStat.timestamp >= cutoff_time
        ).order_by(desc(TrafficStat.timestamp)).all()
        
        # Aggregate connection data
        source_ips = {}
        dest_ports = {}
        total_connections = 0
        connection_trend = []
        
        for stat in traffic_stats:
            total_connections += stat.active_connections
            connection_trend.append({
                'timestamp': stat.timestamp.isoformat(),
                'active_connections': stat.active_connections
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
        peak_connections = max((stat.active_connections for stat in traffic_stats), default=0)
        current_connections = traffic_stats[0].active_connections if traffic_stats else 0
        
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
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        traffic_stats = TrafficStat.query.filter(
            TrafficStat.timestamp >= cutoff_time
        ).order_by(desc(TrafficStat.timestamp)).all()
        
        # Calculate anomaly statistics
        total_anomalies = sum(stat.anomaly_count for stat in traffic_stats)
        anomalies_per_hour = total_anomalies / hours if hours > 0 else 0
        peak_anomalies = max((stat.anomaly_count for stat in traffic_stats), default=0)
        current_anomaly_rate = traffic_stats[0].anomaly_count if traffic_stats else 0
        
        # Anomaly trend
        anomaly_trend = [
            {
                'timestamp': stat.timestamp.isoformat(),
                'anomaly_count': stat.anomaly_count
            }
            for stat in traffic_stats
        ]
        
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
                'end_time': datetime.utcnow().isoformat()
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting anomaly stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def _calculate_traffic_summary(traffic_stats):
    """
    Calculate summary statistics from traffic data
    
    Args:
        traffic_stats: List of TrafficStat objects
        
    Returns:
        Dictionary with summary statistics
    """
    if not traffic_stats:
        return {}
    
    # Calculate averages
    total_packets = sum(stat.total_packets for stat in traffic_stats)
    total_connections = sum(stat.active_connections for stat in traffic_stats)
    total_anomalies = sum(stat.anomaly_count for stat in traffic_stats)
    
    avg_packet_rate = sum(stat.packet_rate for stat in traffic_stats) / len(traffic_stats)
    peak_packet_rate = max(stat.packet_rate for stat in traffic_stats)
    
    # Find most active protocol
    protocol_counts = {}
    for stat in traffic_stats:
        if stat.protocol_distribution:
            for protocol, count in stat.protocol_distribution.items():
                protocol_counts[protocol] = protocol_counts.get(protocol, 0) + count
    
    most_active_protocol = max(protocol_counts.items(), key=lambda x: x[1])[0] if protocol_counts else None
    
    return {
        'avg_packet_rate': round(avg_packet_rate, 2),
        'peak_packet_rate': round(peak_packet_rate, 2),
        'total_anomalies': total_anomalies,
        'most_active_protocol': most_active_protocol,
        'avg_connections': round(total_connections / len(traffic_stats), 2) if traffic_stats else 0
    }
