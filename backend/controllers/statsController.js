const storage = require('../utils/storage');

/**
 * Get real-time statistics
 */
const getStats = async (req, res) => {
  try {
    const [alerts, packets] = await Promise.all([
      storage.getAlerts(),
      storage.getPackets()
    ]);

    const now = Date.now();
    const oneMinuteAgo = now - 60000; // 1 minute ago
    const fiveMinutesAgo = now - 300000; // 5 minutes ago
    const oneHourAgo = now - 3600000; // 1 hour ago

    // Calculate packets per second (last minute)
    const recentPackets = packets.filter(p => p.timestamp >= oneMinuteAgo);
    const packetsPerSecond = recentPackets.length / 60;

    // Calculate traffic volume (last minute)
    const trafficBytes = recentPackets.reduce((sum, p) => sum + (p.size || 0), 0);
    const trafficMBPerSecond = (trafficBytes / 1024 / 1024) / 60;

    // Count alerts by severity (last 5 minutes)
    const recentAlerts = alerts.filter(a => a.timestamp >= fiveMinutesAgo);
    const alertCounts = {
      low: recentAlerts.filter(a => a.severity === 'low').length,
      medium: recentAlerts.filter(a => a.severity === 'medium').length,
      high: recentAlerts.filter(a => a.severity === 'high').length,
      critical: recentAlerts.filter(a => a.severity === 'critical').length
    };

    // Get top suspicious IPs (last 5 minutes)
    const ipCounts = {};
    recentAlerts.forEach(alert => {
      ipCounts[alert.source_ip] = (ipCounts[alert.source_ip] || 0) + 1;
    });
    
    const topSuspiciousIPs = Object.entries(ipCounts)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 10)
      .map(([ip, count]) => ({ ip, alert_count: count }));

    // Calculate total intrusions
    const totalIntrusions = alerts.length;

    // Active threats (alerts in last 5 minutes)
    const activeThreats = recentAlerts.length;

    // Protocol distribution (last hour)
    const hourlyPackets = packets.filter(p => p.timestamp >= oneHourAgo);
    const protocolCounts = {};
    hourlyPackets.forEach(packet => {
      protocolCounts[packet.protocol] = (protocolCounts[packet.protocol] || 0) + 1;
    });

    const topProtocols = Object.entries(protocolCounts)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5)
      .map(([protocol, count]) => ({ protocol, count }));

    // Traffic trends (last hour, 5-minute intervals)
    const trafficTrends = [];
    for (let i = 0; i < 12; i++) {
      const intervalStart = oneHourAgo + (i * 300000); // 5-minute intervals
      const intervalEnd = intervalStart + 300000;
      const intervalPackets = packets.filter(p => p.timestamp >= intervalStart && p.timestamp < intervalEnd);
      const intervalBytes = intervalPackets.reduce((sum, p) => sum + (p.size || 0), 0);
      
      trafficTrends.push({
        timestamp: intervalStart,
        packet_count: intervalPackets.length,
        bytes: intervalBytes,
        mb: intervalBytes / (1024 * 1024)
      });
    }

    res.json({
      packets_per_second: Math.round(packetsPerSecond * 100) / 100,
      traffic_mb_per_second: Math.round(trafficMBPerSecond * 100) / 100,
      total_intrusions: totalIntrusions,
      active_threats: activeThreats,
      alert_counts: alertCounts,
      top_suspicious_ips: topSuspiciousIPs,
      top_protocols: topProtocols,
      traffic_trends: trafficTrends,
      timestamp: now
    });
  } catch (error) {
    console.error('Error getting stats:', error);
    res.status(500).json({ error: 'Failed to retrieve statistics' });
  }
};

/**
 * Get summary statistics for dashboard
 */
const getSummary = async (req, res) => {
  try {
    const alerts = await storage.getAlerts();
    const now = Date.now();
    const oneHourAgo = now - 3600000; // 1 hour ago
    const oneDayAgo = now - 86400000; // 1 day ago

    const hourlyAlerts = alerts.filter(a => a.timestamp >= oneHourAgo);
    const dailyAlerts = alerts.filter(a => a.timestamp >= oneDayAgo);

    // Alert trends
    const alertTrends = {
      last_hour: hourlyAlerts.length,
      last_24_hours: dailyAlerts.length,
      total: alerts.length
    };

    // Most common attack types
    const attackTypes = {};
    dailyAlerts.forEach(alert => {
      attackTypes[alert.type] = (attackTypes[alert.type] || 0) + 1;
    });

    const topAttackTypes = Object.entries(attackTypes)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5)
      .map(([type, count]) => ({ type, count }));

    res.json({
      alert_trends: alertTrends,
      top_attack_types: topAttackTypes,
      timestamp: now
    });
  } catch (error) {
    console.error('Error getting summary:', error);
    res.status(500).json({ error: 'Failed to retrieve summary' });
  }
};

