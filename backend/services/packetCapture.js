const pcap = require('pcap');
const storage = require('../utils/storage');
const { generateId, validatePacket } = require('../models/schemas');

class PacketCaptureService {
  constructor() {
    this.session = null;
    this.isCapturing = false;
    this.interfaces = [];
    this.packetBuffer = [];
    this.bufferSize = 100; // Buffer packets before saving
    this.saveInterval = 5000; // Save every 5 seconds
    this.saveTimer = null;
    this.webSocketService = null;
    this.streamPackets = false; // Whether to stream packets via WebSocket
  }

  /**
   * Initialize packet capture service
   */
  async initialize() {
    try {
      console.log('🔍 Initializing packet capture service...');
      
      // Get available network interfaces
      this.interfaces = pcap.findalldevs();
      console.log(`📡 Found ${this.interfaces.length} network interfaces`);
      
      // Log available interfaces
      this.interfaces.forEach((iface, index) => {
        console.log(`  ${index}: ${iface.name} - ${iface.description || 'No description'}`);
      });

      return true;
    } catch (error) {
      console.error('❌ Failed to initialize packet capture:', error.message);
      console.log('💡 Make sure Npcap or WinPcap is installed and you have administrator privileges');
      return false;
    }
  }

  /**
   * Start packet capture on specified interface
   */
  async startCapture(interfaceName = null, filter = '') {
    try {
      if (this.isCapturing) {
        console.log('⚠️  Packet capture is already running');
        return false;
      }

      // Select interface
      let selectedInterface = interfaceName;
      if (!selectedInterface) {
        // Auto-select first available interface
        if (this.interfaces.length === 0) {
          throw new Error('No network interfaces available');
        }
        selectedInterface = this.interfaces[0].name;
      }

      console.log(`🚀 Starting packet capture on interface: ${selectedInterface}`);
      console.log(`🔍 Filter: ${filter || 'none (capture all)'}`);

      // Create pcap session
      this.session = pcap.createSession(selectedInterface, filter);
      
      // Set up packet handler
      this.session.on('packet', (rawPacket) => {
        this.handlePacket(rawPacket);
      });

      // Start capturing
      this.session.on('error', (error) => {
        console.error('❌ Packet capture error:', error);
        this.stopCapture();
      });

      this.isCapturing = true;
      this.startBufferTimer();

      console.log('✅ Packet capture started successfully');
      return true;

    } catch (error) {
      console.error('❌ Failed to start packet capture:', error.message);
      
      if (error.message.includes('permission')) {
        console.log('💡 Try running with administrator privileges');
      } else if (error.message.includes('interface')) {
        console.log('💡 Check if the network interface exists');
      } else if (error.message.includes('pcap')) {
        console.log('💡 Make sure Npcap or WinPcap is installed');
      }
      
      return false;
    }
  }

  /**
   * Stop packet capture
   */
  async stopCapture() {
    try {
      if (!this.isCapturing) {
        console.log('⚠️  Packet capture is not running');
        return false;
      }

      console.log('🛑 Stopping packet capture...');

      // Stop buffer timer
      if (this.saveTimer) {
        clearInterval(this.saveTimer);
        this.saveTimer = null;
      }

      // Save remaining packets in buffer
      if (this.packetBuffer.length > 0) {
        await this.saveBufferedPackets();
      }

      // Close session
      if (this.session) {
        this.session.close();
        this.session = null;
      }

      this.isCapturing = false;
      console.log('✅ Packet capture stopped successfully');
      return true;

    } catch (error) {
      console.error('❌ Error stopping packet capture:', error);
      return false;
    }
  }

  /**
   * Handle incoming packet
   */
  handlePacket(rawPacket) {
    try {
      const parsedPacket = this.parsePacket(rawPacket);
      if (parsedPacket) {
        this.packetBuffer.push(parsedPacket);
        
        // Broadcast packet stream if enabled
        if (this.streamPackets && this.webSocketService) {
          this.webSocketService.broadcastPacketStream(parsedPacket);
        }
        
        // Save if buffer is full
        if (this.packetBuffer.length >= this.bufferSize) {
          this.saveBufferedPackets();
        }
      }
    } catch (error) {
      console.error('❌ Error handling packet:', error);
    }
  }

