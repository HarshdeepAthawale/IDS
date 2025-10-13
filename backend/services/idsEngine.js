const storage = require('../utils/storage');
const { generateId, validateAlert, alertTypes, severityLevels } = require('../models/schemas');

class IDSEngine {
  constructor() {
    this.isRunning = false;
    this.analysisInterval = 5000; // Analyze every 5 seconds
    this.analysisTimer = null;
    
    // Detection state tracking
    this.ipPacketCounts = new Map(); // IP -> { count, firstSeen, lastSeen }
    this.ipPortAccess = new Map(); // IP -> Set of ports accessed
    this.ipVolumeCounts = new Map(); // IP -> { bytes, firstSeen, lastSeen }
    
    // Alert deduplication
    this.recentAlerts = new Map(); // IP+type -> timestamp
    
    // Configuration
    this.config = {
      dos: {
        threshold: parseInt(process.env.DOS_THRESHOLD_PACKETS_PER_SEC) || 100,
        timeWindow: parseInt(process.env.DOS_TIME_WINDOW_MS) || 60000, // 1 minute
        severity: 'high'
      },
      port_scan: {
        threshold: parseInt(process.env.PORT_SCAN_THRESHOLD_PORTS) || 20,
        timeWindow: parseInt(process.env.PORT_SCAN_TIME_WINDOW_MS) || 10000, // 10 seconds
        severity: 'medium'
      },
      suspicious_volume: {
        threshold: parseInt(process.env.SUSPICIOUS_VOLUME_THRESHOLD_MB) || 10,
        timeWindow: parseInt(process.env.SUSPICIOUS_VOLUME_TIME_WINDOW_MS) || 5000, // 5 seconds
        severity: 'medium'
      },
      deduplicationWindow: parseInt(process.env.ALERT_DEDUPLICATION_WINDOW_MS) || 60000 // 1 minute
    };
  }

  /**
   * Start the IDS engine
   */
  async start(webSocketService = null) {
    if (this.isRunning) {
      console.log('⚠️  IDS Engine is already running');
      return false;
    }

    console.log('🚀 Starting IDS Engine...');
    console.log('📊 Detection thresholds:');
    console.log(`  - DoS: ${this.config.dos.threshold} packets/sec in ${this.config.dos.timeWindow}ms`);
    console.log(`  - Port Scan: ${this.config.port_scan.threshold} ports in ${this.config.port_scan.timeWindow}ms`);
    console.log(`  - Suspicious Volume: ${this.config.suspicious_volume.threshold}MB in ${this.config.suspicious_volume.timeWindow}ms`);

    // Store WebSocket service reference
    this.webSocketService = webSocketService;

    this.isRunning = true;
    this.startAnalysisTimer();
    
    console.log('✅ IDS Engine started successfully');
    return true;
  }

  /**
   * Stop the IDS engine
   */
  async stop() {
    if (!this.isRunning) {
      console.log('⚠️  IDS Engine is not running');
      return false;
    }

    console.log('🛑 Stopping IDS Engine...');

    if (this.analysisTimer) {
      clearInterval(this.analysisTimer);
      this.analysisTimer = null;
    }

    this.isRunning = false;
    console.log('✅ IDS Engine stopped successfully');
    return true;
  }

  /**
   * Start the analysis timer
   */
  startAnalysisTimer() {
    this.analysisTimer = setInterval(async () => {
      try {
        await this.analyzePackets();
        await this.cleanupOldData();
      } catch (error) {
        console.error('❌ Error in IDS analysis:', error);
      }
    }, this.analysisInterval);
  }

  /**
   * Analyze recent packets for threats
   */
  async analyzePackets() {
    try {
      const packets = await storage.getPackets();
      const now = Date.now();
      
      // Get packets from last analysis window
      const analysisWindow = Math.max(
        this.config.dos.timeWindow,
        this.config.port_scan.timeWindow,
        this.config.suspicious_volume.timeWindow
      );
      
      const recentPackets = packets.filter(packet => 
        packet.timestamp >= (now - analysisWindow)
      );

      if (recentPackets.length === 0) {
        return;
      }

      // Update tracking data
      this.updateTrackingData(recentPackets);

      // Run detection algorithms
      await this.detectDoS();
      await this.detectPortScan();
      await this.detectSuspiciousVolume();

    } catch (error) {
      console.error('❌ Error analyzing packets:', error);
    }
  }