/**
 * Get historical statistics
 */
const getHistoricalStats = async (req, res) => {
  try {
    const { period = '24h', interval = '1h' } = req.query;
    const [alerts, packets] = await Promise.all([
      storage.getAlerts(),
      storage.getPackets()
    ]);

    const now = Date.now();
    let timeWindow;
    let intervalMs;

    // Parse period
    switch (period) {
      case '1h':
        timeWindow = 3600000;
        break;
      case '24h':
        timeWindow = 86400000;
        break;
      case '7d':
        timeWindow = 604800000;
        break;
      case '30d':
        timeWindow = 2592000000;
        break;
      default:
        timeWindow = 86400000;
    }

    // Parse interval
    switch (interval) {
      case '5m':
        intervalMs = 300000;
        break;
      case '15m':
        intervalMs = 900000;
        break;
      case '1h':
        intervalMs = 3600000;
        break;
      case '6h':
        intervalMs = 21600000;
        break;
      case '1d':
        intervalMs = 86400000;
        break;
      default:
        intervalMs = 3600000;
    }

    const startTime = now - timeWindow;
    const intervals = [];

    // Create time intervals
    for (let time = startTime; time < now; time += intervalMs) {
      const intervalEnd = Math.min(time + intervalMs, now);
      
      const intervalAlerts = alerts.filter(a => a.timestamp >= time && a.timestamp < intervalEnd);
      const intervalPackets = packets.filter(p => p.timestamp >= time && p.timestamp < intervalEnd);
      
      const intervalBytes = intervalPackets.reduce((sum, p) => sum + (p.size || 0), 0);
      
      intervals.push({
        timestamp: time,
        end_timestamp: intervalEnd,
        alerts: intervalAlerts.length,
        packets: intervalPackets.length,
        bytes: intervalBytes,
        mb: intervalBytes / (1024 * 1024),
        alert_counts: {
          low: intervalAlerts.filter(a => a.severity === 'low').length,
          medium: intervalAlerts.filter(a => a.severity === 'medium').length,
          high: intervalAlerts.filter(a => a.severity === 'high').length,
          critical: intervalAlerts.filter(a => a.severity === 'critical').length
        }
      });
    }

    res.json({
      period,
      interval,
      intervals,
      total_alerts: alerts.filter(a => a.timestamp >= startTime).length,
      total_packets: packets.filter(p => p.timestamp >= startTime).length,
      timestamp: now
    });
  } catch (error) {
    console.error('Error getting historical stats:', error);
    res.status(500).json({ error: 'Failed to retrieve historical statistics' });
  }
};

/**
 * Get system health metrics
 */
const getSystemHealth = async (req, res) => {
  try {
    const [alerts, packets, fileStats] = await Promise.all([
      storage.getAlerts(),
      storage.getPackets(),
      storage.getFileStats()
    ]);

    const now = Date.now();
    const oneHourAgo = now - 3600000;

    // Recent activity
    const recentAlerts = alerts.filter(a => a.timestamp >= oneHourAgo);
    const recentPackets = packets.filter(p => p.timestamp >= oneHourAgo);

    // Alert rate
    const alertRate = recentAlerts.length / 60; // alerts per minute

    // Packet rate
    const packetRate = recentPackets.length / 60; // packets per minute

    // System status
    const systemStatus = {
      status: 'healthy',
      alerts: {
        total: alerts.length,
        recent: recentAlerts.length,
        rate_per_minute: Math.round(alertRate * 100) / 100
      },
      packets: {
        total: packets.length,
        recent: recentPackets.length,
        rate_per_minute: Math.round(packetRate * 100) / 100
      },
      storage: fileStats,
      uptime: process.uptime(),
      memory_usage: process.memoryUsage(),
      timestamp: now
    };

    // Determine overall health status
    if (alertRate > 10) {
      systemStatus.status = 'warning';
    } else if (alertRate > 50) {
      systemStatus.status = 'critical';
    }

    res.json(systemStatus);
  } catch (error) {
    console.error('Error getting system health:', error);
    res.status(500).json({ error: 'Failed to retrieve system health' });
  }
};
