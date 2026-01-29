"""
Real-time packet capture service using Scapy
Handles live packet capture, parsing, and queuing for analysis
"""

import threading
import queue
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from collections import deque
from scapy.all import *
from scapy.layers.inet import IP, TCP, UDP, ICMP
from scapy.layers.l2 import Ether, ARP
from scapy.layers.inet6 import IPv6
from scapy.packet import Packet

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

# EtherType to protocol name mapping
ETHERTYPE_MAP = {
    0x0800: 'IPv4',
    0x0806: 'ARP',
    0x86DD: 'IPv6',
    0x8847: 'MPLS',
    0x8848: 'MPLS',
}

class PacketSniffer:
    """
    Real-time packet capture service with queue-based processing
    """
    
    def __init__(self, config, packet_callback: Optional[Callable] = None, auto_start: bool = True):
        """
        Initialize packet sniffer
        
        Args:
            config: Configuration object with capture settings
            packet_callback: Optional callback function to process packets
            auto_start: Automatically start capture on initialization
        """
        self.config = config
        self.packet_callback = packet_callback
        self.packet_queue = queue.Queue(maxsize=10000)
        self.running = False
        self.capture_thread = None
        self.monitoring_thread = None
        self.interface = getattr(config, 'CAPTURE_INTERFACE', 'any')
        self.timeout = getattr(config, 'CAPTURE_TIMEOUT', 1)
        
        # Auto-retry settings
        self.retry_enabled = getattr(config, 'SNIFFER_RETRY_ENABLED', True)
        self.retry_interval = getattr(config, 'SNIFFER_RETRY_INTERVAL', 30)
        self.max_retries = getattr(config, 'SNIFFER_MAX_RETRIES', 10)
        self.retry_count = 0
        self.status_check_interval = getattr(config, 'SCAPY_STATUS_CHECK_INTERVAL', 30)
        
        # Statistics
        self.stats = {
            'total_packets': 0,
            'dropped_packets': 0,
            'start_time': None,
            'last_packet_time': None,
            'total_bytes': 0
        }
        
        # Capture health tracking
        self.capture_health_check_interval = getattr(config, 'CAPTURE_HEALTH_CHECK_INTERVAL', 30)  # seconds
        
        # Connection tracking for insider threat detection
        self.connections = {}  # {(src_ip, dst_ip, port): timestamp}
        self.last_connection_count = 0
        self.cleanup_thread = None
        self.connection_timeout = timedelta(minutes=5)  # 5 minute timeout instead of 1 hour
        
        # Recent packet tracking for current rate calculation
        self.recent_packet_timestamps = deque(maxlen=1000)  # Track last 1000 packet timestamps
        self.rate_window_seconds = 10  # Calculate rate over last 10 seconds
        
        logger.info(f"PacketSniffer initialized for interface: {self.interface}")
        
        # Auto-start if enabled
        if auto_start and getattr(config, 'SCAPY_AUTO_START', True):
            logger.info("🚀 Auto-starting Scapy packet capture...")
            time.sleep(getattr(config, 'SCAPY_AUTO_START_DELAY', 0))
            self.start_capture()
    
    def _normalize_protocol(self, protocol: Any) -> str:
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
            if protocol_upper in ['TCP', 'UDP', 'ICMP', 'ICMPV6', 'IPV6', 'IPV4', 'ARP', 'GRE', 'ESP', 'AH', 'OSPF', 'SCTP']:
                # Normalize casing
                if protocol_upper == 'ICMPV6':
                    return 'ICMPv6'
                elif protocol_upper == 'IPV6':
                    return 'IPv6'
                elif protocol_upper == 'IPV4':
                    return 'IPv4'
                else:
                    return protocol_upper
            # Handle ether type strings
            if protocol_upper.startswith('ETHER-'):
                ether_type = protocol_upper.replace('ETHER-', '')
                try:
                    ether_num = int(ether_type, 16) if '0x' in ether_type else int(ether_type)
                    return ETHERTYPE_MAP.get(ether_num, f'Ether-{ether_type}')
                except (ValueError, TypeError):
                    return f'Ether-{ether_type}'
            # Return as-is if it's a valid string
            return protocol_upper if protocol_upper else 'Other'
        
        # If it's a number, map it to protocol name
        if isinstance(protocol, (int, float)):
            protocol_num = int(protocol)
            return PROTOCOL_MAP.get(protocol_num, f'Protocol-{protocol_num}')
        
        # Fallback for unknown types
        try:
            protocol_str = str(protocol).upper().strip()
            return protocol_str if protocol_str else 'Other'
        except:
            return 'Other'
    
    def _parse_packet(self, packet: Packet) -> Optional[Dict[str, Any]]:
        """
        Parse a Scapy packet into a standardized format
        
        Args:
            packet: Scapy packet object
            
        Returns:
            Dictionary with parsed packet data or None if parsing fails
        """
        try:
            parsed = {
                'timestamp': datetime.utcnow(),
                'raw_size': len(packet),
                'protocol': 'Other',
                'src_ip': None,
                'dst_ip': None,
                'src_port': None,
                'dst_port': None,
                'flags': None,
                'payload_size': 0,
                'payload_preview': None
            }
            
            # Extract IP layer information
            if IP in packet:
                ip_layer = packet[IP]
                parsed['src_ip'] = ip_layer.src
                parsed['dst_ip'] = ip_layer.dst
                protocol_num = ip_layer.proto
                
                # Extract transport layer information
                if TCP in packet:
                    tcp_layer = packet[TCP]
                    parsed['src_port'] = tcp_layer.sport
                    parsed['dst_port'] = tcp_layer.dport
                    parsed['flags'] = tcp_layer.flags
                    parsed['protocol'] = 'TCP'
                    
                    # Extract payload
                    if tcp_layer.payload:
                        payload = bytes(tcp_layer.payload)
                        parsed['payload_size'] = len(payload)
                        # Preview first 100 bytes of payload
                        parsed['payload_preview'] = payload[:100].hex()
                        
                elif UDP in packet:
                    udp_layer = packet[UDP]
                    parsed['src_port'] = udp_layer.sport
                    parsed['dst_port'] = udp_layer.dport
                    parsed['protocol'] = 'UDP'
                    
                    # Extract payload
                    if udp_layer.payload:
                        payload = bytes(udp_layer.payload)
                        parsed['payload_size'] = len(payload)
                        parsed['payload_preview'] = payload[:100].hex()
                        
                elif ICMP in packet:
                    parsed['protocol'] = 'ICMP'
                    icmp_layer = packet[ICMP]
                    parsed['flags'] = str(icmp_layer.type)
                else:
                    # IP packet without recognized transport layer - normalize protocol number
                    parsed['protocol'] = self._normalize_protocol(protocol_num)
                    
            # Handle IPv6 packets
            elif IPv6 in packet:
                ipv6_layer = packet[IPv6]
                parsed['src_ip'] = ipv6_layer.src
                parsed['dst_ip'] = ipv6_layer.dst
                protocol_num = ipv6_layer.nh  # Next header field
                
                # Check for ICMPv6 (protocol number 58)
                if protocol_num == 58:
                    parsed['protocol'] = 'ICMPv6'
                    # Try to extract ICMPv6 layer - check for any ICMPv6 message type
                    try:
                        # Check for common ICMPv6 layer types by iterating through packet layers
                        for layer in packet.layers():
                            layer_name = layer.__name__
                            if 'ICMPv6' in layer_name:
                                icmpv6_layer = packet[layer]
                                # Try to get type field
                                if hasattr(icmpv6_layer, 'type'):
                                    parsed['flags'] = str(icmpv6_layer.type)
                                elif hasattr(icmpv6_layer, 'code'):
                                    parsed['flags'] = str(icmpv6_layer.code)
                                else:
                                    parsed['flags'] = 'unknown'
                                break
                        else:
                            # No ICMPv6 layer found, use protocol number
                            parsed['flags'] = '58'
                    except Exception as e:
                        logger.debug(f"Could not extract ICMPv6 details: {e}")
                        parsed['flags'] = 'unknown'
                elif TCP in packet:
                    tcp_layer = packet[TCP]
                    parsed['src_port'] = tcp_layer.sport
                    parsed['dst_port'] = tcp_layer.dport
                    parsed['protocol'] = 'TCP'
                elif UDP in packet:
                    udp_layer = packet[UDP]
                    parsed['src_port'] = udp_layer.sport
                    parsed['dst_port'] = udp_layer.dport
                    parsed['protocol'] = 'UDP'
                else:
                    # IPv6 packet without recognized transport layer
                    parsed['protocol'] = self._normalize_protocol(protocol_num)
                    
            # Handle ARP packets
            elif ARP in packet:
                parsed['protocol'] = 'ARP'
                arp_layer = packet[ARP]
                parsed['src_ip'] = arp_layer.psrc
                parsed['dst_ip'] = arp_layer.pdst
                
            elif Ether in packet:
                # Handle non-IP traffic
                ether_layer = packet[Ether]
                ether_type = ether_layer.type
                # Map ethertype to protocol name
                protocol_name = ETHERTYPE_MAP.get(ether_type, f'Ether-{hex(ether_type)}')
                parsed['protocol'] = self._normalize_protocol(protocol_name)
            else:
                # Unknown packet type
                parsed['protocol'] = 'Other'
            
            # Ensure protocol is always normalized to a string
            parsed['protocol'] = self._normalize_protocol(parsed['protocol'])
            
            # Extract application layer data for analysis
            self._extract_application_data(packet, parsed)
            
            return parsed
            
        except Exception as e:
            logger.warning(f"Error parsing packet: {e}")
            return None
    
    def _extract_application_data(self, packet: Packet, parsed: Dict[str, Any]):
        """
        Extract application layer data for enhanced analysis
        
        Args:
            packet: Scapy packet object
            parsed: Parsed packet dictionary to update
        """
        try:
            # HTTP analysis
            if TCP in packet and packet[TCP].dport in [80, 8080, 8000]:
                payload = bytes(packet[TCP].payload) if packet[TCP].payload else b''
                if payload.startswith(b'GET') or payload.startswith(b'POST') or payload.startswith(b'PUT'):
                    # Extract HTTP headers
                    try:
                        http_data = payload.decode('utf-8', errors='ignore')
                        lines = http_data.split('\r\n')
                        if lines:
                            parsed['http_method'] = lines[0].split()[0] if len(lines[0].split()) > 0 else None
                            
                            # Extract User-Agent
                            for line in lines:
                                if line.lower().startswith('user-agent:'):
                                    parsed['user_agent'] = line.split(':', 1)[1].strip()
                                    break
                                    
                            # Extract URI
                            if len(lines[0].split()) > 1:
                                parsed['uri'] = lines[0].split()[1]
                    except:
                        pass
            
            # DNS analysis
            elif UDP in packet and packet[UDP].dport == 53:
                parsed['dns_query'] = True
                
            # SSH analysis
            elif TCP in packet and packet[TCP].dport == 22:
                parsed['ssh_connection'] = True
                
            # FTP analysis
            elif TCP in packet and packet[TCP].dport in [21, 20]:
                parsed['ftp_connection'] = True
                
        except Exception as e:
            logger.debug(f"Error extracting application data: {e}")
    
    def _packet_handler(self, packet: Packet):
        """
        Handle individual packets from Scapy sniff
        
        Args:
            packet: Scapy packet object
        """
        try:
            # Update statistics
            current_time = datetime.utcnow()
            self.stats['total_packets'] += 1
            self.stats['total_bytes'] += len(packet)
            self.stats['last_packet_time'] = current_time
            
            # Track recent packet timestamp for current rate calculation
            self.recent_packet_timestamps.append(current_time)
            
            # Reset retry count on successful packet capture
            if self.retry_count > 0:
                self.retry_count = 0
                logger.info("[PacketSniffer] Capture recovered successfully - packets are now being received")
            
            # Parse packet
            parsed_packet = self._parse_packet(packet)
            if not parsed_packet:
                return
            
            # Log packet capture (every 100 packets to avoid spam)
            if self.stats['total_packets'] % 100 == 0:
                logger.debug(f"Packet captured from {parsed_packet.get('src_ip', 'unknown')} to {parsed_packet.get('dst_ip', 'unknown')}")
            
            # Update connection tracking for ALL packets (before whitelist check)
            # This ensures browser traffic (HTTP/HTTPS) is tracked for the dashboard
            self._update_connection_tracking(parsed_packet)
            
            # Check if packet should be whitelisted (skip deep analysis but still track connections)
            is_whitelisted = self._is_whitelisted(parsed_packet)
            
            # Only skip queue processing and callback for whitelisted packets
            # Connection tracking and statistics already happened above
            if not is_whitelisted:
                # Add to queue for analysis (only non-whitelisted packets)
                try:
                    self.packet_queue.put_nowait(parsed_packet)
                except queue.Full:
                    self.stats['dropped_packets'] += 1
                    logger.warning("Packet queue is full, dropping packet")
                
                # Call callback if provided
                if self.packet_callback:
                    try:
                        self.packet_callback(parsed_packet)
                    except Exception as e:
                        logger.error(f"Error in packet callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error in packet handler: {e}")
    
    def _is_whitelisted(self, packet_data: Dict[str, Any]) -> bool:
        """
        Check if packet should be whitelisted based on configuration
        
        Args:
            packet_data: Parsed packet data
            
        Returns:
            True if packet should be whitelisted
        """
        try:
            src_ip = packet_data.get('src_ip')
            dst_ip = packet_data.get('dst_ip')
            dst_port = packet_data.get('dst_port')
            protocol = packet_data.get('protocol')
            
            # Check whitelist IPs
            whitelist_ips = getattr(self.config, 'WHITELIST_IPS', [])
            for whitelist_ip in whitelist_ips:
                if src_ip and self._ip_in_network(src_ip, whitelist_ip):
                    return True
                if dst_ip and self._ip_in_network(dst_ip, whitelist_ip):
                    return True
            
            # Check whitelist ports (configurable, defaults to empty to track all traffic)
            whitelist_ports = getattr(self.config, 'WHITELIST_PORTS', [])
            # Convert to list of strings for comparison
            if isinstance(whitelist_ports, str):
                whitelist_ports = [p.strip() for p in whitelist_ports.split(',') if p.strip()]
            elif not isinstance(whitelist_ports, list):
                whitelist_ports = []
            
            if dst_port and whitelist_ports and str(dst_port) in whitelist_ports:
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking whitelist: {e}")
            return False
    
    def _ip_in_network(self, ip: str, network: str) -> bool:
        """
        Check if IP is in the specified network
        
        Args:
            ip: IP address to check
            network: Network in CIDR notation (e.g., '192.168.0.0/16')
            
        Returns:
            True if IP is in network
        """
        try:
            import ipaddress
            return ipaddress.ip_address(ip) in ipaddress.ip_network(network)
        except:
            # Fallback to simple string matching for basic cases
            if '/' in network:
                network_base = network.split('/')[0]
                return ip.startswith(network_base.rsplit('.', 1)[0] + '.')
            return ip == network
    
    def _update_connection_tracking(self, packet_data: Dict[str, Any]):
        """
        Update connection tracking for insider threat detection
        
        Args:
            packet_data: Parsed packet data
        """
        try:
            src_ip = packet_data.get('src_ip')
            dst_ip = packet_data.get('dst_ip')
            dst_port = packet_data.get('dst_port')
            protocol = packet_data.get('protocol')
            
            if src_ip and dst_ip and dst_port:
                connection_key = (src_ip, dst_ip, dst_port)
                current_time = datetime.utcnow()
                
                # Update connection timestamp (always update on each packet)
                self.connections[connection_key] = current_time
                
        except Exception as e:
            logger.debug(f"Error updating connection tracking: {e}")
    
    def _cleanup_stale_connections(self):
        """
        Remove stale connections that haven't been active recently
        Called periodically to ensure inactive connections are removed
        """
        try:
            current_time = datetime.utcnow()
            cutoff_time = current_time - self.connection_timeout
            
            before_count = len(self.connections)
            
            # Remove connections older than timeout
            self.connections = {
                k: v for k, v in self.connections.items() 
                if v > cutoff_time
            }
            
            after_count = len(self.connections)
            removed_count = before_count - after_count
            
            if removed_count > 0:
                logger.debug(f"Cleaned up {removed_count} stale connections (timeout: {self.connection_timeout.total_seconds()}s)")
                
        except Exception as e:
            logger.debug(f"Error cleaning up stale connections: {e}")
    
    def _cleanup_loop(self):
        """
        Periodic cleanup loop running in separate thread
        Cleans up stale connections every 30 seconds
        """
        while self.running:
            try:
                time.sleep(30)  # Run every 30 seconds
                if self.running:
                    self._cleanup_stale_connections()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                time.sleep(30)  # Wait before retrying
    
    def start_capture(self):
        """
        Start packet capture in a separate thread with auto-retry
        """
        if self.running:
            logger.warning("Packet capture is already running")
            return
        
        self.running = True
        self.stats['start_time'] = datetime.utcnow()
        
        # Start capture thread
        self.capture_thread = threading.Thread(
            target=self._capture_loop_with_retry,
            name="PacketCapture",
            daemon=True
        )
        self.capture_thread.start()
        
        # Start monitoring thread if retry is enabled
        if self.retry_enabled and not self.monitoring_thread:
            self.monitoring_thread = threading.Thread(
                target=self._monitor_status,
                name="PacketCaptureMonitor",
                daemon=True
            )
            self.monitoring_thread.start()
            logger.info(f"Started status monitoring (checking every {self.status_check_interval}s)")
        
        # Start cleanup thread for stale connections
        if not self.cleanup_thread:
            self.cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                name="ConnectionCleanup",
                daemon=True
            )
            self.cleanup_thread.start()
            logger.info(f"Started connection cleanup thread (running every 30s, timeout: {self.connection_timeout.total_seconds()}s)")
        
        logger.info("Scapy packet capture started - collecting logs")
    
    def stop_capture(self):
        """
        Stop packet capture
        """
        if not self.running:
            return
        
        self.running = False
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=5)
        
        logger.info("Packet capture stopped")
    
    def _capture_loop_with_retry(self):
        """
        Capture loop with automatic retry on failure
        """
        while self.retry_enabled and self.retry_count < self.max_retries:
            try:
                self._capture_loop()
                # If we exit normally, break
                break
            except Exception as e:
                logger.error(f"Capture loop error: {e}")
                if self.retry_count < self.max_retries:
                    self.retry_count += 1
                    wait_time = min(5 * (2 ** (self.retry_count - 1)), 60)  # Exponential backoff, max 60s
                    logger.info(f"Retrying Scapy initialization... (attempt {self.retry_count}/{self.max_retries}) - waiting {wait_time}s")
                    time.sleep(wait_time)
                    self.running = True  # Reset running flag for retry
                else:
                    logger.error(f"Max retries ({self.max_retries}) reached. Stopping capture attempts.")
                    self.running = False
                    break
        else:
            # If retry is disabled or max retries reached, just run once
            if not self.retry_enabled:
                self._capture_loop()
    
    def _capture_loop(self):
        """
        Main capture loop running in separate thread
        """
        try:
            # Check if we have permission to capture
            if not self._check_capture_permissions():
                import platform
                is_windows = platform.system() == 'Windows'
                logger.error("=" * 60)
                logger.error("PERMISSION ERROR: Insufficient privileges for packet capture")
                logger.error("=" * 60)
                if is_windows:
                    logger.error("SOLUTION 1: Run PowerShell as Administrator, then execute:")
                    logger.error("  cd backend")
                    logger.error("  python app.py")
                    logger.error("")
                    logger.error("SOLUTION 2: Use the admin start script:")
                    logger.error("  Right-click start_backend_admin.ps1 -> Run as Administrator")
                else:
                    logger.error("SOLUTION 1: Run with sudo privileges:")
                    logger.error("  cd backend")
                    logger.error("  sudo python app.py")
                    logger.error("")
                    logger.error("SOLUTION 2: Grant capabilities (recommended for development):")
                    logger.error("  sudo setcap cap_net_raw,cap_net_admin=eip $(which python3)")
                    logger.error("  Then run: python app.py")
                logger.error("")
                logger.error("NOTE: System will continue in analysis-only mode")
                logger.error("Manual packet analysis via API will still work")
                logger.error("=" * 60)
                return
            
            # Auto-detect interface if 'any' is specified
            if self.interface == 'any':
                self.interface = self._get_best_interface()
                logger.info(f"Auto-selected interface: {self.interface}")
            
            logger.info(f"[PacketSniffer] Starting continuous packet capture on interface: {self.interface}")
            logger.info(f"[PacketSniffer] Capture will run until stopped (no timeout)")
            
            # Start Scapy sniff with continuous capture (no timeout)
            # Use stop_filter to control when to stop instead of timeout-based restarts
            # This ensures continuous packet capture without interruptions
            sniff(
                iface=self.interface,
                prn=self._packet_handler,
                store=0,  # Don't store packets in memory
                stop_filter=lambda x: not self.running  # Stop when running becomes False
            )
            
        except Exception as e:
            logger.error(f"Error in capture loop: {e}")
            import platform
            is_windows = platform.system() == 'Windows'
            
            if "Permission denied" in str(e) or "Operation not permitted" in str(e) or "WinError 10013" in str(e):
                logger.error("=" * 60)
                logger.error("PERMISSION ERROR: Packet capture requires elevated privileges")
                logger.error(f"Error details: {str(e)}")
                logger.error("=" * 60)
                if is_windows:
                    logger.error("SOLUTION 1: Run PowerShell as Administrator, then execute:")
                    logger.error("  cd backend")
                    logger.error("  python app.py")
                    logger.error("")
                    logger.error("SOLUTION 2: Use the admin start script:")
                    logger.error("  Right-click start_backend_admin.ps1 -> Run as Administrator")
                else:
                    logger.error("SOLUTION 1: Run with sudo privileges:")
                    logger.error("  cd backend")
                    logger.error("  sudo python app.py")
                    logger.error("")
                    logger.error("SOLUTION 2: Grant capabilities (recommended for development):")
                    logger.error("  sudo setcap cap_net_raw,cap_net_admin=eip $(which python3)")
                    logger.error("  Then run: python app.py")
                logger.error("")
                logger.error("NOTE: System will continue in analysis-only mode")
                logger.error("Manual packet analysis via API will still work")
                logger.error("=" * 60)
            elif "No such device" in str(e) or "Interface not found" in str(e):
                logger.error("=" * 60)
                logger.error(f"INTERFACE ERROR: Interface '{self.interface}' not found")
                logger.error(f"Error details: {str(e)}")
                logger.error("=" * 60)
                logger.error("Available network interfaces:")
                try:
                    from scapy.all import get_if_list
                    interfaces = get_if_list()
                    if interfaces:
                        for iface in interfaces:
                            logger.error(f"  - {iface}")
                    else:
                        logger.error("  (No interfaces found)")
                except Exception as iface_error:
                    logger.error(f"  (Could not list interfaces: {iface_error})")
                logger.error("")
                logger.error("SOLUTION: Set CAPTURE_INTERFACE in .env file to a valid interface")
                logger.error("Example: CAPTURE_INTERFACE=eth0")
                logger.error("=" * 60)
            else:
                logger.error("=" * 60)
                logger.error(f"CAPTURE ERROR: Unexpected error during packet capture")
                logger.error(f"Error type: {type(e).__name__}")
                logger.error(f"Error message: {str(e)}")
                logger.error("=" * 60)
                logger.error("Please check:")
                logger.error("  1. Network interface is valid and accessible")
                logger.error("  2. Required permissions are available (sudo/admin)")
                logger.error("  3. Scapy is properly installed: pip install scapy")
                logger.error("  4. Backend logs for additional details")
                logger.error("=" * 60)
        finally:
            self.running = False
    
    def _get_best_interface(self) -> str:
        """
        Auto-detect the best network interface for packet capture
        
        Returns:
            Best interface name for packet capture
        """
        try:
            from scapy.all import get_if_list, get_if_addr
            
            interfaces = get_if_list()
            logger.info(f"Available interfaces: {interfaces}")
            
            # Prefer non-loopback interfaces
            for iface in interfaces:
                if 'Loopback' not in iface and 'lo' not in iface.lower():
                    try:
                        addr = get_if_addr(iface)
                        if addr and addr != '127.0.0.1':
                            logger.info(f"Selected interface: {iface} (IP: {addr})")
                            return iface
                    except:
                        continue
            
            # Fallback to first available interface
            if interfaces:
                logger.info(f"Using fallback interface: {interfaces[0]}")
                return interfaces[0]
            
            # Last resort
            return 'any'
            
        except Exception as e:
            logger.warning(f"Error detecting interface: {e}")
            return 'any'
    
    def _check_capture_permissions(self) -> bool:
        """
        Check if we have sufficient permissions for packet capture
        """
        try:
            # Try to create a test socket to check permissions
            import socket
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
            test_socket.close()
            return True
        except PermissionError:
            import platform
            is_windows = platform.system() == 'Windows'
            logger.debug("Insufficient permissions for packet capture (expected without admin)")
            if is_windows:
                logger.debug("TIP: Run as Administrator or use start_backend_admin.ps1")
            else:
                logger.debug("TIP: Run with sudo to enable packet capture")
            return False
        except Exception as e:
            logger.warning(f"Permission check failed: {e}")
            return False
    
    def _check_capture_permissions_old(self) -> bool:
        """
        Check if we have sufficient permissions for packet capture
        
        Returns:
            True if permissions are sufficient
        """
        try:
            # Try to create a socket to check permissions
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
            s.close()
            return True
        except PermissionError:
            return False
        except Exception:
            return True  # Assume OK if we can't test
    
    def get_packet(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        Get a packet from the queue for processing
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Packet data or None if timeout
        """
        try:
            return self.packet_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def ensure_running(self):
        """
        Ensure packet capture is running, restart if stopped
        """
        if not self.running:
            logger.warning("WARNING: Scapy capture stopped, attempting restart...")
            self.start_capture()
        elif not self.capture_thread or not self.capture_thread.is_alive():
            logger.warning("WARNING: Scapy capture thread died, attempting restart...")
            self.running = False
            self.start_capture()
    
    def _monitor_status(self):
        """
        Monitor Scapy status and auto-restart if needed
        """
        while self.retry_enabled:
            try:
                time.sleep(self.status_check_interval)
                
                # Check if capture thread is alive
                if self.running and (not self.capture_thread or not self.capture_thread.is_alive()):
                    logger.warning("Scapy capture thread stopped unexpectedly, restarting...")
                    self.running = False
                    if self.retry_count < self.max_retries:
                        self.start_capture()
                
                # Log periodic status with capture health check
                stats = self.get_stats()
                total_packets = stats.get('total_packets', 0)
                
                if total_packets > 0 and total_packets % 1000 == 0:
                    logger.info(f"[PacketSniffer] Active: {total_packets} packets captured, "
                              f"rate: {stats.get('packet_rate', 0):.2f} pps, "
                              f"connections: {stats.get('active_connections', 0)}")
                elif total_packets == 0 and self.running:
                    # Log warning if running but no packets received
                    last_packet_age = stats.get('last_packet_age_seconds')
                    if last_packet_age and last_packet_age > 30:
                        logger.warning(f"[PacketSniffer] Running but no packets captured for {last_packet_age:.1f} seconds")
                        capture_warning = stats.get('capture_warning')
                        if capture_warning:
                            logger.warning(f"[PacketSniffer] {capture_warning}")
                    
            except Exception as e:
                logger.error(f"Error in status monitoring: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get capture statistics
        
        Returns:
            Dictionary with capture statistics
        """
        stats = self.stats.copy()
        stats['queue_size'] = self.packet_queue.qsize()
        
        # Clean up stale connections before getting count
        self._cleanup_stale_connections()
        stats['active_connections'] = len(self.connections)
        stats['running'] = self.running
        stats['retry_count'] = self.retry_count
        
        # Calculate current packet rate based on recent packets (last N seconds)
        current_time = datetime.utcnow()
        window_start = current_time - timedelta(seconds=self.rate_window_seconds)
        
        # Count packets in the recent window
        recent_packet_count = sum(
            1 for ts in self.recent_packet_timestamps 
            if ts > window_start
        )
        
        # Calculate current rate (packets per second)
        if self.rate_window_seconds > 0:
            stats['packet_rate'] = recent_packet_count / self.rate_window_seconds
        else:
            stats['packet_rate'] = 0
        
        # Debug logging for packet rate calculation
        logger.debug(f"[PacketSniffer] get_stats: packet_rate={stats['packet_rate']:.2f}, recent_count={recent_packet_count}, window={self.rate_window_seconds}s, total_packets={stats['total_packets']}, running={self.running}")
        
        # Calculate byte rate (total bytes / runtime for now, could be improved)
        if stats['start_time']:
            runtime = (current_time - stats['start_time']).total_seconds()
            if runtime > 0:
                stats['byte_rate'] = stats.get('total_bytes', 0) / runtime
            else:
                stats['byte_rate'] = 0
        else:
            stats['byte_rate'] = 0
        
        # Capture health verification
        last_packet_time = stats.get('last_packet_time')
        if last_packet_time:
            age_seconds = (current_time - last_packet_time).total_seconds()
            stats['last_packet_age_seconds'] = age_seconds
            
            # Consider capture unhealthy if no packets received for longer than health check interval
            # and sniffer is supposedly running
            if self.running and age_seconds > self.capture_health_check_interval:
                stats['capture_healthy'] = False
                stats['capture_warning'] = f"No packets captured for {age_seconds:.1f} seconds. Packet capture may not be working. Check permissions or interface."
            else:
                stats['capture_healthy'] = True
                stats['capture_warning'] = None
        else:
            # Never received any packets
            if stats['start_time']:
                age_seconds = (current_time - stats['start_time']).total_seconds()
                stats['last_packet_age_seconds'] = age_seconds
                if self.running and age_seconds > self.capture_health_check_interval:
                    stats['capture_healthy'] = False
                    stats['capture_warning'] = f"Packet capture started {age_seconds:.1f} seconds ago but no packets received. Check permissions: run with sudo (Linux) or as Administrator (Windows)."
                else:
                    stats['capture_healthy'] = None  # Too early to tell
                    stats['capture_warning'] = None
            else:
                stats['last_packet_age_seconds'] = None
                stats['capture_healthy'] = None
                stats['capture_warning'] = None
            
        return stats
    
    def get_connections(self) -> Dict[tuple, datetime]:
        """
        Get current active connections
        
        Returns:
            Dictionary of connection tuples to timestamps
        """
        return self.connections.copy()
