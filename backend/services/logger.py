"""
Database logging service with deduplication logic
Handles saving alerts, traffic statistics, and user activities to database
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
from sqlalchemy import and_, func, desc
from models.db_models import db, Alert, TrafficStat, UserActivity, WhitelistRule

logger = logging.getLogger(__name__)

class DatabaseLogger:
    """
    Database logging service with deduplication and batch operations
    """
    
    def __init__(self, config):
        """
        Initialize database logger
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.alert_cache = {}  # For deduplication
        self.traffic_stats_cache = defaultdict(int)
        self.last_traffic_flush = datetime.utcnow()
        
        logger.info("DatabaseLogger initialized")
    
    def log_alert(self, detection_result: Dict[str, Any], packet_data: Dict[str, Any]) -> Optional[Alert]:
        """
        Log security alert to database with deduplication
        
        Args:
            detection_result: Detection result from analyzer
            packet_data: Original packet data
            
        Returns:
            Alert object if created, None if deduplicated
        """
        try:
            # Create deduplication key
            dedup_key = self._create_dedup_key(detection_result, packet_data)
            current_time = datetime.utcnow()
            
            # Check for recent duplicate alert
            if self._is_duplicate_alert(dedup_key, current_time):
                logger.debug(f"Deduplicated alert: {dedup_key}")
                return None
            
            # Create alert object
            alert = Alert(
                source_ip=packet_data.get('src_ip', 'unknown'),
                dest_ip=packet_data.get('dst_ip', 'unknown'),
                protocol=packet_data.get('protocol', 'unknown'),
                port=packet_data.get('dst_port'),
                type=detection_result.get('type', 'unknown'),
                severity=detection_result.get('severity', 'medium'),
                description=detection_result.get('description', ''),
                confidence_score=detection_result.get('confidence'),
                signature_id=detection_result.get('signature_id'),
                timestamp=current_time,
                payload_size=packet_data.get('payload_size'),
                flags=packet_data.get('flags'),
                user_agent=packet_data.get('user_agent'),
                uri=packet_data.get('uri')
            )
            
            # Save to database
            db.session.add(alert)
            db.session.commit()
            
            # Update cache
            self.alert_cache[dedup_key] = current_time
            
            # Clean old cache entries
            self._clean_alert_cache()
            
            logger.info(f"Logged alert: {alert.id} - {alert.type} - {alert.severity}")
            return alert
            
        except Exception as e:
            logger.error(f"Error logging alert: {e}")
            db.session.rollback()
            return None
    
    def _create_dedup_key(self, detection_result: Dict[str, Any], packet_data: Dict[str, Any]) -> str:
        """
        Create deduplication key for alert
        
        Args:
            detection_result: Detection result
            packet_data: Packet data
            
        Returns:
            Deduplication key string
        """
        source_ip = packet_data.get('src_ip', 'unknown')
        signature_id = detection_result.get('signature_id', 'unknown')
        dest_port = packet_data.get('dst_port', 'unknown')
        
        return f"{source_ip}:{signature_id}:{dest_port}"
    
    def _is_duplicate_alert(self, dedup_key: str, current_time: datetime) -> bool:
        """
        Check if alert is a duplicate within the deduplication window
        
        Args:
            dedup_key: Deduplication key
            current_time: Current timestamp
            
        Returns:
            True if duplicate
        """
        # Check cache first
        if dedup_key in self.alert_cache:
            last_time = self.alert_cache[dedup_key]
            if (current_time - last_time).total_seconds() < self.config.ALERT_DEDUP_WINDOW:
                return True
        
        # Check database for recent alerts
        cutoff_time = current_time - timedelta(seconds=self.config.ALERT_DEDUP_WINDOW)
        
        # Parse dedup key
        parts = dedup_key.split(':')
        if len(parts) >= 3:
            source_ip, signature_id, dest_port = parts[0], parts[1], parts[2]
            
            recent_alert = Alert.query.filter(
                and_(
                    Alert.source_ip == source_ip,
                    Alert.signature_id == signature_id,
                    Alert.port == (int(dest_port) if dest_port.isdigit() else None),
                    Alert.timestamp > cutoff_time
                )
            ).first()
            
            if recent_alert:
                return True
        
        return False
    
    def _clean_alert_cache(self):
        """Clean old entries from alert cache"""
        current_time = datetime.utcnow()
        cutoff_time = current_time - timedelta(seconds=self.config.ALERT_DEDUP_WINDOW * 2)
        
        keys_to_remove = [
            key for key, timestamp in self.alert_cache.items()
            if timestamp < cutoff_time
        ]
        
        for key in keys_to_remove:
            del self.alert_cache[key]
    
    def log_traffic_stats(self, packet_data: Dict[str, Any]):
        """
        Log traffic statistics (batched for performance)
        
        Args:
            packet_data: Packet data to aggregate
        """
        try:
            # Update cache
            protocol = packet_data.get('protocol', 'unknown')
            src_ip = packet_data.get('src_ip', 'unknown')
            dst_port = packet_data.get('dst_port', 0)
            
            self.traffic_stats_cache['total_packets'] += 1
            self.traffic_stats_cache['total_bytes'] += packet_data.get('raw_size', 0)
            self.traffic_stats_cache[f'protocol_{protocol}'] += 1
            self.traffic_stats_cache[f'src_ip_{src_ip}'] += 1
            self.traffic_stats_cache[f'dst_port_{dst_port}'] += 1
            
            # Flush to database periodically
            current_time = datetime.utcnow()
            if (current_time - self.last_traffic_flush).total_seconds() > 60:  # Flush every minute
                self._flush_traffic_stats()
                
        except Exception as e:
            logger.error(f"Error logging traffic stats: {e}")
    
    def _flush_traffic_stats(self):
        """Flush cached traffic statistics to database"""
        try:
            if not self.traffic_stats_cache:
                return
            
            # Calculate protocol distribution
            protocol_dist = {}
            src_ip_counts = {}
            dst_port_counts = {}
            
            for key, count in self.traffic_stats_cache.items():
                if key.startswith('protocol_'):
                    protocol = key.replace('protocol_', '')
                    protocol_dist[protocol] = count
                elif key.startswith('src_ip_'):
                    src_ip = key.replace('src_ip_', '')
                    src_ip_counts[src_ip] = count
                elif key.startswith('dst_port_'):
                    port = key.replace('dst_port_', '')
                    dst_port_counts[port] = count
            
            # Get top talkers (limit to 10)
            top_source_ips = [
                {'ip': ip, 'count': count}
                for ip, count in sorted(src_ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            ]
            
            # Get top destination ports (limit to 10)
            top_dest_ports = [
                {'port': port, 'count': count}
                for port, count in sorted(dst_port_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            ]
            
            # Calculate rates
            total_packets = self.traffic_stats_cache.get('total_packets', 0)
            total_bytes = self.traffic_stats_cache.get('total_bytes', 0)
            
            # Estimate active connections (unique source-destination pairs)
            active_connections = len(set(
                key.replace('src_ip_', '') for key in self.traffic_stats_cache.keys()
                if key.startswith('src_ip_')
            ))
            
            # Get recent anomaly count
            recent_anomalies = Alert.query.filter(
                and_(
                    Alert.type == 'anomaly',
                    Alert.timestamp > datetime.utcnow() - timedelta(minutes=1)
                )
            ).count()
            
            # Create traffic stat record
            traffic_stat = TrafficStat(
                total_packets=total_packets,
                total_bytes=total_bytes,
                active_connections=active_connections,
                protocol_distribution=protocol_dist,
                anomaly_count=recent_anomalies,
                packet_rate=total_packets / 60.0,  # packets per second (1 minute window)
                byte_rate=total_bytes / 60.0,  # bytes per second
                top_source_ips=top_source_ips,
                top_dest_ports=top_dest_ports,
                avg_packet_size=total_bytes / total_packets if total_packets > 0 else 0,
                timestamp=datetime.utcnow()
            )
            
            db.session.add(traffic_stat)
            db.session.commit()
            
            # Clear cache
            self.traffic_stats_cache.clear()
            self.last_traffic_flush = datetime.utcnow()
            
            logger.debug(f"Flushed traffic stats: {total_packets} packets, {active_connections} connections")
            
        except Exception as e:
            logger.error(f"Error flushing traffic stats: {e}")
            db.session.rollback()
    
    def log_user_activity(self, user_id: str, username: str, activity_type: str, 
                         severity: str, description: str, **kwargs) -> Optional[UserActivity]:
        """
        Log user activity for insider threat detection
        
        Args:
            user_id: User identifier
            username: Username
            activity_type: Type of activity
            severity: Severity level
            description: Activity description
            **kwargs: Additional activity data
            
        Returns:
            UserActivity object if created
        """
        try:
            activity = UserActivity(
                user_id=user_id,
                username=username,
                activity_type=activity_type,
                severity=severity,
                description=description,
                source_ip=kwargs.get('source_ip'),
                destination=kwargs.get('destination'),
                command=kwargs.get('command'),
                file_size=kwargs.get('file_size'),
                success=kwargs.get('success'),
                session_id=kwargs.get('session_id'),
                user_agent=kwargs.get('user_agent'),
                geolocation=kwargs.get('geolocation'),
                timestamp=datetime.utcnow()
            )
            
            db.session.add(activity)
            db.session.commit()
            
            logger.info(f"Logged user activity: {user_id} - {activity_type} - {severity}")
            return activity
            
        except Exception as e:
            logger.error(f"Error logging user activity: {e}")
            db.session.rollback()
            return None
    
    def get_recent_alerts(self, limit: int = 100, **filters) -> List[Alert]:
        """
        Get recent alerts with optional filtering
        
        Args:
            limit: Maximum number of alerts to return
            **filters: Filter parameters (type, severity, resolved, etc.)
            
        Returns:
            List of Alert objects
        """
        try:
            query = Alert.query
            
            # Apply filters
            if filters.get('type'):
                query = query.filter(Alert.type == filters['type'])
            
            if filters.get('severity'):
                query = query.filter(Alert.severity == filters['severity'])
            
            if filters.get('resolved') is not None:
                query = query.filter(Alert.resolved == filters['resolved'])
            
            if filters.get('start_date'):
                query = query.filter(Alert.timestamp >= filters['start_date'])
            
            if filters.get('end_date'):
                query = query.filter(Alert.timestamp <= filters['end_date'])
            
            if filters.get('source_ip'):
                query = query.filter(Alert.source_ip == filters['source_ip'])
            
            # Order by timestamp (newest first) and limit
            query = query.order_by(desc(Alert.timestamp)).limit(limit)
            
            return query.all()
            
        except Exception as e:
            logger.error(f"Error getting recent alerts: {e}")
            return []
    
    def get_traffic_stats(self, limit: int = 24) -> List[TrafficStat]:
        """
        Get recent traffic statistics
        
        Args:
            limit: Number of recent records to return
            
        Returns:
            List of TrafficStat objects
        """
        try:
            return TrafficStat.query.order_by(desc(TrafficStat.timestamp)).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error getting traffic stats: {e}")
            return []
    
    def get_user_activities(self, limit: int = 100, **filters) -> List[UserActivity]:
        """
        Get user activities with optional filtering
        
        Args:
            limit: Maximum number of activities to return
            **filters: Filter parameters (user_id, severity, activity_type, etc.)
            
        Returns:
            List of UserActivity objects
        """
        try:
            query = UserActivity.query
            
            # Apply filters
            if filters.get('user_id'):
                query = query.filter(UserActivity.user_id == filters['user_id'])
            
            if filters.get('severity'):
                query = query.filter(UserActivity.severity == filters['severity'])
            
            if filters.get('activity_type'):
                query = query.filter(UserActivity.activity_type == filters['activity_type'])
            
            if filters.get('start_date'):
                query = query.filter(UserActivity.timestamp >= filters['start_date'])
            
            if filters.get('end_date'):
                query = query.filter(UserActivity.timestamp <= filters['end_date'])
            
            # Order by timestamp (newest first) and limit
            query = query.order_by(desc(UserActivity.timestamp)).limit(limit)
            
            return query.all()
            
        except Exception as e:
            logger.error(f"Error getting user activities: {e}")
            return []
    
    def resolve_alert(self, alert_id: int, resolved_by: str = None) -> bool:
        """
        Mark alert as resolved
        
        Args:
            alert_id: Alert ID to resolve
            resolved_by: User who resolved the alert
            
        Returns:
            True if successful
        """
        try:
            alert = Alert.query.get(alert_id)
            if not alert:
                logger.warning(f"Alert {alert_id} not found")
                return False
            
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            alert.resolved_by = resolved_by
            
            db.session.commit()
            
            logger.info(f"Resolved alert {alert_id} by {resolved_by}")
            return True
            
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            db.session.rollback()
            return False
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """
        Get alert summary statistics
        
        Returns:
            Dictionary with alert statistics
        """
        try:
            current_time = datetime.utcnow()
            
            # Recent alerts (last 24 hours)
            recent_cutoff = current_time - timedelta(hours=24)
            recent_alerts = Alert.query.filter(Alert.timestamp > recent_cutoff).count()
            
            # Unresolved alerts
            unresolved_alerts = Alert.query.filter(Alert.resolved == False).count()
            
            # Alerts by type
            type_counts = db.session.query(
                Alert.type, func.count(Alert.id)
            ).filter(Alert.timestamp > recent_cutoff).group_by(Alert.type).all()
            
            # Alerts by severity
            severity_counts = db.session.query(
                Alert.severity, func.count(Alert.id)
            ).filter(Alert.timestamp > recent_cutoff).group_by(Alert.severity).all()
            
            return {
                'total_recent_alerts': recent_alerts,
                'unresolved_alerts': unresolved_alerts,
                'alerts_by_type': dict(type_counts),
                'alerts_by_severity': dict(severity_counts),
                'last_updated': current_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting alert summary: {e}")
            return {}
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """
        Clean up old data to manage database size
        
        Args:
            days_to_keep: Number of days of data to keep
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Delete old alerts
            old_alerts = Alert.query.filter(Alert.timestamp < cutoff_date).count()
            Alert.query.filter(Alert.timestamp < cutoff_date).delete()
            
            # Delete old traffic stats
            old_traffic = TrafficStat.query.filter(TrafficStat.timestamp < cutoff_date).count()
            TrafficStat.query.filter(TrafficStat.timestamp < cutoff_date).delete()
            
            # Delete old user activities
            old_activities = UserActivity.query.filter(UserActivity.timestamp < cutoff_date).count()
            UserActivity.query.filter(UserActivity.timestamp < cutoff_date).delete()
            
            db.session.commit()
            
            logger.info(f"Cleaned up old data: {old_alerts} alerts, {old_traffic} traffic stats, {old_activities} activities")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            db.session.rollback()