  /**
   * Parse raw packet into structured data
   */
  parsePacket(rawPacket) {
    try {
      const packet = pcap.decode.packet(rawPacket);
      
      // Extract basic packet info
      const timestamp = Date.now();
      const size = rawPacket.buf.length;

      // Parse Ethernet layer
      const ethernet = packet.payload;
      if (!ethernet) return null;

      // Parse IP layer
      const ip = ethernet.payload;
      if (!ip || !ip.saddr || !ip.daddr) return null;

      // Extract IP addresses
      const src_ip = this.formatIP(ip.saddr);
      const dst_ip = this.formatIP(ip.daddr);
      const protocol = this.getProtocolName(ip.protocol);

      // Parse transport layer (TCP/UDP)
      let src_port = null;
      let dst_port = null;
      let flags = '';

      if (ip.payload) {
        if (protocol === 'TCP') {
          src_port = ip.payload.sport;
          dst_port = ip.payload.dport;
          flags = this.parseTCPFlags(ip.payload.flags);
        } else if (protocol === 'UDP') {
          src_port = ip.payload.sport;
          dst_port = ip.payload.dport;
          flags = 'UDP';
        } else if (protocol === 'ICMP') {
          flags = 'ICMP';
        }
      }

      // Create packet object
      const parsedPacket = {
        id: generateId(),
        timestamp,
        src_ip,
        dst_ip,
        protocol,
        src_port,
        dst_port,
        size,
        flags,
        source: 'capture'
      };

      // Validate packet
      const errors = validatePacket(parsedPacket);
      if (errors.length > 0) {
        console.warn('⚠️  Invalid packet:', errors);
        return null;
      }

      return parsedPacket;

    } catch (error) {
      console.error('❌ Error parsing packet:', error);
      return null;
    }
  }

  /**
   * Format IP address from buffer
   */
  formatIP(ipBuffer) {
    if (!ipBuffer || ipBuffer.length !== 4) return '0.0.0.0';
    return Array.from(ipBuffer).join('.');
  }

  /**
   * Get protocol name from number
   */
  getProtocolName(protocolNumber) {
    const protocols = {
      1: 'ICMP',
      6: 'TCP',
      17: 'UDP',
      47: 'GRE',
      50: 'ESP',
      51: 'AH'
    };
    return protocols[protocolNumber] || `Unknown(${protocolNumber})`;
  }

  /**
   * Parse TCP flags
   */
  parseTCPFlags(flags) {
    const flagNames = [];
    if (flags & 0x01) flagNames.push('FIN');
    if (flags & 0x02) flagNames.push('SYN');
    if (flags & 0x04) flagNames.push('RST');
    if (flags & 0x08) flagNames.push('PSH');
    if (flags & 0x10) flagNames.push('ACK');
    if (flags & 0x20) flagNames.push('URG');
    return flagNames.join(',') || 'NONE';
  }

  /**
   * Start buffer timer for periodic saves
   */
  startBufferTimer() {
    this.saveTimer = setInterval(async () => {
      if (this.packetBuffer.length > 0) {
        await this.saveBufferedPackets();
      }
    }, this.saveInterval);
  }

  /**
   * Save buffered packets to storage
   */
  async saveBufferedPackets() {
    try {
      if (this.packetBuffer.length === 0) return;

      const packetsToSave = [...this.packetBuffer];
      this.packetBuffer = [];

      const success = await storage.savePackets(packetsToSave);
      if (success) {
        console.log(`💾 Saved ${packetsToSave.length} packets to storage`);
      } else {
        console.error('❌ Failed to save packets to storage');
      }
    } catch (error) {
      console.error('❌ Error saving buffered packets:', error);
    }
  }

  /**
   * Get capture status
   */
  getStatus() {
    return {
      isCapturing: this.isCapturing,
      interface: this.session ? this.session.device_name : null,
      bufferSize: this.packetBuffer.length,
      totalInterfaces: this.interfaces.length,
      interfaces: this.interfaces.map(iface => ({
        name: iface.name,
        description: iface.description
      }))
    };
  }

  /**
   * Get available interfaces
   */
  getInterfaces() {
    return this.interfaces.map(iface => ({
      name: iface.name,
      description: iface.description || 'No description'
    }));
  }

  /**
   * Set capture filter
   */
  setFilter(filter) {
    if (this.isCapturing) {
      console.log('⚠️  Cannot change filter while capturing. Stop capture first.');
      return false;
    }
    
    console.log(`🔍 Filter set to: ${filter}`);
    return true;
  }

  /**
   * Set WebSocket service for broadcasting
   */
  setWebSocketService(webSocketService) {
    this.webSocketService = webSocketService;
    console.log('📡 WebSocket service connected to packet capture');
  }

  /**
   * Enable/disable packet streaming via WebSocket
   */
  setPacketStreaming(enabled) {
    this.streamPackets = enabled;
    console.log(`📡 Packet streaming ${enabled ? 'enabled' : 'disabled'}`);
  }
}

// Create singleton instance
const packetCaptureService = new PacketCaptureService();

module.exports = packetCaptureService;
