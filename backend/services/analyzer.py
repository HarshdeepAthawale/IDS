"""
Packet analysis service with signature-based and ML-based anomaly detection
"""

import logging
import re
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from collections import defaultdict, deque
import pickle
import os

logger = logging.getLogger(__name__)

class SignatureDetector:
    """
    Signature-based detection engine
    """
    
    def __init__(self):
        """Initialize signature detector with attack patterns"""
        self.signatures = self._load_signatures()
        self.recent_packets = deque(maxlen=1000)  # Keep recent packets for context
        
    def _load_signatures(self) -> Dict[str, Dict[str, Any]]:
        """
        Load attack signatures
        
        Returns:
            Dictionary of signature patterns
        """
        return {
            'sql_injection': {
                'patterns': [
                    r"(union\s+select|select\s+.*\s+from|drop\s+table|delete\s+from)",
                    r"(or\s+1=1|and\s+1=1|'or\s+'1'='1)",
                    r"(information_schema|mysql\.user|sys\.databases)",
                    r"(script\s*>|<\s*script|javascript:|vbscript:)",
                ],
                'severity': 'high',
                'description': 'Potential SQL injection attempt detected'
            },
            'xss_attack': {
                'patterns': [
                    r"(<script[^>]*>.*?</script>|<script[^>]*/>)",
                    r"(javascript:|vbscript:|onload=|onerror=|onclick=)",
                    r"(document\.cookie|document\.location|window\.open)",
                    r"(eval\s*\(|setTimeout\s*\(|setInterval\s*\()",
                ],
                'severity': 'medium',
                'description': 'Potential XSS attack detected'
            },
            'port_scan': {
                'patterns': [
                    r"port_scan",  # Detected by connection pattern analysis
                ],
                'severity': 'medium',
                'description': 'Port scanning activity detected'
            },
            'dos_attack': {
                'patterns': [
                    r"dos_attack",  # Detected by packet rate analysis
                ],
                'severity': 'high',
                'description': 'Potential DoS attack detected'
            },
            'brute_force': {
                'patterns': [
                    r"brute_force",  # Detected by failed login attempts
                ],
                'severity': 'medium',
                'description': 'Brute force attack detected'
            },
            'malware_communication': {
                'patterns': [
                    r"(botnet|malware|trojan|virus)",
                    r"(cmd\.exe|powershell|wscript|cscript)",
                    r"(base64|decode|encrypt|payload)",
                ],
                'severity': 'critical',
                'description': 'Potential malware communication detected'
            },
            'data_exfiltration': {
                'patterns': [
                    r"(ftp|sftp|scp|rsync).*put|upload",
                    r"(large_data_transfer|bulk_download)",
                ],
                'severity': 'high',
                'description': 'Potential data exfiltration detected'
            }
        }
    
    def analyze_packet(self, packet_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze packet against signature patterns
        
        Args:
            packet_data: Parsed packet data
            
        Returns:
            Detection result or None if no threat
        """
        try:
            # Normalize timestamp to timezone-aware before storing
            if 'timestamp' in packet_data and packet_data['timestamp']:
                timestamp = packet_data['timestamp']
                if timestamp.tzinfo is None:
                    # Naive datetime - assume UTC and make it aware
                    packet_data['timestamp'] = timestamp.replace(tzinfo=timezone.utc)
            
            # Add packet to recent packets for context analysis
            self.recent_packets.append(packet_data)
            
            # Check payload patterns
            payload_preview = packet_data.get('payload_preview', '')
            if payload_preview:
                payload_hex = payload_preview
                try:
                    # Try to decode as ASCII for text-based attacks
                    payload_text = bytes.fromhex(payload_hex).decode('ascii', errors='ignore')
                except:
                    payload_text = ''
                
                # Check against signatures
                for sig_name, sig_data in self.signatures.items():
                    for pattern in sig_data['patterns']:
                        if re.search(pattern, payload_text, re.IGNORECASE):
                            return {
                                'type': 'signature',
                                'signature_id': sig_name,
                                'severity': sig_data['severity'],
                                'description': sig_data['description'],
                                'confidence': 0.8,
                                'matched_pattern': pattern,
                                'source': 'payload_analysis'
                            }
            
            # Check URI patterns for web attacks
            uri = packet_data.get('uri', '')
            if uri:
                for sig_name, sig_data in self.signatures.items():
                    for pattern in sig_data['patterns']:
                        if re.search(pattern, uri, re.IGNORECASE):
                            return {
                                'type': 'signature',
                                'signature_id': sig_name,
                                'severity': sig_data['severity'],
                                'description': sig_data['description'],
                                'confidence': 0.9,
                                'matched_pattern': pattern,
                                'source': 'uri_analysis'
                            }
            
            # Check HTTP method for suspicious patterns
            http_method = packet_data.get('http_method', '')
            if http_method and http_method.upper() in ['POST', 'PUT', 'DELETE']:
                # Check for suspicious user agents
                user_agent = packet_data.get('user_agent', '')
                if user_agent:
                    suspicious_agents = ['sqlmap', 'nikto', 'nmap', 'masscan', 'zap']
                    if any(agent in user_agent.lower() for agent in suspicious_agents):
                        return {
                            'type': 'signature',
                            'signature_id': 'suspicious_scanner',
                            'severity': 'medium',
                            'description': f'Suspicious scanner detected: {user_agent}',
                            'confidence': 0.7,
                            'matched_pattern': 'suspicious_user_agent',
                            'source': 'user_agent_analysis'
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error in signature analysis: {e}")
            return None
    
    def analyze_connection_pattern(self, packet_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze connection patterns for port scanning and DoS attacks
        
        Args:
            packet_data: Parsed packet data
            
        Returns:
            Detection result or None if no threat
        """
        try:
            src_ip = packet_data.get('src_ip')
            dst_port = packet_data.get('dst_port')
            protocol = packet_data.get('protocol')
            
            if not src_ip or not dst_port:
                return None
            
            # Analyze recent packets for patterns
            current_time = datetime.now(timezone.utc)
            recent_from_src = []
            for p in self.recent_packets:
                if p.get('src_ip') == src_ip:
                    packet_timestamp = p.get('timestamp')
                    if packet_timestamp:
                        # Ensure timestamp is timezone-aware
                        if packet_timestamp.tzinfo is None:
                            # Naive datetime - assume UTC
                            packet_timestamp = packet_timestamp.replace(tzinfo=timezone.utc)
                        time_diff = (current_time - packet_timestamp).total_seconds()
                        if time_diff < 60:
                            recent_from_src.append(p)
            
            # Check for port scanning (many different ports from same IP)
            unique_ports = set(p.get('dst_port') for p in recent_from_src if p.get('dst_port'))
            if len(unique_ports) > 10:  # Threshold for port scanning
                return {
                    'type': 'signature',
                    'signature_id': 'port_scan',
                    'severity': 'medium',
                    'description': f'Port scanning detected from {src_ip} to {len(unique_ports)} ports',
                    'confidence': 0.8,
                    'matched_pattern': 'port_scanning_pattern',
                    'source': 'connection_pattern_analysis'
                }
            
            # Check for DoS (high packet rate)
            packet_count = len(recent_from_src)
            if packet_count > 100:  # More than 100 packets in 60 seconds
                return {
                    'type': 'signature',
                    'signature_id': 'dos_attack',
                    'severity': 'high',
                    'description': f'High packet rate detected from {src_ip}: {packet_count} packets/minute',
                    'confidence': 0.9,
                    'matched_pattern': 'high_packet_rate',
                    'source': 'connection_pattern_analysis'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error in connection pattern analysis: {e}")
            return None


class AnomalyDetector:
    """
    ML-based anomaly detection using Isolation Forest
    """
    
    def __init__(self, config):
        """
        Initialize anomaly detector
        
        Args:
            config: Configuration object with ML settings
        """
        self.config = config
        self.model = IsolationForest(
            contamination=0.1,  # Expect 10% anomalies
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_data = deque(maxlen=10000)  # Store features for training
        self.model_path = 'anomaly_model.pkl'
        
        # Load existing model if available
        self._load_model()
        
    def _load_model(self):
        """Load existing trained model"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    self.model = model_data['model']
                    self.scaler = model_data['scaler']
                    self.is_trained = True
                    logger.info("Loaded existing anomaly detection model")
        except Exception as e:
            logger.warning(f"Could not load existing model: {e}")
    
    def _save_model(self):
        """Save trained model"""
        try:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'timestamp': datetime.now(timezone.utc)
            }
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
            logger.info("Saved anomaly detection model")
        except Exception as e:
            logger.error(f"Could not save model: {e}")
    
    def _extract_features(self, packet_data: Dict[str, Any]) -> List[float]:
        """
        Extract features from packet data for ML analysis
        
        Args:
            packet_data: Parsed packet data
            
        Returns:
            List of feature values
        """
        try:
            features = []
            
            # Basic packet features
            features.append(packet_data.get('payload_size', 0))
            features.append(packet_data.get('raw_size', 0))
            
            # Protocol encoding (one-hot like)
            protocol_map = {'TCP': 1, 'UDP': 2, 'ICMP': 3, 'unknown': 0}
            features.append(protocol_map.get(packet_data.get('protocol', 'unknown'), 0))
            
            # Port features
            features.append(packet_data.get('src_port', 0) or 0)
            features.append(packet_data.get('dst_port', 0) or 0)
            
            # TCP flags (if available)
            flags = packet_data.get('flags', 0)
            if isinstance(flags, (int, str)):
                features.append(int(str(flags), 16) if isinstance(flags, str) and '0x' in str(flags) else flags)
            else:
                features.append(0)
            
            # Time-based features
            timestamp = packet_data.get('timestamp', datetime.now(timezone.utc))
            if isinstance(timestamp, datetime):
                features.append(timestamp.hour)
                features.append(timestamp.minute)
                features.append(timestamp.weekday())
            
            # Payload characteristics
            payload_preview = packet_data.get('payload_preview', '')
            if payload_preview:
                # Entropy of payload
                hex_data = payload_preview
                byte_counts = defaultdict(int)
                for i in range(0, len(hex_data), 2):
                    if i + 1 < len(hex_data):
                        byte_counts[hex_data[i:i+2]] += 1
                
                entropy = 0
                total_bytes = len(byte_counts)
                if total_bytes > 0:
                    for count in byte_counts.values():
                        p = count / total_bytes
                        if p > 0:
                            entropy -= p * np.log2(p)
                features.append(entropy)
            else:
                features.append(0)
            
            # Ensure we always return the same number of features
            while len(features) < 10:
                features.append(0)
            
            return features[:10]  # Return exactly 10 features
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return [0] * 10
    
    def train_model(self):
        """
        Train the anomaly detection model
        """
        try:
            if len(self.feature_data) < self.config.MIN_SAMPLES_FOR_TRAINING:
                logger.info(f"Not enough data for training: {len(self.feature_data)} < {self.config.MIN_SAMPLES_FOR_TRAINING}")
                return False
            
            # Convert to numpy array
            features_array = np.array(list(self.feature_data))
            
            # Scale features
            features_scaled = self.scaler.fit_transform(features_array)
            
            # Train model
            self.model.fit(features_scaled)
            self.is_trained = True
            
            # Save model
            self._save_model()
            
            logger.info(f"Anomaly detection model trained with {len(self.feature_data)} samples")
            return True
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            return False
    
    def detect_anomaly(self, packet_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Detect anomalies in packet data
        
        Args:
            packet_data: Parsed packet data
            
        Returns:
            Detection result or None if no anomaly
        """
        try:
            # Extract features
            features = self._extract_features(packet_data)
            
            # Add to training data
            self.feature_data.append(features)
            
            # Train model if not trained and we have enough data
            if not self.is_trained and len(self.feature_data) >= self.config.MIN_SAMPLES_FOR_TRAINING:
                self.train_model()
            
            # If model is not trained, return None (no anomaly detection yet)
            if not self.is_trained:
                return None
            
            # Predict anomaly
            features_array = np.array(features).reshape(1, -1)
            features_scaled = self.scaler.transform(features_array)
            
            anomaly_score = self.model.decision_function(features_scaled)[0]
            is_anomaly = self.model.predict(features_scaled)[0] == -1
            
            # Convert anomaly score to confidence (0-1 scale)
            confidence = max(0, min(1, abs(anomaly_score)))
            
            # Check against threshold
            anomaly_score_threshold = getattr(self.config, 'ANOMALY_SCORE_THRESHOLD', 0.5)
            if is_anomaly and confidence > anomaly_score_threshold:
                return {
                    'type': 'anomaly',
                    'signature_id': 'ml_anomaly',
                    'severity': 'medium' if confidence < 0.8 else 'high',
                    'description': f'Anomalous traffic pattern detected (confidence: {confidence:.2f})',
                    'confidence': confidence,
                    'matched_pattern': 'ml_anomaly_detection',
                    'source': 'ml_analysis',
                    'anomaly_score': anomaly_score
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
            return None


class PacketAnalyzer:
    """
    Main packet analyzer combining signature, anomaly, and classification detection
    """
    
    def __init__(self, config):
        """
        Initialize packet analyzer
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.signature_detector = SignatureDetector()
        self.anomaly_detector = AnomalyDetector(config)
        self.last_model_training = datetime.now(timezone.utc)
        
        # Initialize classification detector if enabled
        self.classification_detector = None
        self.feature_extractor = None
        self.data_collector = None
        
        _ce = getattr(config, 'CLASSIFICATION_ENABLED', None) or (config.get('CLASSIFICATION_ENABLED') if hasattr(config, 'get') else None)
        classification_enabled = _ce is True or (isinstance(_ce, str) and _ce.lower() == 'true')
        if classification_enabled:
            try:
                from services.classifier import get_classification_detector
                from services.feature_extractor import FeatureExtractor
                self.classification_detector = get_classification_detector(config)
                self.feature_extractor = FeatureExtractor(config)
                logger.info("Classification detector enabled")
            except Exception as e:
                logger.warning(f"Could not initialize classification detector: {e}")
            try:
                from services.data_collector import DataCollector
                self.data_collector = DataCollector(config)
            except Exception as e:
                logger.debug(f"DataCollector not available (optional for SecIDS-CNN): {e}")
                self.data_collector = None
        
        logger.info("PacketAnalyzer initialized")
    
    def analyze_packet(self, packet_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze packet using signature, anomaly, and classification detection
        
        Args:
            packet_data: Parsed packet data
            
        Returns:
            List of detection results
        """
        detections = []
        
        try:
            # Signature-based detection
            sig_result = self.signature_detector.analyze_packet(packet_data)
            if sig_result:
                detections.append(sig_result)
                
                # Record failed login attempts for classification features
                if sig_result.get('signature_id') == 'brute_force' and self.feature_extractor:
                    src_ip = packet_data.get('src_ip')
                    if src_ip:
                        self.feature_extractor.record_failed_login(src_ip)
            
            # Connection pattern analysis
            pattern_result = self.signature_detector.analyze_connection_pattern(packet_data)
            if pattern_result:
                detections.append(pattern_result)
            
            # ML-based anomaly detection
            anomaly_result = self.anomaly_detector.detect_anomaly(packet_data)
            if anomaly_result:
                detections.append(anomaly_result)
            
            # Supervised classification detection
            if self.classification_detector and self.feature_extractor:
                try:
                    # Extract features for classification
                    packet_features = self.feature_extractor.extract_features(packet_data)
                    
                    # If model has stored feature names, ensure we provide features in correct format
                    # The classifier will handle padding/truncation automatically
                    features = packet_features
                    
                    # Classify packet
                    classification_result = self.classification_detector.classify(features)
                    
                    # If classified as malicious and confidence exceeds threshold
                    confidence_threshold = getattr(self.config, 'CLASSIFICATION_CONFIDENCE_THRESHOLD', 0.7)
                    if (classification_result.get('label') == 'malicious' and 
                        classification_result.get('confidence', 0) >= confidence_threshold):
                        
                        detections.append({
                            'type': 'classification',
                            'signature_id': 'ml_classification',
                            'severity': 'high' if classification_result.get('confidence', 0) > 0.9 else 'medium',
                            'description': f'Malicious traffic classified by ML model (confidence: {classification_result.get("confidence", 0):.2f})',
                            'confidence': classification_result.get('confidence', 0),
                            'matched_pattern': 'supervised_classification',
                            'source': 'classification_ml',
                            'classification_result': classification_result
                        })
                    
                    # Collect sample for training (auto-label based on signature detection)
                    if self.data_collector:
                        # Auto-label: if signature detected, label as malicious; otherwise benign
                        label = None
                        labeled_by = 'auto'
                        confidence = 0.5
                        
                        if sig_result or pattern_result or anomaly_result:
                            label = 'malicious'
                            confidence = 0.8
                        else:
                            label = 'benign'
                            confidence = 0.6
                        
                        self.data_collector.collect_sample(
                            features=features,
                            packet_data=packet_data,
                            label=label,
                            labeled_by=labeled_by,
                            confidence=confidence
                        )
                        
                except Exception as e:
                    logger.error(f"Error in classification detection: {e}")
            
            # Retrain model periodically
            model_retrain_interval = getattr(self.config, 'MODEL_RETRAIN_INTERVAL', 3600)
            if (datetime.now(timezone.utc) - self.last_model_training).total_seconds() > model_retrain_interval:
                self.anomaly_detector.train_model()
                self.last_model_training = datetime.now(timezone.utc)
            
            return detections
            
        except Exception as e:
            logger.error(f"Error in packet analysis: {e}")
            return []
    
    def get_model_stats(self) -> Dict[str, Any]:
        """
        Get model statistics
        
        Returns:
            Dictionary with model statistics
        """
        stats = {
            'is_trained': self.anomaly_detector.is_trained,
            'training_samples': len(self.anomaly_detector.feature_data),
            'last_training': self.last_model_training.isoformat(),
            'signature_count': len(self.signature_detector.signatures),
            'recent_packets': len(self.signature_detector.recent_packets)
        }
        
        # Add classification detector stats if enabled
        if self.classification_detector:
            classification_info = self.classification_detector.get_model_info()
            stats['classification'] = {
                'enabled': True,
                'is_trained': classification_info.get('is_trained', False),
                'model_type': classification_info.get('model_type', 'unknown')
            }
        else:
            stats['classification'] = {'enabled': False}
        
        return stats