  /**
   * Update tracking data structures
   */
  updateTrackingData(packets) {
    const now = Date.now();

    packets.forEach(packet => {
      const srcIP = packet.src_ip;
      
      // Update packet count tracking
      if (!this.ipPacketCounts.has(srcIP)) {
        this.ipPacketCounts.set(srcIP, {
          count: 0,
          firstSeen: packet.timestamp,
          lastSeen: packet.timestamp
        });
      }
      
      const packetData = this.ipPacketCounts.get(srcIP);
      packetData.count++;
      packetData.lastSeen = packet.timestamp;

      // Update port access tracking
      if (packet.src_port && packet.dst_port) {
        if (!this.ipPortAccess.has(srcIP)) {
          this.ipPortAccess.set(srcIP, new Set());
        }
        this.ipPortAccess.get(srcIP).add(packet.dst_port);
      }

      // Update volume tracking
      if (!this.ipVolumeCounts.has(srcIP)) {
        this.ipVolumeCounts.set(srcIP, {
          bytes: 0,
          firstSeen: packet.timestamp,
          lastSeen: packet.timestamp
        });
      }
      
      const volumeData = this.ipVolumeCounts.get(srcIP);
      volumeData.bytes += packet.size || 0;
      volumeData.lastSeen = packet.timestamp;
    });
  }

  /**
   * Detect DoS attacks based on packet rate
   */
  async detectDoS() {
    const now = Date.now();
    const threshold = this.config.dos.threshold;
    const timeWindow = this.config.dos.timeWindow;

    for (const [srcIP, data] of this.ipPacketCounts) {
      const timeDiff = (now - data.firstSeen) / 1000; // seconds
      const packetsPerSecond = data.count / timeDiff;

      if (packetsPerSecond > threshold && timeDiff >= 1) {
        const alertKey = `${srcIP}_dos`;
        
        if (!this.isDuplicateAlert(alertKey)) {
          await this.createAlert({
            type: 'dos',
            source_ip: srcIP,
            severity: this.config.dos.severity,
            description: `High packet rate detected: ${packetsPerSecond.toFixed(2)} packets/sec`,
            details: {
              packets_per_second: packetsPerSecond,
              packet_count: data.count,
              time_window: timeDiff,
              threshold: threshold
            }
          });
          
          this.recentAlerts.set(alertKey, now);
        }
      }
    }
  }

  /**
   * Detect port scan attacks
   */
  async detectPortScan() {
    const now = Date.now();
    const threshold = this.config.port_scan.threshold;
    const timeWindow = this.config.port_scan.timeWindow;

    for (const [srcIP, ports] of this.ipPortAccess) {
      const portCount = ports.size;
      
      if (portCount > threshold) {
        const alertKey = `${srcIP}_port_scan`;
        
        if (!this.isDuplicateAlert(alertKey)) {
          await this.createAlert({
            type: 'port_scan',
            source_ip: srcIP,
            severity: this.config.port_scan.severity,
            description: `Port scan detected: ${portCount} unique ports accessed`,
            details: {
              unique_ports: portCount,
              ports: Array.from(ports).slice(0, 20), // Show first 20 ports
              threshold: threshold,
              time_window: timeWindow
            }
          });
          
          this.recentAlerts.set(alertKey, now);
        }
      }
    }
  }

  /**
   * Detect suspicious traffic volume
   */
  async detectSuspiciousVolume() {
    const now = Date.now();
    const threshold = this.config.suspicious_volume.threshold * 1024 * 1024; // Convert MB to bytes
    const timeWindow = this.config.suspicious_volume.timeWindow;

    for (const [srcIP, data] of this.ipVolumeCounts) {
      const timeDiff = (now - data.firstSeen) / 1000; // seconds
      const bytesPerSecond = data.bytes / timeDiff;
      const mbPerSecond = bytesPerSecond / (1024 * 1024);

      if (bytesPerSecond > threshold && timeDiff >= 1) {
        const alertKey = `${srcIP}_suspicious_volume`;
        
        if (!this.isDuplicateAlert(alertKey)) {
          await this.createAlert({
            type: 'suspicious_volume',
            source_ip: srcIP,
            severity: this.config.suspicious_volume.severity,
            description: `Suspicious traffic volume: ${mbPerSecond.toFixed(2)} MB/sec`,
            details: {
              bytes_per_second: bytesPerSecond,
              mb_per_second: mbPerSecond,
              total_bytes: data.bytes,
              time_window: timeDiff,
              threshold_mb: this.config.suspicious_volume.threshold
            }
          });
          
          this.recentAlerts.set(alertKey, now);
        }
      }
    }
  }

