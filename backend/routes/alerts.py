"""
Alerts API routes for Flask IDS Backend
Provides endpoints for retrieving and managing security alerts
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from models.db_models import alerts_collection, alert_to_dict, to_object_id
from services.logger import DatabaseLogger
from utils.validators import (
    validate_alert_ids, validate_pagination_params, validate_iso_date,
    validate_severity, validate_alert_type, sanitize_string,
    validate_ip_address, create_validation_error
)

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
        # Parse and validate query parameters
        alert_type = request.args.get('type')
        if alert_type and not validate_alert_type(alert_type):
            return create_validation_error(f"Invalid alert type: {alert_type}. Must be 'signature', 'anomaly', or 'classification'")
        
        severity = request.args.get('severity')
        if severity and not validate_severity(severity):
            return create_validation_error(f"Invalid severity: {severity}. Must be 'low', 'medium', 'high', or 'critical'")
        
        resolved = request.args.get('resolved')
        source_ip = sanitize_string(request.args.get('source_ip'), max_length=45)  # Max IPv6 length
        if source_ip and not validate_ip_address(source_ip):
            return create_validation_error(f"Invalid source IP address: {source_ip}")
        # Validate pagination limit
        limit_param = request.args.get('limit', '100')
        valid_limit, limit_int, limit_error = validate_pagination_params(limit_param, max_limit=1000)
        if not valid_limit:
            return create_validation_error(limit_error or "Invalid limit parameter")
        limit = limit_int
        
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
        
        # Convert alerts to dictionaries (already dicts, but ensure _id is converted)
        alerts_data = [alert_to_dict(alert) for alert in alerts]
        
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
        
        # Parse and validate optional filters
        alert_type = request.args.get('type')
        if alert_type and not validate_alert_type(alert_type):
            return create_validation_error(f"Invalid alert type: {alert_type}")
        
        severity = request.args.get('severity')
        if severity and not validate_severity(severity):
            return create_validation_error(f"Invalid severity: {severity}")
        # Validate pagination limit
        limit_param = request.args.get('limit', '1000')
        valid_limit, limit_int, limit_error = validate_pagination_params(limit_param, max_limit=5000)
        if not valid_limit:
            return create_validation_error(limit_error or "Invalid limit parameter")
        limit = limit_int
        
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
        alerts_data = [alert_to_dict(alert) for alert in alerts]
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

@alerts_bp.route('/api/alerts/<alert_id>', methods=['PATCH'])
def update_alert(alert_id):
    """
    Update alert (mark as resolved/unresolved)
    
    Path Parameters:
    - alert_id: Alert ID to update (MongoDB ObjectId as string)
    
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
            "id": "507f1f77bcf86cd799439011",
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
        
        # Convert string ID to ObjectId
        obj_id = to_object_id(alert_id)
        if not obj_id:
            return jsonify({'error': 'Invalid alert ID format'}), 400
        
        # Get alert
        alert = alerts_collection.find_one({'_id': obj_id})
        if not alert:
            return jsonify({'error': 'Alert not found'}), 404
        
        # Build update document
        update_doc = {}
        if 'resolved' in data:
            resolved = bool(data['resolved'])
            update_doc['resolved'] = resolved
            if resolved:
                update_doc['resolved_at'] = datetime.utcnow()
                update_doc['resolved_by'] = data.get('resolved_by')
            else:
                update_doc['resolved_at'] = None
                update_doc['resolved_by'] = None
        
        # Update alert
        alerts_collection.update_one(
            {'_id': obj_id},
            {'$set': update_doc}
        )
        
        # Get updated alert
        updated_alert = alerts_collection.find_one({'_id': obj_id})
        
        logger.info(f"Updated alert {alert_id}: resolved={update_doc.get('resolved', False)}")
        
        return jsonify({
            'alert': alert_to_dict(updated_alert),
            'message': f"Alert {'resolved' if update_doc.get('resolved', False) else 'unresolved'} successfully"
        })
        
    except Exception as e:
        logger.error(f"Error updating alert: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@alerts_bp.route('/api/alerts/<alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    """
    Delete alert (admin only)
    
    Rate limited: 10 per minute per IP
    
    Path Parameters:
    - alert_id: Alert ID to delete (MongoDB ObjectId as string)
    
    Returns:
    JSON response with deletion confirmation
    
    Example Response:
    {
        "message": "Alert deleted successfully",
        "alert_id": "507f1f77bcf86cd799439011"
    }
    """
    try:
        # Convert string ID to ObjectId
        obj_id = to_object_id(alert_id)
        if not obj_id:
            return jsonify({'error': 'Invalid alert ID format'}), 400
        
        # Check if alert exists
        alert = alerts_collection.find_one({'_id': obj_id})
        if not alert:
            return jsonify({'error': 'Alert not found'}), 404
        
        # Delete alert
        alerts_collection.delete_one({'_id': obj_id})
        
        logger.info(f"Deleted alert {alert_id}")
        
        return jsonify({
            'message': 'Alert deleted successfully',
            'alert_id': alert_id
        })
        
    except Exception as e:
        logger.error(f"Error deleting alert: {e}")
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

@alerts_bp.route('/api/alerts/critical', methods=['GET'])
def get_critical_alerts():
    """
    Get count of critical severity alerts
    
    Returns:
    JSON response with critical alerts count
    
    Example Response:
    {
        "count": 5,
        "alerts": [
            {
                "id": "507f1f77bcf86cd799439011",
                "severity": "critical",
                "type": "malware_communication",
                "description": "Potential malware communication detected",
                "timestamp": "2024-01-15T10:30:00Z",
                "source_ip": "192.168.1.100",
                "dest_ip": "10.0.0.1"
            }
        ],
        "unresolved_count": 4
    }
    """
    try:
        # Get unresolved critical alerts
        filters = {
            'severity': 'critical',
            'resolved': False
        }
        
        # Get alerts from logger service
        alerts = logger_service.get_recent_alerts(limit=100, **filters)
        alerts_data = [alert_to_dict(alert) for alert in alerts]
        
        # Get total count including resolved
        all_critical = logger_service.get_recent_alerts(limit=1000, severity='critical')
        total_count = len(all_critical)
        
        response = {
            'count': total_count,
            'unresolved_count': len(alerts_data),
            'alerts': alerts_data[:10]  # Return first 10 for preview
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting critical alerts: {e}")
        return jsonify({'error': 'Internal server error', 'count': 0, 'unresolved_count': 0}), 500

@alerts_bp.route('/api/alerts/bulk-delete', methods=['POST'])
def bulk_delete_alerts():
    """
    Bulk delete multiple alerts
    
    Rate limited: 5 per minute per IP
    
    Request Body:
    {
        "alert_ids": ["507f1f77bcf86cd799439011", "507f1f77bcf86cd799439012"]
    }
    
    Returns:
    JSON response with bulk deletion results
    
    Example Response:
    {
        "deleted_count": 2,
        "failed_count": 0,
        "failed_alerts": [],
        "message": "Deleted 2 alerts successfully"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return create_validation_error('Request body is required')
        
        alert_ids_raw = data.get('alert_ids', [])
        valid_ids, alert_ids, ids_error = validate_alert_ids(alert_ids_raw)
        if not valid_ids:
            return create_validation_error(ids_error or 'Invalid alert_ids')
        
        deleted_count = 0
        failed_alerts = []
        
        for alert_id in alert_ids:
            try:
                obj_id = to_object_id(alert_id)
                if not obj_id:
                    failed_alerts.append(alert_id)
                    continue
                
                # Check if alert exists
                alert = alerts_collection.find_one({'_id': obj_id})
                if alert:
                    alerts_collection.delete_one({'_id': obj_id})
                    deleted_count += 1
                else:
                    failed_alerts.append(alert_id)
            except Exception as e:
                logger.error(f"Error deleting alert {alert_id}: {e}")
                failed_alerts.append(alert_id)
        
        logger.info(f"Bulk deleted {deleted_count} alerts")
        
        return jsonify({
            'deleted_count': deleted_count,
            'failed_count': len(failed_alerts),
            'failed_alerts': failed_alerts,
            'message': f"Deleted {deleted_count} out of {len(alert_ids)} alerts successfully"
        })
        
    except Exception as e:
        logger.error(f"Error in bulk delete: {e}")
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
                obj_id = to_object_id(alert_id)
                if not obj_id:
                    failed_alerts.append(alert_id)
                    continue
                
                alert = alerts_collection.find_one({'_id': obj_id})
                if alert:
                    update_doc = {'resolved': resolved}
                    if resolved:
                        update_doc['resolved_at'] = datetime.utcnow()
                        update_doc['resolved_by'] = resolved_by
                    else:
                        update_doc['resolved_at'] = None
                        update_doc['resolved_by'] = None
                    
                    alerts_collection.update_one(
                        {'_id': obj_id},
                        {'$set': update_doc}
                    )
                    resolved_count += 1
                else:
                    failed_alerts.append(alert_id)
            except Exception as e:
                logger.error(f"Error resolving alert {alert_id}: {e}")
                failed_alerts.append(alert_id)
        
        logger.info(f"Bulk resolved {resolved_count} alerts")
        
        return jsonify({
            'resolved_count': resolved_count,
            'failed_count': len(failed_alerts),
            'failed_alerts': failed_alerts,
            'message': f"{'Resolved' if resolved else 'Unresolved'} {resolved_count} out of {len(alert_ids)} alerts"
        })
        
    except Exception as e:
        logger.error(f"Error in bulk resolve: {e}")
        return jsonify({'error': 'Internal server error'}), 500
