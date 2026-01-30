"""
Feature extraction service for supervised ML classification
Extracts all required features: packet size, protocol type, connection duration,
failed login attempts, data transfer rate, and access frequency
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class ConnectionTracker:
    """
    Tracks active connections and calculates connection duration
    """
    
    def __init__(self, timeout_seconds: int = 300):
        """
        Initialize connection tracker
        
        Args:
            timeout_seconds: Timeout for inactive connections (default 5 minutes)
        """
        self.connections = {}  # {(src_ip, dst_ip, dst_port): start_time}
        self.timeout = timedelta(seconds=timeout_seconds)
        
    def start_connection(self, src_ip: str, dst_ip: str, dst_port: int) -> datetime:
        """
        Start tracking a new connection
        
        Args:
            src_ip: Source IP address
            dst_ip: Destination IP address
            dst_port: Destination port
            
        Returns:
            Connection start time
        """
        key = (src_ip, dst_ip, dst_port)
        current_time = datetime.now(timezone.utc)
        
        if key not in self.connections:
            self.connections[key] = current_time
            
        return self.connections[key]
    
    def get_connection_duration(self, src_ip: str, dst_ip: str, dst_port: int) -> float:
        """
        Get duration of an active connection
        
        Args:
            src_ip: Source IP address
            dst_ip: Destination IP address
            dst_port: Destination port
            
        Returns:
            Connection duration in seconds, or 0 if not found
        """
        key = (src_ip, dst_ip, dst_port)
        if key in self.connections:
            start_time = self.connections[key]
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            return max(0, duration)
        return 0.0
    
    def end_connection(self, src_ip: str, dst_ip: str, dst_port: int) -> Optional[float]:
        """
        End a connection and return its duration
        
        Args:
            src_ip: Source IP address
            dst_ip: Destination IP address
            dst_port: Destination port
            
        Returns:
            Connection duration in seconds, or None if connection not found
        """
        key = (src_ip, dst_ip, dst_port)
        if key in self.connections:
            start_time = self.connections[key]
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            del self.connections[key]
            return max(0, duration)
        return None
    
    def cleanup_stale_connections(self):
        """Remove stale connections that have timed out"""
        current_time = datetime.now(timezone.utc)
        keys_to_remove = [
            key for key, start_time in self.connections.items()
            if (current_time - start_time) > self.timeout
        ]
        for key in keys_to_remove:
            del self.connections[key]
        
        if keys_to_remove:
            logger.debug(f"Cleaned up {len(keys_to_remove)} stale connections")


class LoginAttemptTracker:
    """
    Tracks failed login attempts per source IP
    """
    
    def __init__(self, window_seconds: int = 3600):
        """
        Initialize login attempt tracker
        
        Args:
            window_seconds: Time window for tracking attempts (default 1 hour)
        """
        self.failed_attempts = defaultdict(list)  # {src_ip: [timestamps]}
        self.window = timedelta(seconds=window_seconds)
        
    def record_failed_attempt(self, src_ip: str):
        """
        Record a failed login attempt
        
        Args:
            src_ip: Source IP address
        """
        current_time = datetime.now(timezone.utc)
        self.failed_attempts[src_ip].append(current_time)
        self._cleanup_old_attempts(src_ip)
        
    def get_failed_attempt_count(self, src_ip: str) -> int:
        """
        Get number of failed login attempts for an IP within the time window
        
        Args:
            src_ip: Source IP address
            
        Returns:
            Number of failed attempts
        """
        self._cleanup_old_attempts(src_ip)
        return len(self.failed_attempts.get(src_ip, []))
    
    def _cleanup_old_attempts(self, src_ip: str):
        """Remove attempts outside the time window"""
        if src_ip not in self.failed_attempts:
            return
            
        current_time = datetime.now(timezone.utc)
        cutoff_time = current_time - self.window
        
        self.failed_attempts[src_ip] = [
            timestamp for timestamp in self.failed_attempts[src_ip]
            if timestamp > cutoff_time
        ]
        
        # Remove empty entries
        if not self.failed_attempts[src_ip]:
            del self.failed_attempts[src_ip]


class FlowRateCalculator:
    """
    Calculates data transfer rate for connections
    """
    
    def __init__(self, window_seconds: int = 60):
        """
        Initialize flow rate calculator
        
        Args:
            window_seconds: Time window for rate calculation (default 1 minute)
        """
        self.flow_data = defaultdict(lambda: {'bytes': 0, 'start_time': None})  # {flow_key: data}
        self.window = timedelta(seconds=window_seconds)
        
    def update_flow(self, src_ip: str, dst_ip: str, dst_port: int, bytes_transferred: int):
        """
        Update flow data with bytes transferred
        
        Args:
            src_ip: Source IP address
            dst_ip: Destination IP address
            dst_port: Destination port
            bytes_transferred: Number of bytes transferred
        """
        key = (src_ip, dst_ip, dst_port)
        current_time = datetime.now(timezone.utc)
        
        if key not in self.flow_data or self.flow_data[key]['start_time'] is None:
            self.flow_data[key]['start_time'] = current_time
            self.flow_data[key]['bytes'] = 0
        
        self.flow_data[key]['bytes'] += bytes_transferred
        
        # Cleanup old flows
        self._cleanup_old_flows()
    
    def get_transfer_rate(self, src_ip: str, dst_ip: str, dst_port: int) -> float:
        """
        Get data transfer rate for a flow
        
        Args:
            src_ip: Source IP address
            dst_ip: Destination IP address
            dst_port: Destination port
            
        Returns:
            Transfer rate in bytes per second, or 0 if not found
        """
        key = (src_ip, dst_ip, dst_port)
        if key not in self.flow_data:
            return 0.0
        
        flow = self.flow_data[key]
        if flow['start_time'] is None or flow['bytes'] == 0:
            return 0.0
        
        duration = (datetime.now(timezone.utc) - flow['start_time']).total_seconds()
        if duration <= 0:
            return 0.0
        
        return flow['bytes'] / duration
    
    def _cleanup_old_flows(self):
        """Remove flows that are outside the time window"""
        current_time = datetime.now(timezone.utc)
        keys_to_remove = [
            key for key, data in self.flow_data.items()
            if data['start_time'] and (current_time - data['start_time']) > self.window
        ]
        for key in keys_to_remove:
            del self.flow_data[key]


class AccessFrequencyTracker:
    """
    Tracks access frequency per source IP
    """
    
    def __init__(self, window_seconds: int = 300):
        """
        Initialize access frequency tracker
        
        Args:
            window_seconds: Time window for frequency calculation (default 5 minutes)
        """
        self.access_times = defaultdict(list)  # {src_ip: [timestamps]}
        self.window = timedelta(seconds=window_seconds)
        
    def record_access(self, src_ip: str):
        """
        Record an access event
        
        Args:
            src_ip: Source IP address
        """
        current_time = datetime.now(timezone.utc)
        self.access_times[src_ip].append(current_time)
        self._cleanup_old_accesses(src_ip)
    
    def get_access_frequency(self, src_ip: str) -> float:
        """
        Get access frequency for an IP (accesses per second)
        
        Args:
            src_ip: Source IP address
            
        Returns:
            Access frequency (accesses per second)
        """
        self._cleanup_old_accesses(src_ip)
        
        if src_ip not in self.access_times or not self.access_times[src_ip]:
            return 0.0
        
        accesses = self.access_times[src_ip]
        if len(accesses) < 2:
            return 0.0
        
        time_span = (accesses[-1] - accesses[0]).total_seconds()
        if time_span <= 0:
            return float(len(accesses))
        
        return len(accesses) / time_span
    
    def _cleanup_old_accesses(self, src_ip: str):
        """Remove accesses outside the time window"""
        if src_ip not in self.access_times:
            return
        
        current_time = datetime.now(timezone.utc)
        cutoff_time = current_time - self.window
        
        self.access_times[src_ip] = [
            timestamp for timestamp in self.access_times[src_ip]
            if timestamp > cutoff_time
        ]
        
        # Remove empty entries
        if not self.access_times[src_ip]:
            del self.access_times[src_ip]


class FeatureExtractor:
    """
    Main feature extraction service that combines all feature extractors
    """
    
    def __init__(self, config=None):
        """
        Initialize feature extractor
        
        Args:
            config: Configuration object (optional)
        """
        self.connection_tracker = ConnectionTracker()
        self.login_tracker = LoginAttemptTracker()
        self.flow_calculator = FlowRateCalculator()
        self.frequency_tracker = AccessFrequencyTracker()
        
        # Protocol encoding map
        self.protocol_map = {
            'TCP': 1,
            'UDP': 2,
            'ICMP': 3,
            'unknown': 0
        }
        
        logger.info("FeatureExtractor initialized")
    
    def extract_features(self, packet_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract all required features from packet data
        
        Args:
            packet_data: Parsed packet data dictionary
            
        Returns:
            Dictionary with extracted features:
            - packet_size: float
            - protocol_type: int (encoded)
            - connection_duration: float (seconds)
            - failed_login_attempts: int
            - data_transfer_rate: float (bytes/second)
            - access_frequency: float (accesses/second)
        """
        try:
            src_ip = packet_data.get('src_ip', 'unknown')
            dst_ip = packet_data.get('dst_ip', 'unknown')
            dst_port = packet_data.get('dst_port', 0)
            protocol = packet_data.get('protocol', 'unknown')
            
            # 1. Packet Size
            packet_size = float(packet_data.get('payload_size', 0) or packet_data.get('raw_size', 0))
            
            # 2. Protocol Type (encoded)
            protocol_type = float(self.protocol_map.get(protocol, 0))
            
            # 3. Connection Duration
            # Start tracking if new connection
            self.connection_tracker.start_connection(src_ip, dst_ip, dst_port)
            connection_duration = self.connection_tracker.get_connection_duration(src_ip, dst_ip, dst_port)
            
            # 4. Failed Login Attempts
            failed_login_attempts = float(self.login_tracker.get_failed_attempt_count(src_ip))
            
            # 5. Data Transfer Rate
            bytes_transferred = packet_data.get('payload_size', 0) or packet_data.get('raw_size', 0)
            self.flow_calculator.update_flow(src_ip, dst_ip, dst_port, bytes_transferred)
            data_transfer_rate = self.flow_calculator.get_transfer_rate(src_ip, dst_ip, dst_port)
            
            # 6. Access Frequency
            self.frequency_tracker.record_access(src_ip)
            access_frequency = self.frequency_tracker.get_access_frequency(src_ip)
            
            # Cleanup stale data periodically
            if hash(str(packet_data.get('timestamp', datetime.now(timezone.utc)))) % 100 == 0:
                self.connection_tracker.cleanup_stale_connections()
            
            features = {
                'packet_size': packet_size,
                'protocol_type': protocol_type,
                'connection_duration': connection_duration,
                'failed_login_attempts': failed_login_attempts,
                'data_transfer_rate': data_transfer_rate,
                'access_frequency': access_frequency
            }
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            # Return default features on error
            return {
                'packet_size': 0.0,
                'protocol_type': 0.0,
                'connection_duration': 0.0,
                'failed_login_attempts': 0.0,
                'data_transfer_rate': 0.0,
                'access_frequency': 0.0
            }
    
    def record_failed_login(self, src_ip: str):
        """
        Record a failed login attempt (called by signature detector)
        
        Args:
            src_ip: Source IP address
        """
        self.login_tracker.record_failed_attempt(src_ip)
    
    def end_connection(self, src_ip: str, dst_ip: str, dst_port: int) -> Optional[float]:
        """
        End a connection and return its duration
        
        Args:
            src_ip: Source IP address
            dst_ip: Destination IP address
            dst_port: Destination port
            
        Returns:
            Final connection duration in seconds
        """
        return self.connection_tracker.end_connection(src_ip, dst_ip, dst_port)
    
    def get_feature_names(self) -> List[str]:
        """
        Get list of feature names in order
        
        Returns:
            List of feature names
        """
        return [
            'packet_size',
            'protocol_type',
            'connection_duration',
            'failed_login_attempts',
            'data_transfer_rate',
            'access_frequency'
        ]