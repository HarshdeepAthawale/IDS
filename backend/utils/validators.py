"""
Input validation utilities for API endpoints
"""

import re
import ipaddress
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from flask import jsonify

def validate_ip_address(ip: str) -> bool:
    """Validate IPv4 or IPv6 address"""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def validate_port(port: Any) -> bool:
    """Validate port number (1-65535)"""
    try:
        port_num = int(port)
        return 1 <= port_num <= 65535
    except (ValueError, TypeError):
        return False

def validate_iso_date(date_string: str) -> Optional[datetime]:
    """Validate and parse ISO date string"""
    try:
        # Handle both with and without 'Z' suffix
        date_string = date_string.replace('Z', '+00:00')
        return datetime.fromisoformat(date_string)
    except (ValueError, AttributeError):
        return None

def validate_severity(severity: str) -> bool:
    """Validate severity level"""
    return severity.lower() in ['low', 'medium', 'high', 'critical']

def validate_alert_type(alert_type: str) -> bool:
    """Validate alert type"""
    return alert_type.lower() in ['signature', 'anomaly', 'classification']

def sanitize_string(value: Any, max_length: int = 1000) -> Optional[str]:
    """Sanitize string input"""
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    # Remove null bytes and limit length
    value = value.replace('\x00', '').strip()
    if len(value) > max_length:
        value = value[:max_length]
    return value

def validate_pagination_params(limit: Any, max_limit: int = 1000) -> Tuple[bool, int, Optional[str]]:
    """Validate pagination limit parameter"""
    try:
        limit_int = int(limit)
        if limit_int < 1:
            return False, 0, "Limit must be greater than 0"
        if limit_int > max_limit:
            return False, 0, f"Limit cannot exceed {max_limit}"
        return True, limit_int, None
    except (ValueError, TypeError):
        return False, 0, "Limit must be a valid integer"

def validate_alert_ids(alert_ids: Any) -> Tuple[bool, Optional[List[str]], Optional[str]]:
    """Validate list of alert IDs"""
    if not isinstance(alert_ids, list):
        return False, None, "alert_ids must be a list"
    if len(alert_ids) == 0:
        return False, None, "alert_ids cannot be empty"
    if len(alert_ids) > 100:
        return False, None, "Cannot process more than 100 alerts at once"
    
    # Validate each ID is a string
    sanitized_ids = []
    for alert_id in alert_ids:
        if not isinstance(alert_id, (str, int)):
            return False, None, f"Invalid alert ID type: {type(alert_id)}"
        sanitized_ids.append(str(alert_id))
    
    return True, sanitized_ids, None

def validate_packet_data(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate packet data structure"""
    if not isinstance(data, dict):
        return False, "packet_data must be a dictionary"
    
    # Validate required fields
    required_fields = ['src_ip', 'dst_ip', 'protocol']
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    # Validate IP addresses
    if not validate_ip_address(str(data.get('src_ip', ''))):
        return False, "Invalid source IP address"
    
    if not validate_ip_address(str(data.get('dst_ip', ''))):
        return False, "Invalid destination IP address"
    
    # Validate protocol
    protocol = str(data.get('protocol', '')).upper()
    if protocol not in ['TCP', 'UDP', 'ICMP', 'HTTP', 'HTTPS']:
        return False, "Invalid protocol. Must be TCP, UDP, ICMP, HTTP, or HTTPS"
    
    # Validate ports if present
    if 'src_port' in data and data['src_port'] is not None:
        if not validate_port(data['src_port']):
            return False, "Invalid source port"
    
    if 'dst_port' in data and data['dst_port'] is not None:
        if not validate_port(data['dst_port']):
            return False, "Invalid destination port"
    
    return True, None

def validate_query_params(params: Dict[str, Any], allowed_params: List[str]) -> Dict[str, Any]:
    """Validate and sanitize query parameters"""
    validated = {}
    for key in allowed_params:
        if key in params:
            value = params[key]
            # Sanitize string values
            if isinstance(value, str):
                validated[key] = sanitize_string(value, max_length=500)
            else:
                validated[key] = value
    return validated

def create_validation_error(message: str, field: Optional[str] = None) -> Tuple[Any, int]:
    """Create a standardized validation error response"""
    error_data = {'error': 'Validation error', 'message': message}
    if field:
        error_data['field'] = field
    return jsonify(error_data), 400
