"""
SQLAlchemy database models for Flask IDS Backend
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index, func
import json

db = SQLAlchemy()

class Alert(db.Model):
    """
    Model for storing security alerts
    """
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    source_ip = db.Column(db.String(45), nullable=False, index=True)  # IPv6 compatible
    dest_ip = db.Column(db.String(45), nullable=False, index=True)
    protocol = db.Column(db.String(20), nullable=False)
    port = db.Column(db.Integer, nullable=True)
    type = db.Column(db.Enum('signature', 'anomaly', name='alert_type'), nullable=False)
    severity = db.Column(db.Enum('low', 'medium', 'high', 'critical', name='severity'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    confidence_score = db.Column(db.Float, nullable=True)  # For ML-based detections
    signature_id = db.Column(db.String(100), nullable=True)  # For signature-based detections
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    resolved = db.Column(db.Boolean, default=False, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.String(100), nullable=True)
    
    # Additional fields for enhanced analysis
    payload_size = db.Column(db.Integer, nullable=True)
    flags = db.Column(db.String(50), nullable=True)  # TCP flags, etc.
    user_agent = db.Column(db.String(500), nullable=True)
    uri = db.Column(db.String(1000), nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_alert_source_timestamp', 'source_ip', 'timestamp'),
        Index('idx_alert_type_severity', 'type', 'severity'),
        Index('idx_alert_unresolved', 'resolved', 'timestamp'),
    )
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'source_ip': self.source_ip,
            'dest_ip': self.dest_ip,
            'protocol': self.protocol,
            'port': self.port,
            'type': self.type,
            'severity': self.severity,
            'description': self.description,
            'confidence_score': self.confidence_score,
            'signature_id': self.signature_id,
            'timestamp': self.timestamp.isoformat(),
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': self.resolved_by,
            'payload_size': self.payload_size,
            'flags': self.flags,
            'user_agent': self.user_agent,
            'uri': self.uri
        }
    
    def __repr__(self):
        return f'<Alert {self.id}: {self.type} - {self.severity} from {self.source_ip}>'


class TrafficStat(db.Model):
    """
    Model for storing traffic statistics
    """
    __tablename__ = 'traffic_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    total_packets = db.Column(db.BigInteger, nullable=False, default=0)
    total_bytes = db.Column(db.BigInteger, nullable=False, default=0)
    active_connections = db.Column(db.Integer, nullable=False, default=0)
    protocol_distribution = db.Column(db.JSON, nullable=False, default=dict)  # JSON field for protocol counts
    anomaly_count = db.Column(db.Integer, nullable=False, default=0)
    packet_rate = db.Column(db.Float, nullable=False, default=0.0)  # packets per second
    byte_rate = db.Column(db.Float, nullable=False, default=0.0)  # bytes per second
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Top talkers and protocols
    top_source_ips = db.Column(db.JSON, nullable=True)  # JSON array of {ip: count}
    top_dest_ports = db.Column(db.JSON, nullable=True)  # JSON array of {port: count}
    
    # Network health metrics
    avg_packet_size = db.Column(db.Float, nullable=True)
    connection_success_rate = db.Column(db.Float, nullable=True)
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'total_packets': self.total_packets,
            'total_bytes': self.total_bytes,
            'active_connections': self.active_connections,
            'protocol_distribution': self.protocol_distribution,
            'anomaly_count': self.anomaly_count,
            'packet_rate': self.packet_rate,
            'byte_rate': self.byte_rate,
            'timestamp': self.timestamp.isoformat(),
            'top_source_ips': self.top_source_ips,
            'top_dest_ports': self.top_dest_ports,
            'avg_packet_size': self.avg_packet_size,
            'connection_success_rate': self.connection_success_rate
        }
    
    def __repr__(self):
        return f'<TrafficStat {self.id}: {self.total_packets} packets at {self.timestamp}>'


class UserActivity(db.Model):
    """
    Model for storing user activity for insider threat detection
    """
    __tablename__ = 'user_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), nullable=False, index=True)
    username = db.Column(db.String(100), nullable=False, index=True)
    activity_type = db.Column(db.Enum('login', 'file_access', 'network_access', 'privilege_escalation', 
                                    'data_exfiltration', 'suspicious_command', 'off_hours_access', 
                                    name='activity_type'), nullable=False)
    severity = db.Column(db.Enum('low', 'medium', 'high', 'critical', name='severity'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    source_ip = db.Column(db.String(45), nullable=True)
    destination = db.Column(db.String(500), nullable=True)  # File path, URL, etc.
    command = db.Column(db.Text, nullable=True)  # For command-based activities
    file_size = db.Column(db.BigInteger, nullable=True)  # For file access activities
    success = db.Column(db.Boolean, nullable=True)  # Whether the activity was successful
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Additional context
    session_id = db.Column(db.String(100), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    geolocation = db.Column(db.String(200), nullable=True)  # Country, city if available
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_activity_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_user_activity_type_severity', 'activity_type', 'severity'),
        Index('idx_user_activity_source_ip', 'source_ip'),
    )
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'activity_type': self.activity_type,
            'severity': self.severity,
            'description': self.description,
            'source_ip': self.source_ip,
            'destination': self.destination,
            'command': self.command,
            'file_size': self.file_size,
            'success': self.success,
            'timestamp': self.timestamp.isoformat(),
            'session_id': self.session_id,
            'user_agent': self.user_agent,
            'geolocation': self.geolocation
        }
    
    def __repr__(self):
        return f'<UserActivity {self.id}: {self.username} - {self.activity_type} ({self.severity})>'


class WhitelistRule(db.Model):
    """
    Model for storing whitelist rules to reduce false positives
    """
    __tablename__ = 'whitelist_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    rule_type = db.Column(db.Enum('ip', 'port', 'protocol', 'signature', 'user', name='rule_type'), nullable=False)
    value = db.Column(db.String(500), nullable=False)  # The actual rule value
    description = db.Column(db.Text, nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by = db.Column(db.String(100), nullable=True)
    
    # Index for fast lookups
    __table_args__ = (
        Index('idx_whitelist_type_value', 'rule_type', 'value'),
        Index('idx_whitelist_active', 'active'),
    )
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'rule_type': self.rule_type,
            'value': self.value,
            'description': self.description,
            'active': self.active,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by
        }
    
    def __repr__(self):
        return f'<WhitelistRule {self.id}: {self.rule_type}={self.value}>'


# Database initialization function
def init_db(app):
    """Initialize the database with the Flask app"""
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Insert default whitelist rules
        default_rules = [
            WhitelistRule(
                name='Localhost Traffic',
                rule_type='ip',
                value='127.0.0.1',
                description='Allow localhost traffic',
                created_by='system'
            ),
            WhitelistRule(
                name='Private Networks',
                rule_type='ip',
                value='192.168.0.0/16',
                description='Allow private network traffic',
                created_by='system'
            ),
            WhitelistRule(
                name='HTTP Traffic',
                rule_type='port',
                value='80',
                description='Allow HTTP traffic',
                created_by='system'
            ),
            WhitelistRule(
                name='HTTPS Traffic',
                rule_type='port',
                value='443',
                description='Allow HTTPS traffic',
                created_by='system'
            )
        ]
        
        # Only insert if they don't exist
        for rule in default_rules:
            existing = WhitelistRule.query.filter_by(
                rule_type=rule.rule_type,
                value=rule.value
            ).first()
            if not existing:
                db.session.add(rule)
        
        db.session.commit()
