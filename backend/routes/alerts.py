"""
Alerts API routes for Flask IDS Backend
Provides endpoints for retrieving and managing security alerts
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from models.db_models import Alert, db
from services.logger import DatabaseLogger

logger = logging.getLogger(__name__)

# Create blueprint
alerts_bp = Blueprint('alerts', __name__)

# Initialize logger (will be injected from main app)
logger_service = None

def init_logger(logger_instance):
    """Initialize logger service"""
    global logger_service
    logger_service = logger_instance

@alerts_bp.route('/api/alerts', methods=['GET'])
def get_alerts():
    """
    Get recent alerts with optional filtering
    
    Query Parameters:
    - type: Alert type (signature|anomaly)
    - severity: Severity level (low|medium|high|critical)
    - resolved: Whether alert is resolved (true|false)
    - source_ip: Source IP address
    - limit: Maximum number of alerts to return (default: 100)
    - start_date: Start date (ISO format)
    - end_date: End date (ISO format)
    
    Returns:
    JSON response with alerts list and metadata
    
    Example Response:
    {
        "alerts": [
            {
                "id": 1,
                "source_ip": "192.168.1.100",
                "dest_ip": "10.0.0.1",
                "protocol": "TCP",
                "port": 80,
                "type": "signature",
                "severity": "high",
                "description": "Potential SQL injection attempt detected",
                "confidence_score": 0.85,
                "signature_id": "sql_injection",
                "timestamp": "2024-01-15T10:30:00Z",
                "resolved": false,
                "resolved_at": null,
                "resolved_by": null,
                "payload_size": 1024,
                "flags": "SYN",
                "user_agent": "Mozilla/5.0...",
                "uri": "/api/users?id=1' OR 1=1--"
            }
        ],
        "total": 1,
        "page": 1,
        "per_page": 100,
        "summary": {
            "total_recent_alerts": 25,
            "unresolved_alerts": 12,
            "alerts_by_type": {
                "signature": 15,
                "anomaly": 10
            },
            "alerts_by_severity": {
                "high": 8,
                "medium": 12,
                "low": 5
            }
        }
    }
    """
    try:
        # Parse query parameters
        alert_type = request.args.get('type')
        severity = request.args.get('severity')
        resolved = request.args.get('resolved')
        source_ip = request.args.get('source_ip')
        limit = min(int(request.args.get('limit', 100)), 1000)  # Max 1000 alerts
        
        # Parse date filters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid start_date format. Use ISO format.'}), 400
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid end_date format. Use ISO format.'}), 400
        
        # Build filters
        filters = {}
        if alert_type:
            filters['type'] = alert_type
        if severity:
            filters['severity'] = severity
        if resolved is not None:
            filters['resolved'] = resolved.lower() == 'true'
        if source_ip:
            filters['source_ip'] = source_ip
        if start_date:
            filters['start_date'] = start_date
        if end_date:
            filters['end_date'] = end_date
        
        # Get alerts
        alerts = logger_service.get_recent_alerts(limit=limit, **filters)
        
        # Get summary statistics
        summary = logger_service.get_alert_summary()
        
        # Convert alerts to dictionaries
        alerts_data = [alert.to_dict() for alert in alerts]
        
        response = {
            'alerts': alerts_data,
            'total': len(alerts_data),
            'page': 1,
            'per_page': limit,
            'summary': summary
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@alerts_bp.route('/api/alerts/history', methods=['GET'])
def get_alert_history():
    """
    Get historical alerts by date range
    
    Query Parameters:
    - start_date: Start date (ISO format, required)
    - end_date: End date (ISO format, required)
    - type: Alert type filter
    - severity: Severity level filter
    - limit: Maximum number of alerts (default: 1000)
    
    Returns:
    JSON response with historical alerts
    
    Example Response:
    {
        "alerts": [...],
        "total": 150,
        "date_range": {
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-01-31T23:59:59Z"
        },
        "statistics": {
            "alerts_per_day": 4.8,
            "peak_day": "2024-01-15",
            "peak_alerts": 25
        }
    }
    """
    try:
        # Parse required date parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date are required'}), 400
        
        try:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use ISO format.'}), 400
        
        # Validate date range
        if start_date >= end_date:
            return jsonify({'error': 'start_date must be before end_date'}), 400
        
        if (end_date - start_date).days > 90:  # Max 90 days
            return jsonify({'error': 'Date range cannot exceed 90 days'}), 400
        
        # Parse optional filters
        alert_type = request.args.get('type')
        severity = request.args.get('severity')
        limit = min(int(request.args.get('limit', 1000)), 5000)  # Max 5000 for history
        
        # Build filters
        filters = {
            'start_date': start_date,
            'end_date': end_date
        }
        if alert_type:
            filters['type'] = alert_type
        if severity:
            filters['severity'] = severity
        
        # Get alerts
        alerts = logger_service.get_recent_alerts(limit=limit, **filters)
        
        # Calculate statistics
        alerts_data = [alert.to_dict() for alert in alerts]
        days_in_range = (end_date - start_date).days + 1
        alerts_per_day = len(alerts_data) / days_in_range if days_in_range > 0 else 0
        
        # Find peak day
        daily_counts = {}
        for alert in alerts:
            day = alert.timestamp.date().isoformat()
            daily_counts[day] = daily_counts.get(day, 0) + 1
        
        peak_day = max(daily_counts.items(), key=lambda x: x[1]) if daily_counts else (None, 0)
        
        response = {
            'alerts': alerts_data,
            'total': len(alerts_data),
            'date_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'statistics': {
                'alerts_per_day': round(alerts_per_day, 2),
                'peak_day': peak_day[0],
                'peak_alerts': peak_day[1]
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting alert history: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@alerts_bp.route('/api/alerts/<int:alert_id>', methods=['PATCH'])
def update_alert(alert_id):
    """
    Update alert (mark as resolved/unresolved)
    
    Path Parameters:
    - alert_id: Alert ID to update
    
    Request Body:
    {
        "resolved": true,
        "resolved_by": "admin_user"
    }
    
    Returns:
    JSON response with updated alert
    
    Example Response:
    {
        "alert": {
            "id": 1,
            "resolved": true,
            "resolved_at": "2024-01-15T11:00:00Z",
            "resolved_by": "admin_user",
            ...
        },
        "message": "Alert resolved successfully"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Get alert
        alert = Alert.query.get(alert_id)
        if not alert:
            return jsonify({'error': 'Alert not found'}), 404
        
        # Update fields
        if 'resolved' in data:
            alert.resolved = bool(data['resolved'])
            if alert.resolved:
                alert.resolved_at = datetime.utcnow()
                alert.resolved_by = data.get('resolved_by')
            else:
                alert.resolved_at = None
                alert.resolved_by = None
        
        db.session.commit()
        
        logger.info(f"Updated alert {alert_id}: resolved={alert.resolved}")
        
        return jsonify({
            'alert': alert.to_dict(),
            'message': f"Alert {'resolved' if alert.resolved else 'unresolved'} successfully"
        })
        
    except Exception as e:
        logger.error(f"Error updating alert: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@alerts_bp.route('/api/alerts/<int:alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    """
    Delete alert (admin only)
    
    Path Parameters:
    - alert_id: Alert ID to delete
    
    Returns:
    JSON response with deletion confirmation
    
    Example Response:
    {
        "message": "Alert deleted successfully",
        "alert_id": 1
    }
    """
    try:
        # Get alert
        alert = Alert.query.get(alert_id)
        if not alert:
            return jsonify({'error': 'Alert not found'}), 404
        
        # Delete alert
        db.session.delete(alert)
        db.session.commit()
        
        logger.info(f"Deleted alert {alert_id}")
        
        return jsonify({
            'message': 'Alert deleted successfully',
            'alert_id': alert_id
        })
        
    except Exception as e:
        logger.error(f"Error deleting alert: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@alerts_bp.route('/api/alerts/summary', methods=['GET'])
def get_alert_summary():
    """
    Get alert summary statistics
    
    Returns:
    JSON response with alert statistics
    
    Example Response:
    {
        "total_recent_alerts": 25,
        "unresolved_alerts": 12,
        "alerts_by_type": {
            "signature": 15,
            "anomaly": 10
        },
        "alerts_by_severity": {
            "high": 8,
            "medium": 12,
            "low": 5
        },
        "last_updated": "2024-01-15T10:30:00Z"
    }
    """
    try:
        summary = logger_service.get_alert_summary()
        return jsonify(summary)
        
    except Exception as e:
        logger.error(f"Error getting alert summary: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@alerts_bp.route('/api/alerts/bulk-resolve', methods=['POST'])
def bulk_resolve_alerts():
    """
    Bulk resolve multiple alerts
    
    Request Body:
    {
        "alert_ids": [1, 2, 3],
        "resolved": true,
        "resolved_by": "admin_user"
    }
    
    Returns:
    JSON response with bulk operation results
    
    Example Response:
    {
        "resolved_count": 2,
        "failed_count": 1,
        "failed_alerts": [3],
        "message": "Resolved 2 out of 3 alerts"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        alert_ids = data.get('alert_ids', [])
        resolved = data.get('resolved', True)
        resolved_by = data.get('resolved_by')
        
        if not alert_ids or not isinstance(alert_ids, list):
            return jsonify({'error': 'alert_ids must be a non-empty list'}), 400
        
        resolved_count = 0
        failed_alerts = []
        
        for alert_id in alert_ids:
            try:
                alert = Alert.query.get(alert_id)
                if alert:
                    alert.resolved = resolved
                    if resolved:
                        alert.resolved_at = datetime.utcnow()
                        alert.resolved_by = resolved_by
                    else:
                        alert.resolved_at = None
                        alert.resolved_by = None
                    resolved_count += 1
                else:
                    failed_alerts.append(alert_id)
            except Exception as e:
                logger.error(f"Error resolving alert {alert_id}: {e}")
                failed_alerts.append(alert_id)
        
        db.session.commit()
        
        logger.info(f"Bulk resolved {resolved_count} alerts")
        
        return jsonify({
            'resolved_count': resolved_count,
            'failed_count': len(failed_alerts),
            'failed_alerts': failed_alerts,
            'message': f"{'Resolved' if resolved else 'Unresolved'} {resolved_count} out of {len(alert_ids)} alerts"
        })
        
    except Exception as e:
        logger.error(f"Error in bulk resolve: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
