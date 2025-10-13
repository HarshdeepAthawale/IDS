const { Server } = require('socket.io');
const path = require('path');
const fs = require('fs').promises;

class WebSocketService {
  constructor(server) {
    this.io = new Server(server, {
      cors: {
        origin: "http://localhost:3000",
        methods: ["GET", "POST"]
      }
    });
    
    this.connectedClients = new Set();
    this.statsInterval = null;
    
    this.setupEventHandlers();
    this.startStatsBroadcast();
  }

  setupEventHandlers() {
    this.io.on('connection', (socket) => {
      console.log(`Client connected: ${socket.id}`);
      this.connectedClients.add(socket.id);

      // Send initial data to newly connected client
      this.sendInitialData(socket);

      socket.on('disconnect', () => {
        console.log(`Client disconnected: ${socket.id}`);
        this.connectedClients.delete(socket.id);
      });

      socket.on('request-stats', async () => {
        try {
          const stats = await this.getCurrentStats();
          socket.emit('stats-update', stats);
        } catch (error) {
          console.error('Error fetching stats for client:', error);
          socket.emit('error', { message: 'Failed to fetch statistics' });
        }
      });

      socket.on('request-alerts', async (data = {}) => {
        try {
          const alerts = await this.getRecentAlerts(data);
          socket.emit('alerts-data', alerts);
        } catch (error) {
          console.error('Error fetching alerts for client:', error);
          socket.emit('error', { message: 'Failed to fetch alerts' });
        }
      });
    });
  }

  async sendInitialData(socket) {
    try {
      // Send current stats
      const stats = await this.getCurrentStats();
      socket.emit('stats-update', stats);

      // Send recent alerts
      const alerts = await this.getRecentAlerts({ limit: 50 });
      socket.emit('alerts-data', alerts);

      console.log(`Initial data sent to client: ${socket.id}`);
    } catch (error) {
      console.error('Error sending initial data:', error);
      socket.emit('error', { message: 'Failed to load initial data' });
    }
  }

  startStatsBroadcast() {
    // Broadcast stats every 2 seconds to all connected clients
    this.statsInterval = setInterval(async () => {
      if (this.connectedClients.size > 0) {
        try {
          const stats = await this.getCurrentStats();
          this.io.emit('stats-update', stats);
        } catch (error) {
          console.error('Error broadcasting stats:', error);
        }
      }
    }, 2000);
  }

  async getCurrentStats() {
    try {
      const packetsPath = path.join(__dirname, '../data/packets.json');
      const alertsPath = path.join(__dirname, '../data/alerts.json');

      // Calculate packets per second from recent packets
      const packetsData = await this.readJsonFile(packetsPath);
      const recentPackets = packetsData.packets || [];
      const now = Date.now();
      const oneSecondAgo = now - 1000;
      
      const recentPacketCount = recentPackets.filter(p => 
        new Date(p.timestamp).getTime() > oneSecondAgo
      ).length;

      // Get total intrusions count
      const alertsData = await this.readJsonFile(alertsPath);
      const totalIntrusions = alertsData.alerts ? alertsData.alerts.length : 0;

      // Calculate top suspicious IPs from recent alerts (last hour)
      const oneHourAgo = now - (60 * 60 * 1000);
      const recentAlerts = (alertsData.alerts || []).filter(alert => 
        new Date(alert.timestamp).getTime() > oneHourAgo
      );

      const ipCounts = {};
      recentAlerts.forEach(alert => {
        ipCounts[alert.source_ip] = (ipCounts[alert.source_ip] || 0) + 1;
      });

      const topSuspiciousIPs = Object.entries(ipCounts)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 5)
        .map(([ip, count]) => ({ ip, count }));

      // Calculate traffic volume (MB per second)
      const totalBytes = recentPackets.reduce((sum, packet) => sum + (packet.size || 0), 0);
      const trafficMBPerSec = totalBytes / (1024 * 1024);

      return {
        packets_per_sec: recentPacketCount,
        total_intrusions: totalIntrusions,
        top_suspicious_ips: topSuspiciousIPs,
        traffic_mb_per_sec: parseFloat(trafficMBPerSec.toFixed(2)),
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      console.error('Error calculating stats:', error);
      return {
        packets_per_sec: 0,
        total_intrusions: 0,
        top_suspicious_ips: [],
        traffic_mb_per_sec: 0,
        timestamp: new Date().toISOString()
      };
    }
  }

  async getRecentAlerts(options = {}) {
    try {
      const alertsPath = path.join(__dirname, '../data/alerts.json');
      const alertsData = await this.readJsonFile(alertsPath);
      const alerts = alertsData.alerts || [];

      // Apply pagination
      const page = parseInt(options.page) || 1;
      const limit = parseInt(options.limit) || 50;
      const startIndex = (page - 1) * limit;
      const endIndex = startIndex + limit;

      // Apply severity filter
      let filteredAlerts = alerts;
      if (options.severity) {
        filteredAlerts = alerts.filter(alert => alert.severity === options.severity);
      }

      // Sort by timestamp (newest first)
      filteredAlerts.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

      return {
        alerts: filteredAlerts.slice(startIndex, endIndex),
        pagination: {
          page,
          limit,
          total: filteredAlerts.length,
          totalPages: Math.ceil(filteredAlerts.length / limit)
        }
      };
    } catch (error) {
      console.error('Error fetching alerts:', error);
      return { alerts: [], pagination: { page: 1, limit: 50, total: 0, totalPages: 0 } };
    }
  }

  async readJsonFile(filePath) {
    try {
      const data = await fs.readFile(filePath, 'utf8');
      return JSON.parse(data);
    } catch (error) {
      if (error.code === 'ENOENT') {
        // Return default structure if file doesn't exist
        return { alerts: [], packets: [] };
      }
      throw error;
    }
  }

  // Method to broadcast new alerts to all connected clients
  broadcastNewAlert(alert) {
    console.log(`Broadcasting new alert: ${alert.type} from ${alert.source_ip}`);
    this.io.emit('new-alert', {
      ...alert,
      timestamp: new Date().toISOString()
    });
  }

  // Method to broadcast packet stream (for visualization)
  broadcastPacketStream(packet) {
    this.io.emit('packet-stream', {
      ...packet,
      timestamp: new Date().toISOString()
    });
  }

  // Method to broadcast system status updates
  broadcastSystemStatus(status) {
    this.io.emit('system-status', {
      ...status,
      timestamp: new Date().toISOString()
    });
  }

  // Get connection statistics
  getConnectionStats() {
    return {
      connected_clients: this.connectedClients.size,
      is_broadcasting: this.statsInterval !== null,
      uptime: process.uptime()
    };
  }

  // Cleanup method
  destroy() {
    if (this.statsInterval) {
      clearInterval(this.statsInterval);
      this.statsInterval = null;
    }
    this.io.close();
    console.log('WebSocket service destroyed');
  }
}

module.exports = WebSocketService;
