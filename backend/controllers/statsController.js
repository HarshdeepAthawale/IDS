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

    res.json({
      packets_per_second: Math.round(packetsPerSecond * 100) / 100,
      traffic_mb_per_second: Math.round(trafficMBPerSecond * 100) / 100,
      total_intrusions: totalIntrusions,
      active_threats: activeThreats,
      alert_counts: alertCounts,
      top_suspicious_ips: topSuspiciousIPs,
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

module.exports = {
  getStats,
  getSummary
};
