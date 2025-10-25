"""
Real-time packet capture service using Scapy
Handles live packet capture, parsing, and queuing for analysis
"""

import threading
import queue
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from scapy.all import *
from scapy.layers.inet import IP, TCP, UDP, ICMP
from scapy.layers.l2 import Ether
from scapy.packet import Packet

logger = logging.getLogger(__name__)

class PacketSniffer:
    """
    Real-time packet capture service with queue-based processing
    """
    
    def __init__(self, config, packet_callback: Optional[Callable] = None):
        """
        Initialize packet sniffer
        
        Args:
            config: Configuration object with capture settings
            packet_callback: Optional callback function to process packets
        """
        self.config = config
        self.packet_callback = packet_callback
        self.packet_queue = queue.Queue(maxsize=10000)
        self.running = False
        self.capture_thread = None
        self.interface = getattr(config, 'CAPTURE_INTERFACE', 'any')
        self.timeout = getattr(config, 'CAPTURE_TIMEOUT', 1)
        
        # Statistics
        self.stats = {
            'total_packets': 0,
            'dropped_packets': 0,
            'start_time': None,
            'last_packet_time': None
        }
        
        # Connection tracking for insider threat detection
        self.connections = {}  # {(src_ip, dst_ip, port): timestamp}
        
        logger.info(f"PacketSniffer initialized for interface: {self.interface}")
    
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
                'protocol': 'unknown',
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
                parsed['protocol'] = ip_layer.proto
                
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
                    
            elif Ether in packet:
                # Handle non-IP traffic
                ether_layer = packet[Ether]
                parsed['protocol'] = f"Ether-{ether_layer.type}"
                
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
            self.stats['total_packets'] += 1
            self.stats['last_packet_time'] = datetime.utcnow()
            
            # Parse packet
            parsed_packet = self._parse_packet(packet)
            if not parsed_packet:
                return
            
            # Check if packet should be whitelisted
            if self._is_whitelisted(parsed_packet):
                return
            
            # Update connection tracking
            self._update_connection_tracking(parsed_packet)
            
            # Add to queue for analysis
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
            
            # Check whitelist ports
            whitelist_ports = ['80', '443', '53']  # HTTP, HTTPS, DNS
            if dst_port and str(dst_port) in whitelist_ports:
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
                
                # Clean old connections (older than 1 hour)
                cutoff_time = current_time - timedelta(hours=1)
                self.connections = {
                    k: v for k, v in self.connections.items() 
                    if v > cutoff_time
                }
                
                # Update connection
                self.connections[connection_key] = current_time
                
        except Exception as e:
            logger.debug(f"Error updating connection tracking: {e}")
    
    def start_capture(self):
        """
        Start packet capture in a separate thread
        """
        if self.running:
            logger.warning("Packet capture is already running")
            return
        
        self.running = True
        self.stats['start_time'] = datetime.utcnow()
        
        # Start capture thread
        self.capture_thread = threading.Thread(
            target=self._capture_loop,
            name="PacketCapture",
            daemon=True
        )
        self.capture_thread.start()
        
        logger.info("Packet capture started")
    
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
    
    def _capture_loop(self):
        """
        Main capture loop running in separate thread
        """
        try:
            # Check if we have permission to capture
            if not self._check_capture_permissions():
                logger.error("Insufficient permissions for packet capture. Run with elevated privileges.")
                logger.info("SOLUTION: Run PowerShell as Administrator and execute:")
                logger.info("  .\\start_backend_admin.ps1")
                logger.info("  OR")
                logger.info("  .\\START_BACKEND.bat")
                return
            
            # Auto-detect interface if 'any' is specified
            if self.interface == 'any':
                self.interface = self._get_best_interface()
                logger.info(f"Auto-selected interface: {self.interface}")
            
            logger.info(f"Starting packet capture on interface: {self.interface}")
            
            # Start Scapy sniff with Windows-specific handling
            sniff(
                iface=self.interface,
                prn=self._packet_handler,
                store=0,  # Don't store packets in memory
                timeout=self.timeout,
                stop_filter=lambda x: not self.running  # Stop when running becomes False
            )
            
        except Exception as e:
            logger.error(f"Error in capture loop: {e}")
            if "Permission denied" in str(e) or "Operation not permitted" in str(e) or "WinError 10013" in str(e):
                logger.error("Packet capture requires elevated privileges (run as Administrator)")
                logger.info("SOLUTION: Run PowerShell as Administrator and execute:")
                logger.info("  .\\start_backend_admin.ps1")
                logger.info("  OR")
                logger.info("  .\\START_BACKEND.bat")
            elif "No such device" in str(e) or "Interface not found" in str(e):
                logger.error(f"Interface '{self.interface}' not found")
                logger.info("Available interfaces:")
                try:
                    from scapy.all import get_if_list
                    for iface in get_if_list():
                        logger.info(f"  - {iface}")
                except:
                    pass
            else:
                logger.error(f"Capture error: {e}")
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
            logger.warning("Insufficient permissions for packet capture")
            logger.info("TIP: Run the application as Administrator to enable packet capture")
            logger.info("   Or use the start_backend_admin.ps1 script for automatic admin privileges")
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
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get capture statistics
        
        Returns:
            Dictionary with capture statistics
        """
        stats = self.stats.copy()
        stats['queue_size'] = self.packet_queue.qsize()
        stats['active_connections'] = len(self.connections)
        stats['running'] = self.running
        
        # Calculate rates
        if stats['start_time']:
            runtime = (datetime.utcnow() - stats['start_time']).total_seconds()
            if runtime > 0:
                stats['packet_rate'] = stats['total_packets'] / runtime
            else:
                stats['packet_rate'] = 0
        else:
            stats['packet_rate'] = 0
            
        return stats
    
    def get_connections(self) -> Dict[tuple, datetime]:
        """
        Get current active connections
        
        Returns:
            Dictionary of connection tuples to timestamps
        """
        return self.connections.copy()
