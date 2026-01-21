"""
Insider threat detection API routes for Flask IDS Backend
Provides endpoints for monitoring suspicious user activities
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from models.db_models import user_activities_collection, user_activity_to_dict
from services.logger import DatabaseLogger

logger = logging.getLogger(__name__)

# Create blueprint
insider_bp = Blueprint('insider', __name__)

# Initialize logger (will be injected from main app)
logger_service = None

def init_logger(logger_instance):
    """Initialize logger service"""
    global logger_service
    logger_service = logger_instance

@insider_bp.route('/api/insider-threats', methods=['GET'])
def get_insider_threats():
    """
    Get suspicious user activities and insider threats
    
    Query Parameters:
    - severity: Filter by severity level (low|medium|high|critical)
    - user_id: Filter by specific user ID
    - activity_type: Filter by activity type
    - time_range: Time range in hours (default: 24, max: 168)
    - limit: Maximum number of activities to return (default: 100)
    - start_date: Start date (ISO format)
    - end_date: End date (ISO format)
    
    Returns:
    JSON response with insider threat activities
    
    Example Response:
    {
        "activities": [
            {
                "id": 1,
                "user_id": "user123",
                "username": "john.doe",
                "activity_type": "data_exfiltration",
                "severity": "high",
                "description": "Large file download detected outside business hours",
                "source_ip": "192.168.1.100",
                "destination": "/home/user123/sensitive_data.zip",
                "file_size": 52428800,
                "success": true,
                "timestamp": "2024-01-15T02:30:00Z",
                "session_id": "sess_abc123",
                "user_agent": "Mozilla/5.0...",
                "geolocation": "New York, US"
            }
        ],
        "total": 1,
        "summary": {
            "total_activities": 15,
            "high_severity_count": 3,
            "critical_severity_count": 1,
            "most_common_activity": "off_hours_access",
            "top_suspicious_users": [
                {"user_id": "user123", "activity_count": 8, "severity": "high"}
            ]
        },
        "risk_assessment": {
            "overall_risk": "medium",
            "risk_factors": [
                "Multiple off-hours access attempts",
                "Unusual file access patterns"
            ]
        }
    }
    """
    try:
        # Parse query parameters
        severity = request.args.get('severity')
        user_id = request.args.get('user_id')
        activity_type = request.args.get('activity_type')
        time_range = min(int(request.args.get('time_range', 24)), 168)  # Max 1 week
        limit = min(int(request.args.get('limit', 100)), 1000)
        
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
        
        # If no date range specified, use time_range
        if not start_date and not end_date:
            start_date = datetime.utcnow() - timedelta(hours=time_range)
            end_date = datetime.utcnow()
        
        # Build filters
        filters = {
            'start_date': start_date,
            'end_date': end_date
        }
        if severity:
            filters['severity'] = severity
        if user_id:
            filters['user_id'] = user_id
        if activity_type:
            filters['activity_type'] = activity_type
        
        # Get activities
        activities = logger_service.get_user_activities(limit=limit, **filters)
        
        # Calculate summary statistics
        summary = _calculate_insider_summary(activities, start_date, end_date)
        
        # Perform risk assessment
        risk_assessment = _assess_insider_risk(activities)
        
        # Convert activities to dictionaries
        activities_data = [user_activity_to_dict(activity) for activity in activities]
        
        response = {
            'activities': activities_data,
            'total': len(activities_data),
            'summary': summary,
            'risk_assessment': risk_assessment,
            'time_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'hours': (end_date - start_date).total_seconds() / 3600
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting insider threats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@insider_bp.route('/api/insider-threats/users/<user_id>', methods=['GET'])
def get_user_activities(user_id):
    """
    Get activities for a specific user
    
    Path Parameters:
    - user_id: User ID to get activities for
    
    Query Parameters:
    - days: Number of days to look back (default: 7, max: 30)
    - severity: Filter by severity level
    - limit: Maximum number of activities (default: 50)
    
    Returns:
    JSON response with user-specific activities
    
    Example Response:
    {
        "user_id": "user123",
        "username": "john.doe",
        "activities": [...],
        "total_activities": 25,
        "user_profile": {
            "first_activity": "2024-01-01T09:00:00Z",
            "last_activity": "2024-01-15T17:30:00Z",
            "total_sessions": 15,
            "risk_score": 0.7
        },
        "behavior_analysis": {
            "usual_hours": "09:00-17:00",
            "unusual_access_count": 5,
            "high_risk_activities": 3
        }
    }
    """
    try:
        # Parse query parameters
        days = min(int(request.args.get('days', 7)), 30)
        severity = request.args.get('severity')
        limit = min(int(request.args.get('limit', 50)), 500)
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Build filters
        filters = {
            'user_id': user_id,
            'start_date': start_date,
            'end_date': end_date
        }
        if severity:
            filters['severity'] = severity
        
        # Get user activities
        activities = logger_service.get_user_activities(limit=limit, **filters)
        
        # Get user profile information
        user_profile = _get_user_profile(user_id, activities)
        
        # Analyze user behavior
        behavior_analysis = _analyze_user_behavior(activities)
        
        # Convert activities to dictionaries
        activities_data = [user_activity_to_dict(activity) for activity in activities]
        
        response = {
            'user_id': user_id,
            'username': activities[0].get('username', 'unknown') if activities else 'unknown',
            'activities': activities_data,
            'total_activities': len(activities_data),
            'user_profile': user_profile,
            'behavior_analysis': behavior_analysis,
            'time_range': {
                'days': days,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting user activities: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@insider_bp.route('/api/insider-threats/summary', methods=['GET'])
def get_insider_summary():
    """
    Get insider threat summary statistics
    
    Query Parameters:
    - days: Number of days to analyze (default: 7, max: 30)
    
    Returns:
    JSON response with insider threat summary
    
    Example Response:
    {
        "summary_stats": {
            "total_activities": 45,
            "high_severity_activities": 8,
            "critical_severity_activities": 2,
            "unique_users": 12,
            "most_common_activity": "off_hours_access"
        },
        "activity_distribution": {
            "login": 15,
            "file_access": 12,
            "network_access": 8,
            "data_exfiltration": 3,
            "privilege_escalation": 2
        },
        "severity_distribution": {
            "low": 25,
            "medium": 12,
            "high": 6,
            "critical": 2
        },
        "top_risk_users": [
            {
                "user_id": "user123",
                "username": "john.doe",
                "activity_count": 8,
                "highest_severity": "high",
                "risk_score": 0.8
            }
        ],
        "trend_analysis": {
            "activities_trend": "increasing",
            "risk_level": "medium",
            "recommendations": [
                "Review user123 access patterns",
                "Implement additional monitoring for off-hours access"
            ]
        }
    }
    """
    try:
        # Parse query parameters
        days = min(int(request.args.get('days', 7)), 30)
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get all activities in time range
        activities = logger_service.get_user_activities(
            limit=10000,  # Large limit to get all activities
            start_date=start_date,
            end_date=end_date
        )
        
        # Calculate summary statistics
        summary_stats = _calculate_insider_summary(activities, start_date, end_date)
        
        # Calculate distributions
        activity_distribution = {}
        severity_distribution = {}
        user_activity_counts = {}
        
        for activity in activities:
            # Activity type distribution
            activity_type = activity.get('activity_type')
            activity_distribution[activity_type] = activity_distribution.get(activity_type, 0) + 1
            
            # Severity distribution
            severity = activity.get('severity')
            severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
            
            # User activity counts
            user_id = activity.get('user_id')
            if user_id not in user_activity_counts:
                user_activity_counts[user_id] = {
                    'count': 0,
                    'highest_severity': 'low',
                    'username': activity.get('username', 'unknown')
                }
            user_activity_counts[user_id]['count'] += 1
            
            # Update highest severity
            severity_order = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
            current_severity = user_activity_counts[user_id]['highest_severity']
            if severity_order.get(severity, 0) > severity_order.get(current_severity, 0):
                user_activity_counts[user_id]['highest_severity'] = severity
        
        # Calculate risk scores for users
        top_risk_users = []
        for user_id, data in user_activity_counts.items():
            risk_score = _calculate_user_risk_score(data['count'], data['highest_severity'])
            top_risk_users.append({
                'user_id': user_id,
                'username': data['username'],
                'activity_count': data['count'],
                'highest_severity': data['highest_severity'],
                'risk_score': risk_score
            })
        
        # Sort by risk score
        top_risk_users.sort(key=lambda x: x['risk_score'], reverse=True)
        top_risk_users = top_risk_users[:10]  # Top 10
        
        # Trend analysis
        trend_analysis = _analyze_insider_trends(activities, start_date, end_date)
        
        response = {
            'summary_stats': summary_stats,
            'activity_distribution': activity_distribution,
            'severity_distribution': severity_distribution,
            'top_risk_users': top_risk_users,
            'trend_analysis': trend_analysis,
            'time_range': {
                'days': days,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting insider summary: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@insider_bp.route('/api/insider-threats/log', methods=['POST'])
def log_user_activity():
    """
    Log user activity for insider threat monitoring
    
    Request Body:
    {
        "user_id": "user123",
        "username": "john.doe",
        "activity_type": "file_access",
        "severity": "medium",
        "description": "Accessed sensitive file outside business hours",
        "source_ip": "192.168.1.100",
        "destination": "/sensitive/data.txt",
        "file_size": 1024000,
        "success": true,
        "session_id": "sess_abc123",
        "user_agent": "Mozilla/5.0...",
        "geolocation": "New York, US"
    }
    
    Returns:
    JSON response with logged activity
    
    Example Response:
    {
        "activity": {
            "id": 1,
            "user_id": "user123",
            "username": "john.doe",
            "activity_type": "file_access",
            "severity": "medium",
            "description": "Accessed sensitive file outside business hours",
            "timestamp": "2024-01-15T10:30:00Z",
            ...
        },
        "message": "User activity logged successfully"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Validate required fields
        required_fields = ['user_id', 'username', 'activity_type', 'severity', 'description']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Validate activity type
        valid_activity_types = [
            'login', 'file_access', 'network_access', 'privilege_escalation',
            'data_exfiltration', 'suspicious_command', 'off_hours_access'
        ]
        if data.get('activity_type') not in valid_activity_types:
            return jsonify({
                'error': f'Invalid activity_type. Must be one of: {", ".join(valid_activity_types)}'
            }), 400
        
        # Validate severity
        valid_severities = ['low', 'medium', 'high', 'critical']
        if data.get('severity') not in valid_severities:
            return jsonify({
                'error': f'Invalid severity. Must be one of: {", ".join(valid_severities)}'
            }), 400
        
        # Log activity
        activity = logger_service.log_user_activity(
            user_id=data['user_id'],
            username=data['username'],
            activity_type=data['activity_type'],
            severity=data['severity'],
            description=data['description'],
            source_ip=data.get('source_ip'),
            destination=data.get('destination'),
            command=data.get('command'),
            file_size=data.get('file_size'),
            success=data.get('success'),
            session_id=data.get('session_id'),
            user_agent=data.get('user_agent'),
            geolocation=data.get('geolocation')
        )
        
        if not activity:
            return jsonify({'error': 'Failed to log user activity'}), 500
        
        logger.info(f"Logged user activity: {data['user_id']} - {data['activity_type']} - {data['severity']}")
        
        return jsonify({
            'activity': user_activity_to_dict(activity),
            'message': 'User activity logged successfully'
        })
        
    except Exception as e:
        logger.error(f"Error logging user activity: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def _calculate_insider_summary(activities, start_date, end_date):
    """Calculate summary statistics for insider activities"""
    if not activities:
        return {
            'total_activities': 0,
            'high_severity_count': 0,
            'critical_severity_count': 0,
            'most_common_activity': None,
            'top_suspicious_users': []
        }
    
    total_activities = len(activities)
    high_severity_count = sum(1 for a in activities if a.get('severity') == 'high')
    critical_severity_count = sum(1 for a in activities if a.get('severity') == 'critical')
    
    # Most common activity
    activity_counts = {}
    for activity in activities:
        activity_type = activity.get('activity_type')
        activity_counts[activity_type] = activity_counts.get(activity_type, 0) + 1
    most_common_activity = max(activity_counts.items(), key=lambda x: x[1])[0] if activity_counts else None
    
    # Top suspicious users
    user_counts = {}
    for activity in activities:
        user_id = activity.get('user_id')
        if user_id not in user_counts:
            user_counts[user_id] = {'count': 0, 'severity': 'low'}
        user_counts[user_id]['count'] += 1
        
        # Update highest severity
        severity_order = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        activity_severity = activity.get('severity', 'low')
        if severity_order.get(activity_severity, 0) > severity_order.get(user_counts[user_id]['severity'], 0):
            user_counts[user_id]['severity'] = activity_severity
    
    top_suspicious_users = [
        {
            'user_id': user_id,
            'activity_count': data['count'],
            'severity': data['severity']
        }
        for user_id, data in sorted(user_counts.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
    ]
    
    return {
        'total_activities': total_activities,
        'high_severity_count': high_severity_count,
        'critical_severity_count': critical_severity_count,
        'most_common_activity': most_common_activity,
        'top_suspicious_users': top_suspicious_users
    }

def _assess_insider_risk(activities):
    """Assess overall insider risk based on activities"""
    if not activities:
        return {
            'overall_risk': 'low',
            'risk_factors': [],
            'risk_score': 0.0
        }
    
    risk_factors = []
    risk_score = 0.0
    
    # Count high-risk activities
    high_severity_count = sum(1 for a in activities if a.get('severity') in ['high', 'critical'])
    if high_severity_count > 0:
        risk_score += high_severity_count * 0.3
        risk_factors.append(f"{high_severity_count} high/critical severity activities")
    
    # Check for data exfiltration
    exfiltration_count = sum(1 for a in activities if a.get('activity_type') == 'data_exfiltration')
    if exfiltration_count > 0:
        risk_score += exfiltration_count * 0.4
        risk_factors.append(f"{exfiltration_count} data exfiltration attempts")
    
    # Check for off-hours access
    off_hours_count = sum(1 for a in activities if a.get('activity_type') == 'off_hours_access')
    if off_hours_count > 2:
        risk_score += (off_hours_count - 2) * 0.1
        risk_factors.append(f"{off_hours_count} off-hours access attempts")
    
    # Check for privilege escalation
    privilege_count = sum(1 for a in activities if a.get('activity_type') == 'privilege_escalation')
    if privilege_count > 0:
        risk_score += privilege_count * 0.5
        risk_factors.append(f"{privilege_count} privilege escalation attempts")
    
    # Determine overall risk level
    if risk_score >= 0.8:
        overall_risk = 'critical'
    elif risk_score >= 0.6:
        overall_risk = 'high'
    elif risk_score >= 0.3:
        overall_risk = 'medium'
    else:
        overall_risk = 'low'
    
    return {
        'overall_risk': overall_risk,
        'risk_factors': risk_factors,
        'risk_score': min(1.0, risk_score)
    }

def _get_user_profile(user_id, activities):
    """Get user profile information"""
    if not activities:
        return {
            'first_activity': None,
            'last_activity': None,
            'total_sessions': 0,
            'risk_score': 0.0
        }
    
    timestamps = [a.get('timestamp') for a in activities if a.get('timestamp')]
    if not timestamps:
        return {
            'first_activity': None,
            'last_activity': None,
            'total_sessions': 0,
            'risk_score': 0.0
        }
    
    first_activity = min(timestamps)
    last_activity = max(timestamps)
    
    # Count unique sessions
    sessions = set(a.get('session_id') for a in activities if a.get('session_id'))
    total_sessions = len(sessions)
    
    # Calculate risk score
    first_severity = activities[0].get('severity', 'low') if activities else 'low'
    risk_score = _calculate_user_risk_score(len(activities), first_severity)
    
    return {
        'first_activity': first_activity.isoformat(),
        'last_activity': last_activity.isoformat(),
        'total_sessions': total_sessions,
        'risk_score': risk_score
    }

def _analyze_user_behavior(activities):
    """Analyze user behavior patterns"""
    if not activities:
        return {
            'usual_hours': None,
            'unusual_access_count': 0,
            'high_risk_activities': 0
        }
    
    # Analyze activity hours
    hours = []
    for a in activities:
        timestamp = a.get('timestamp')
        if timestamp and isinstance(timestamp, datetime):
            hours.append(timestamp.hour)
    
    if hours:
        usual_start = min(hours)
        usual_end = max(hours)
        usual_hours = f"{usual_start:02d}:00-{usual_end:02d}:00"
    else:
        usual_hours = None
    
    # Count unusual access (outside 9-17)
    unusual_access_count = 0
    for a in activities:
        timestamp = a.get('timestamp')
        if timestamp and isinstance(timestamp, datetime):
            if timestamp.hour < 9 or timestamp.hour > 17:
                unusual_access_count += 1
    
    # Count high-risk activities
    high_risk_activities = sum(1 for a in activities if a.get('severity') in ['high', 'critical'])
    
    return {
        'usual_hours': usual_hours,
        'unusual_access_count': unusual_access_count,
        'high_risk_activities': high_risk_activities
    }

def _calculate_user_risk_score(activity_count, highest_severity):
    """Calculate risk score for a user"""
    severity_scores = {'low': 0.1, 'medium': 0.3, 'high': 0.6, 'critical': 0.9}
    base_score = severity_scores.get(highest_severity, 0.1)
    
    # Adjust based on activity count
    if activity_count > 20:
        base_score += 0.2
    elif activity_count > 10:
        base_score += 0.1
    
    return min(1.0, base_score)

def _analyze_insider_trends(activities, start_date, end_date):
    """Analyze trends in insider activities"""
    if len(activities) < 2:
        return {
            'activities_trend': 'stable',
            'risk_level': 'low',
            'recommendations': []
        }
    
    # Simple trend analysis based on activity count
    total_days = (end_date - start_date).days
    if total_days > 0:
        daily_activity_rate = len(activities) / total_days
        
        if daily_activity_rate > 5:
            activities_trend = 'increasing'
            risk_level = 'high'
        elif daily_activity_rate > 2:
            activities_trend = 'stable'
            risk_level = 'medium'
        else:
            activities_trend = 'decreasing'
            risk_level = 'low'
    else:
        activities_trend = 'stable'
        risk_level = 'medium'
    
    # Generate recommendations
    recommendations = []
    if risk_level == 'high':
        recommendations.extend([
            'Implement additional monitoring for high-risk users',
            'Review access patterns and permissions',
            'Consider implementing behavioral analytics'
        ])
    elif risk_level == 'medium':
        recommendations.extend([
            'Monitor unusual access patterns',
            'Review user permissions regularly'
        ])
    
    return {
        'activities_trend': activities_trend,
        'risk_level': risk_level,
        'recommendations': recommendations
    }
