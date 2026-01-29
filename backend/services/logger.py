"""
Database logging service with deduplication logic
Handles saving alerts, traffic statistics, and user activities to database
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from collections import defaultdict
from models.db_models import (
    alerts_collection, traffic_stats_collection, user_activities_collection,
    alert_to_dict, traffic_stat_to_dict, user_activity_to_dict, to_object_id
)
from .cache import CacheService, CachePrefixes, CacheTTL

logger = logging.getLogger(__name__)

# Protocol number to name mapping (IANA IP protocol numbers)
PROTOCOL_MAP = {
    0: 'HOPOPT',      # IPv6 Hop-by-Hop Option
    1: 'ICMP',        # Internet Control Message Protocol
    2: 'IGMP',        # Internet Group Management Protocol
    4: 'IPv4',        # IPv4 encapsulation
    6: 'TCP',         # Transmission Control Protocol
    17: 'UDP',        # User Datagram Protocol
    41: 'IPv6',       # IPv6 encapsulation
    47: 'GRE',        # Generic Routing Encapsulation
    50: 'ESP',        # Encapsulating Security Payload
    51: 'AH',         # Authentication Header
    58: 'ICMPv6',     # ICMP for IPv6
    89: 'OSPF',       # Open Shortest Path First
    132: 'SCTP',      # Stream Control Transmission Protocol
}

def normalize_protocol(protocol: Any) -> str:
    """
    Normalize protocol identifier to a consistent string name
    
    Args:
        protocol: Protocol identifier (string, number, or other)
        
    Returns:
        Normalized protocol name as string
    """
    if protocol is None:
        return 'Other'
    
    # If already a string, normalize it
    if isinstance(protocol, str):
        protocol_upper = protocol.upper().strip()
        # Handle common variations
        if protocol_upper in ['TCP', 'UDP', 'ICMP', 'ICMPV6', 'IPV6', 'IPV4', 'ARP', 'GRE', 'ESP', 'AH', 'OSPF', 'SCTP', 'OTHER', 'UNKNOWN']:
            # Normalize casing
            if protocol_upper == 'ICMPV6':
                return 'ICMPv6'
            elif protocol_upper == 'IPV6':
                return 'IPv6'
            elif protocol_upper == 'IPV4':
                return 'IPv4'
            elif protocol_upper in ['UNKNOWN', 'OTHER']:
                return 'Other'
            else:
                return protocol_upper
        # Handle ether type strings
        if protocol_upper.startswith('ETHER-'):
            return protocol_upper  # Keep as-is for ether types
        # Return as-is if it's a valid string
        return protocol_upper if protocol_upper else 'Other'
    
    # If it's a number, map it to protocol name
    if isinstance(protocol, (int, float)):
        protocol_num = int(protocol)
        return PROTOCOL_MAP.get(protocol_num, f'Protocol-{protocol_num}')
    
    # Fallback for unknown types
    try:
        protocol_str = str(protocol).upper().strip()
        if protocol_str in ['UNKNOWN', 'OTHER', '']:
            return 'Other'
        return protocol_str if protocol_str else 'Other'
    except:
        return 'Other'

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
        self.last_traffic_flush = datetime.now(timezone.utc)
        
        # Initialize cache service
        self.cache = CacheService(config)
        
        logger.info("DatabaseLogger initialized with caching")
    
    def log_alert(self, detection_result: Dict[str, Any], packet_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Log security alert to database with deduplication
        
        Args:
            detection_result: Detection result from analyzer
            packet_data: Original packet data
            
        Returns:
            Alert document if created, None if deduplicated
        """
        try:
            # Create deduplication key
            dedup_key = self._create_dedup_key(detection_result, packet_data)
            current_time = datetime.now(timezone.utc)
            
            # Check for recent duplicate alert
            if self._is_duplicate_alert(dedup_key, current_time):
                logger.debug(f"Deduplicated alert: {dedup_key}")
                return None
            
            # Create alert document
            alert_doc = {
                'source_ip': packet_data.get('src_ip', 'unknown'),
                'dest_ip': packet_data.get('dst_ip', 'unknown'),
                'protocol': packet_data.get('protocol', 'unknown'),
                'port': packet_data.get('dst_port'),
                'type': detection_result.get('type', 'unknown'),
                'severity': detection_result.get('severity', 'medium'),
                'description': detection_result.get('description', ''),
                'confidence_score': detection_result.get('confidence'),
                'signature_id': detection_result.get('signature_id'),
                'timestamp': current_time,
                'resolved': False,
                'resolved_at': None,
                'resolved_by': None,
                'payload_size': packet_data.get('payload_size'),
                'flags': packet_data.get('flags'),
                'user_agent': packet_data.get('user_agent'),
                'uri': packet_data.get('uri')
            }
            
            # Save to database
            if alerts_collection is not None:
                result = alerts_collection.insert_one(alert_doc)
            else:
                logger.warning("alerts_collection is None, skipping alert insert")
                return None
            alert_doc['_id'] = result.inserted_id
            
            # Update cache
            self.alert_cache[dedup_key] = current_time
            
            # Clean old cache entries
            self._clean_alert_cache()
            
            logger.info(f"Logged alert: {result.inserted_id} - {alert_doc['type']} - {alert_doc['severity']}")
            return alert_doc
            
        except Exception as e:
            logger.error(f"Error logging alert: {e}")
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
        # Use getattr with default to handle missing config attribute
        dedup_window = getattr(self.config, 'ALERT_DEDUP_WINDOW', 300)
        
        # Check cache first
        if dedup_key in self.alert_cache:
            last_time = self.alert_cache[dedup_key]
            # Ensure last_time is timezone-aware
            if last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=timezone.utc)
            if (current_time - last_time).total_seconds() < dedup_window:
                return True
        
        # Check database for recent alerts
        cutoff_time = current_time - timedelta(seconds=dedup_window)
        
        # Parse dedup key
        parts = dedup_key.split(':')
        if len(parts) >= 3:
            source_ip, signature_id, dest_port = parts[0], parts[1], parts[2]
            
            query = {
                'source_ip': source_ip,
                'signature_id': signature_id,
                'timestamp': {'$gt': cutoff_time}
            }
            
            # Add port filter if it's a number
            try:
                port_int = int(dest_port)
                query['port'] = port_int
            except (ValueError, TypeError):
                query['port'] = dest_port
            
            if alerts_collection is not None:
                try:
                    recent_alert = alerts_collection.find_one(query)
                    if recent_alert:
                        return True
                except Exception as e:
                    logger.debug(f"Error checking for duplicate alert: {e}")
            else:
                logger.warning("alerts_collection is None, skipping duplicate check")
        
        return False
    
    def _clean_alert_cache(self):
        """Clean old entries from alert cache"""
        current_time = datetime.now(timezone.utc)
        # Use getattr with default to handle missing config attribute
        dedup_window = getattr(self.config, 'ALERT_DEDUP_WINDOW', 300)
        cutoff_time = current_time - timedelta(seconds=dedup_window * 2)
        
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
            # Normalize protocol name before caching
            protocol = normalize_protocol(packet_data.get('protocol', 'Other'))
            src_ip = packet_data.get('src_ip', 'unknown')
            dst_port = packet_data.get('dst_port', 0)
            
            self.traffic_stats_cache['total_packets'] += 1
            self.traffic_stats_cache['total_bytes'] += packet_data.get('raw_size', 0)
            self.traffic_stats_cache[f'protocol_{protocol}'] += 1
            self.traffic_stats_cache[f'src_ip_{src_ip}'] += 1
            self.traffic_stats_cache[f'dst_port_{dst_port}'] += 1
            
            # Flush to database periodically (30 seconds instead of 60)
            current_time = datetime.now(timezone.utc)
            flush_interval = getattr(self.config, 'TRAFFIC_STATS_FLUSH_INTERVAL', 30)
            if (current_time - self.last_traffic_flush).total_seconds() > flush_interval:
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
                    # Normalize protocol name and filter out invalid ones
                    normalized_protocol = normalize_protocol(protocol)
                    if normalized_protocol and (normalized_protocol != 'Other' or count > 0):
                        # Aggregate counts for the same normalized protocol
                        if normalized_protocol in protocol_dist:
                            protocol_dist[normalized_protocol] += count
                        else:
                            protocol_dist[normalized_protocol] = count
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
            recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=1)
            if alerts_collection is not None:
                try:
                    recent_anomalies = alerts_collection.count_documents({
                        'type': 'anomaly',
                        'timestamp': {'$gt': recent_cutoff}
                    })
                except Exception as e:
                    logger.debug(f"Error counting recent anomalies: {e}")
                    recent_anomalies = 0
            else:
                recent_anomalies = 0
            
            # Calculate flush interval for rate calculations
            flush_interval = getattr(self.config, 'TRAFFIC_STATS_FLUSH_INTERVAL', 30)
            
            # Create traffic stat document
            traffic_stat_doc = {
                'total_packets': total_packets,
                'total_bytes': total_bytes,
                'active_connections': active_connections,
                'protocol_distribution': protocol_dist,
                'anomaly_count': recent_anomalies,
                'packet_rate': total_packets / flush_interval if flush_interval > 0 else 0,  # packets per second
                'byte_rate': total_bytes / flush_interval if flush_interval > 0 else 0,  # bytes per second
                'top_source_ips': top_source_ips,
                'top_dest_ports': top_dest_ports,
                'avg_packet_size': total_bytes / total_packets if total_packets > 0 else 0,
                'connection_success_rate': None,  # Can be calculated later if needed
                'timestamp': datetime.now(timezone.utc)
            }
            
            if traffic_stats_collection is not None:
                traffic_stats_collection.insert_one(traffic_stat_doc)
            else:
                logger.warning("traffic_stats_collection is None, skipping insert")
            
            # Clear cache
            self.traffic_stats_cache.clear()
            self.last_traffic_flush = datetime.now(timezone.utc)
            
            logger.debug(f"Flushed traffic stats: {total_packets} packets, {active_connections} connections")
            
        except Exception as e:
            logger.error(f"Error flushing traffic stats: {e}")
    
    def log_user_activity(self, user_id: str, username: str, activity_type: str, 
                         severity: str, description: str, **kwargs) -> Optional[Dict[str, Any]]:
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
            UserActivity document if created
        """
        try:
            activity_doc = {
                'user_id': user_id,
                'username': username,
                'activity_type': activity_type,
                'severity': severity,
                'description': description,
                'source_ip': kwargs.get('source_ip'),
                'destination': kwargs.get('destination'),
                'command': kwargs.get('command'),
                'file_size': kwargs.get('file_size'),
                'success': kwargs.get('success'),
                'session_id': kwargs.get('session_id'),
                'user_agent': kwargs.get('user_agent'),
                'geolocation': kwargs.get('geolocation'),
                'timestamp': datetime.now(timezone.utc)
            }
            
            result = user_activities_collection.insert_one(activity_doc)
            activity_doc['_id'] = result.inserted_id
            
            logger.info(f"Logged user activity: {user_id} - {activity_type} - {severity}")
            return activity_doc
            
        except Exception as e:
            logger.error(f"Error logging user activity: {e}")
            return None
    
    def get_recent_alerts(self, limit: int = 100, **filters) -> List[Dict[str, Any]]:
        """
        Get recent alerts with optional filtering and caching
        
        Args:
            limit: Maximum number of alerts to return
            **filters: Filter parameters (type, severity, resolved, etc.)
            
        Returns:
            List of alert documents
        """
        try:
            # Create cache key based on filters
            cache_key = f"recent_{limit}_{hash(str(sorted(filters.items())))}"
            
            # Try to get from cache first
            cached_result = self.cache.get(CachePrefixes.ALERTS, cache_key)
            if cached_result:
                logger.debug("Returning alerts from cache")
                return cached_result
            
            # Build MongoDB query
            query = {}
            
            # Apply filters
            if filters.get('type'):
                query['type'] = filters['type']
            
            if filters.get('severity'):
                query['severity'] = filters['severity']
            
            if filters.get('resolved') is not None:
                query['resolved'] = filters['resolved']
            
            if filters.get('start_date'):
                if 'timestamp' not in query:
                    query['timestamp'] = {}
                query['timestamp']['$gte'] = filters['start_date']
            
            if filters.get('end_date'):
                if 'timestamp' not in query:
                    query['timestamp'] = {}
                query['timestamp']['$lte'] = filters['end_date']
            
            if filters.get('source_ip'):
                query['source_ip'] = filters['source_ip']
            
            # Execute query with sort and limit
            alerts = list(alerts_collection.find(query)
                         .sort('timestamp', -1)
                         .limit(limit))
            
            # Convert to dictionaries with string IDs
            alert_dicts = [alert_to_dict(alert) for alert in alerts]
            
            # Cache the result
            self.cache.set(CachePrefixes.ALERTS, cache_key, alert_dicts, CacheTTL.SHORT)
            
            return alerts  # Return raw documents for compatibility
            
        except Exception as e:
            logger.error(f"Error getting recent alerts: {e}")
            return []
    
    def get_traffic_stats(self, limit: int = 24) -> List[Dict[str, Any]]:
        """
        Get recent traffic statistics with caching
        
        Args:
            limit: Number of recent records to return
            
        Returns:
            List of traffic stat documents
        """
        try:
            cache_key = f"recent_{limit}"
            
            # Try cache first
            cached_result = self.cache.get(CachePrefixes.TRAFFIC_STATS, cache_key)
            if cached_result:
                logger.debug("Returning traffic stats from cache")
                return cached_result
            
            if traffic_stats_collection is not None:
                stats = list(traffic_stats_collection.find()
                            .sort('timestamp', -1)
                            .limit(limit))
            else:
                logger.warning("traffic_stats_collection is None, returning empty list")
                stats = []
            
            # Cache the result
            stat_dicts = [traffic_stat_to_dict(stat) for stat in stats]
            self.cache.set(CachePrefixes.TRAFFIC_STATS, cache_key, stat_dicts, CacheTTL.SHORT)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting traffic stats: {e}")
            return []
    
    def get_user_activities(self, limit: int = 100, **filters) -> List[Dict[str, Any]]:
        """
        Get user activities with optional filtering
        
        Args:
            limit: Maximum number of activities to return
            **filters: Filter parameters (user_id, severity, activity_type, etc.)
            
        Returns:
            List of user activity documents
        """
        try:
            # Check if collection is initialized
            if user_activities_collection is None:
                logger.warning("User activities collection not initialized, returning empty list")
                return []
            
            # Build MongoDB query
            query = {}
            
            # Apply filters
            if filters.get('user_id'):
                query['user_id'] = filters['user_id']
            
            if filters.get('severity'):
                query['severity'] = filters['severity']
            
            if filters.get('activity_type'):
                query['activity_type'] = filters['activity_type']
            
            if filters.get('start_date'):
                if 'timestamp' not in query:
                    query['timestamp'] = {}
                query['timestamp']['$gte'] = filters['start_date']
            
            if filters.get('end_date'):
                if 'timestamp' not in query:
                    query['timestamp'] = {}
                query['timestamp']['$lte'] = filters['end_date']
            
            # Execute query with sort and limit
            activities = list(user_activities_collection.find(query)
                             .sort('timestamp', -1)
                             .limit(limit))
            
            return activities
            
        except Exception as e:
            logger.error(f"Error getting user activities: {e}")
            return []
    
    def get_realtime_stats(self) -> Dict[str, Any]:
        """
        Get real-time traffic statistics from in-memory cache
        
        Returns:
            Dictionary with current real-time stats (not yet flushed to DB)
        """
        try:
            if not self.traffic_stats_cache:
                return {
                    'total_packets': 0,
                    'total_bytes': 0,
                    'active_connections': 0,
                    'protocol_distribution': {},
                    'top_source_ips': [],
                    'top_dest_ports': [],
                    'packet_rate': 0,
                    'byte_rate': 0,
                    'avg_packet_size': 0,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Calculate protocol distribution
            protocol_dist = {}
            src_ip_counts = {}
            dst_port_counts = {}
            
            for key, count in self.traffic_stats_cache.items():
                if key.startswith('protocol_'):
                    protocol = key.replace('protocol_', '')
                    # Normalize protocol name and filter out invalid ones
                    normalized_protocol = normalize_protocol(protocol)
                    if normalized_protocol and (normalized_protocol != 'Other' or count > 0):
                        # Aggregate counts for the same normalized protocol
                        if normalized_protocol in protocol_dist:
                            protocol_dist[normalized_protocol] += count
                        else:
                            protocol_dist[normalized_protocol] = count
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
            
            total_packets = self.traffic_stats_cache.get('total_packets', 0)
            total_bytes = self.traffic_stats_cache.get('total_bytes', 0)
            
            # Calculate rates based on time since last flush
            time_since_flush = (datetime.now(timezone.utc) - self.last_traffic_flush).total_seconds()
            if time_since_flush > 0:
                packet_rate = total_packets / time_since_flush
                byte_rate = total_bytes / time_since_flush
            else:
                packet_rate = 0
                byte_rate = 0
            
            # Estimate active connections
            active_connections = len(set(
                key.replace('src_ip_', '') for key in self.traffic_stats_cache.keys()
                if key.startswith('src_ip_')
            ))
            
            return {
                'total_packets': total_packets,
                'total_bytes': total_bytes,
                'active_connections': active_connections,
                'protocol_distribution': protocol_dist,
                'top_source_ips': top_source_ips,
                'top_dest_ports': top_dest_ports,
                'packet_rate': packet_rate,
                'byte_rate': byte_rate,
                'avg_packet_size': total_bytes / total_packets if total_packets > 0 else 0,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'cache_age_seconds': time_since_flush
            }
            
        except Exception as e:
            logger.error(f"Error getting real-time stats: {e}")
            return {}
    
    def resolve_alert(self, alert_id: str, resolved_by: str = None) -> bool:
        """
        Mark alert as resolved
        
        Args:
            alert_id: Alert ID to resolve (string or ObjectId)
            resolved_by: User who resolved the alert
            
        Returns:
            True if successful
        """
        try:
            obj_id = to_object_id(alert_id)
            if not obj_id:
                logger.warning(f"Invalid alert ID format: {alert_id}")
                return False
            
            if alerts_collection is None:
                logger.warning("alerts_collection is None, cannot resolve alert")
                return False
            
            result = alerts_collection.update_one(
                {'_id': obj_id},
                {
                    '$set': {
                        'resolved': True,
                        'resolved_at': datetime.now(timezone.utc),
                        'resolved_by': resolved_by
                    }
                }
            )
            
            if result.matched_count == 0:
                logger.warning(f"Alert {alert_id} not found")
                return False
            
            logger.info(f"Resolved alert {alert_id} by {resolved_by}")
            return True
            
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return False
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """
        Get alert summary statistics with caching
        
        Returns:
            Dictionary with alert statistics
        """
        try:
            # Check if collection is initialized
            if alerts_collection is None:
                logger.warning("Alerts collection not initialized, returning empty summary")
                return {
                    'total_recent_alerts': 0,
                    'unresolved_alerts': 0,
                    'alerts_by_type': {},
                    'alerts_by_severity': {},
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
            
            cache_key = "summary"
            
            # Try cache first
            cached_result = self.cache.get(CachePrefixes.ALERT_SUMMARY, cache_key)
            if cached_result:
                logger.debug("Returning alert summary from cache")
                return cached_result
            
            current_time = datetime.now(timezone.utc)
            
            # Recent alerts (last 24 hours)
            recent_cutoff = current_time - timedelta(hours=24)
            if alerts_collection is not None:
                try:
                    recent_alerts = alerts_collection.count_documents({
                        'timestamp': {'$gt': recent_cutoff}
                    })
                    
                    # Unresolved alerts
                    unresolved_alerts = alerts_collection.count_documents({
                        'resolved': False
                    })
                except Exception as e:
                    logger.error(f"Error getting alert counts: {e}")
                    recent_alerts = 0
                    unresolved_alerts = 0
            else:
                logger.warning("alerts_collection is None, using default values")
                recent_alerts = 0
                unresolved_alerts = 0
            
            # Alerts by type using aggregation
            type_counts = {}
            severity_counts = {}
            if alerts_collection is not None:
                try:
                    type_pipeline = [
                        {'$match': {'timestamp': {'$gt': recent_cutoff}}},
                        {'$group': {'_id': '$type', 'count': {'$sum': 1}}}
                    ]
                    for result in alerts_collection.aggregate(type_pipeline):
                        type_counts[result['_id']] = result['count']
                    
                    # Alerts by severity using aggregation
                    severity_pipeline = [
                        {'$match': {'timestamp': {'$gt': recent_cutoff}}},
                        {'$group': {'_id': '$severity', 'count': {'$sum': 1}}}
                    ]
                    for result in alerts_collection.aggregate(severity_pipeline):
                        severity_counts[result['_id']] = result['count']
                except Exception as e:
                    logger.error(f"Error getting alert aggregations: {e}")
            
            summary = {
                'total_recent_alerts': recent_alerts,
                'unresolved_alerts': unresolved_alerts,
                'alerts_by_type': type_counts,
                'alerts_by_severity': severity_counts,
                'last_updated': current_time.isoformat()
            }
            
            # Cache the result
            self.cache.set(CachePrefixes.ALERT_SUMMARY, cache_key, summary, CacheTTL.SHORT)
            
            return summary
            
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
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            # Delete old alerts
            if alerts_collection is not None:
                old_alerts_result = alerts_collection.delete_many({
                    'timestamp': {'$lt': cutoff_date}
                })
                old_alerts = old_alerts_result.deleted_count
            else:
                logger.warning("alerts_collection is None, skipping cleanup")
                old_alerts = 0
            
            # Delete old traffic stats
            if traffic_stats_collection is not None:
                old_traffic_result = traffic_stats_collection.delete_many({
                    'timestamp': {'$lt': cutoff_date}
                })
                old_traffic = old_traffic_result.deleted_count
            else:
                logger.warning("traffic_stats_collection is None, skipping cleanup")
                old_traffic = 0
            
            # Delete old user activities
            if user_activities_collection is not None:
                old_activities_result = user_activities_collection.delete_many({
                    'timestamp': {'$lt': cutoff_date}
                })
                old_activities = old_activities_result.deleted_count
            else:
                logger.warning("user_activities_collection is None, skipping cleanup")
                old_activities = 0
            
            logger.info(f"Cleaned up old data: {old_alerts} alerts, {old_traffic} traffic stats, {old_activities} activities")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