  /**
   * Create and save an alert
   */
  async createAlert(alertData) {
    try {
      const alert = {
        id: generateId(),
        timestamp: Date.now(),
        type: alertData.type,
        severity: alertData.severity,
        source_ip: alertData.source_ip,
        description: alertData.description,
        details: alertData.details,
        status: 'active'
      };

      // Validate alert
      const errors = validateAlert(alert);
      if (errors.length > 0) {
        console.error('❌ Invalid alert data:', errors);
        return false;
      }

      // Save alert
      const success = await storage.saveAlert(alert);
      if (success) {
        console.log(`🚨 Alert created: ${alert.type.toUpperCase()} from ${alert.source_ip} (${alert.severity})`);
        
        // Emit WebSocket event if available
        this.emitAlertEvent(alert);
        
        return true;
      } else {
        console.error('❌ Failed to save alert');
        return false;
      }
    } catch (error) {
      console.error('❌ Error creating alert:', error);
      return false;
    }
  }

  /**
   * Emit alert event via WebSocket
   */
  emitAlertEvent(alert) {
    try {
      if (this.webSocketService) {
        this.webSocketService.broadcastNewAlert(alert);
        console.log(`📡 Alert broadcasted via WebSocket: ${alert.type} from ${alert.source_ip}`);
      }
    } catch (error) {
      console.error('❌ Error broadcasting alert via WebSocket:', error);
    }
  }

  /**
   * Emit packet stream event via WebSocket
   */
  emitPacketStream(packet) {
    try {
      if (this.webSocketService) {
        this.webSocketService.broadcastPacketStream(packet);
      }
    } catch (error) {
      console.error('❌ Error broadcasting packet stream via WebSocket:', error);
    }
  }

  /**
   * Check if alert is duplicate
   */
  isDuplicateAlert(alertKey) {
    const now = Date.now();
    const lastAlert = this.recentAlerts.get(alertKey);
    
    if (lastAlert && (now - lastAlert) < this.config.deduplicationWindow) {
      return true;
    }
    
    return false;
  }

  /**
   * Clean up old tracking data
   */
  async cleanupOldData() {
    const now = Date.now();
    const maxAge = Math.max(
      this.config.dos.timeWindow,
      this.config.port_scan.timeWindow,
      this.config.suspicious_volume.timeWindow
    ) * 2; // Keep data for 2x the analysis window

    // Clean up packet counts
    for (const [srcIP, data] of this.ipPacketCounts) {
      if (now - data.lastSeen > maxAge) {
        this.ipPacketCounts.delete(srcIP);
      }
    }

    // Clean up port access
    for (const [srcIP, ports] of this.ipPortAccess) {
      // Get the last seen time from packet counts or volume counts
      const packetData = this.ipPacketCounts.get(srcIP);
      const volumeData = this.ipVolumeCounts.get(srcIP);
      const lastSeen = packetData?.lastSeen || volumeData?.lastSeen;
      
      if (lastSeen && (now - lastSeen > maxAge)) {
        this.ipPortAccess.delete(srcIP);
      }
    }

    // Clean up volume counts
    for (const [srcIP, data] of this.ipVolumeCounts) {
      if (now - data.lastSeen > maxAge) {
        this.ipVolumeCounts.delete(srcIP);
      }
    }

    // Clean up recent alerts
    for (const [alertKey, timestamp] of this.recentAlerts) {
      if (now - timestamp > this.config.deduplicationWindow) {
        this.recentAlerts.delete(alertKey);
      }
    }
  }

  /**
   * Get engine status
   */
  getStatus() {
    return {
      isRunning: this.isRunning,
      analysisInterval: this.analysisInterval,
      config: this.config,
      trackingStats: {
        ipPacketCounts: this.ipPacketCounts.size,
        ipPortAccess: this.ipPortAccess.size,
        ipVolumeCounts: this.ipVolumeCounts.size,
        recentAlerts: this.recentAlerts.size
      }
    };
  }

  /**
   * Update configuration
   */
  updateConfig(newConfig) {
    this.config = { ...this.config, ...newConfig };
    console.log('⚙️  IDS Engine configuration updated');
  }

  /**
   * Reset all tracking data
   */
  resetTrackingData() {
    this.ipPacketCounts.clear();
    this.ipPortAccess.clear();
    this.ipVolumeCounts.clear();
    this.recentAlerts.clear();
    console.log('🔄 IDS Engine tracking data reset');
  }
}

// Create singleton instance
const idsEngine = new IDSEngine();

module.exports = idsEngine;
