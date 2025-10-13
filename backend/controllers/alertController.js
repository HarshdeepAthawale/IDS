const storage = require('../utils/storage');
const { severityLevels, alertTypes } = require('../models/schemas');

/**
 * Get paginated alerts with optional filtering
 */
const getAlerts = async (req, res) => {
  try {
    const { 
      page = 1, 
      limit = 50, 
      severity, 
      type, 
      source_ip,
      start_date,
      end_date,
      status = 'active',
      sort = 'timestamp',
      order = 'desc'
    } = req.query;

    const alerts = await storage.getAlerts();
    
    // Apply filters
    let filteredAlerts = alerts;
    
    if (severity) {
      filteredAlerts = filteredAlerts.filter(alert => alert.severity === severity);
    }
    
    if (type) {
      filteredAlerts = filteredAlerts.filter(alert => alert.type === type);
    }
    
    if (source_ip) {
      filteredAlerts = filteredAlerts.filter(alert => alert.source_ip === source_ip);
    }
    
    if (status) {
      filteredAlerts = filteredAlerts.filter(alert => alert.status === status);
    }
    
    if (start_date) {
      const startTime = new Date(start_date).getTime();
      filteredAlerts = filteredAlerts.filter(alert => alert.timestamp >= startTime);
    }
    
    if (end_date) {
      const endTime = new Date(end_date).getTime();
      filteredAlerts = filteredAlerts.filter(alert => alert.timestamp <= endTime);
    }

    // Sort alerts
    filteredAlerts.sort((a, b) => {
      const aVal = a[sort];
      const bVal = b[sort];
      
      if (order === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

    // Pagination
    const startIndex = (page - 1) * limit;
    const endIndex = startIndex + parseInt(limit);
    const paginatedAlerts = filteredAlerts.slice(startIndex, endIndex);

    // Add metadata to alerts
    const alertsWithMetadata = paginatedAlerts.map(alert => ({
      ...alert,
      severity_info: severityLevels[alert.severity],
      type_info: alertTypes[alert.type],
      formatted_timestamp: new Date(alert.timestamp).toISOString()
    }));

    res.json({
      alerts: alertsWithMetadata,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total: filteredAlerts.length,
        pages: Math.ceil(filteredAlerts.length / limit)
      },
      filters: {
        severity,
        type,
        source_ip,
        status,
        start_date,
        end_date
      }
    });
  } catch (error) {
    console.error('Error getting alerts:', error);
    res.status(500).json({ error: 'Failed to retrieve alerts' });
  }
};

/**
 * Get a specific alert by ID
 */
const getAlertById = async (req, res) => {
  try {
    const { id } = req.params;
    const alerts = await storage.getAlerts();
    const alert = alerts.find(a => a.id === id);
    
    if (!alert) {
      return res.status(404).json({ error: 'Alert not found' });
    }
    
    res.json(alert);
  } catch (error) {
    console.error('Error getting alert by ID:', error);
    res.status(500).json({ error: 'Failed to retrieve alert' });
  }
};

/**
 * Delete a specific alert
 */
const deleteAlert = async (req, res) => {
  try {
    const { id } = req.params;
    const success = await storage.deleteAlert(id);
    
    if (!success) {
      return res.status(404).json({ error: 'Alert not found' });
    }
    
    res.json({ message: 'Alert deleted successfully' });
  } catch (error) {
    console.error('Error deleting alert:', error);
    res.status(500).json({ error: 'Failed to delete alert' });
  }
};

/**
 * Update alert status (acknowledge/resolve)
 */
const updateAlertStatus = async (req, res) => {
  try {
    const { id } = req.params;
    const { status, notes } = req.body;
    
    if (!status || !['active', 'acknowledged', 'resolved'].includes(status)) {
      return res.status(400).json({ 
        error: 'Invalid status. Must be active, acknowledged, or resolved' 
      });
    }
    
    const alerts = await storage.getAlerts();
    const alertIndex = alerts.findIndex(a => a.id === id);
    
    if (alertIndex === -1) {
      return res.status(404).json({ error: 'Alert not found' });
    }
    
    // Update alert
    alerts[alertIndex].status = status;
    alerts[alertIndex].updated_at = Date.now();
    if (notes) {
      alerts[alertIndex].notes = notes;
    }
    
    // Save updated alerts
    await storage.saveAlerts(alerts);
    
    res.json({ 
      message: 'Alert status updated successfully',
      alert: alerts[alertIndex]
    });
  } catch (error) {
    console.error('Error updating alert status:', error);
    res.status(500).json({ error: 'Failed to update alert status' });
  }
};

/**
 * Get alert statistics
 */
const getAlertStats = async (req, res) => {
  try {
    const { time_range = '24h' } = req.query;
    const alerts = await storage.getAlerts();
    
    const now = Date.now();
    let timeWindow;
    
    switch (time_range) {
      case '1h':
        timeWindow = 3600000; // 1 hour
        break;
      case '24h':
        timeWindow = 86400000; // 24 hours
        break;
      case '7d':
        timeWindow = 604800000; // 7 days
        break;
      case '30d':
        timeWindow = 2592000000; // 30 days
        break;
      default:
        timeWindow = 86400000; // Default to 24 hours
    }
    
    const recentAlerts = alerts.filter(a => a.timestamp >= (now - timeWindow));
    
    // Count by severity
    const severityCounts = {};
    Object.keys(severityLevels).forEach(severity => {
      severityCounts[severity] = recentAlerts.filter(a => a.severity === severity).length;
    });
    
    // Count by type
    const typeCounts = {};
    Object.keys(alertTypes).forEach(type => {
      typeCounts[type] = recentAlerts.filter(a => a.type === type).length;
    });
    
    // Count by status
    const statusCounts = {
      active: recentAlerts.filter(a => a.status === 'active').length,
      acknowledged: recentAlerts.filter(a => a.status === 'acknowledged').length,
      resolved: recentAlerts.filter(a => a.status === 'resolved').length
    };
    
    // Top source IPs
    const ipCounts = {};
    recentAlerts.forEach(alert => {
      ipCounts[alert.source_ip] = (ipCounts[alert.source_ip] || 0) + 1;
    });
    
    const topSourceIPs = Object.entries(ipCounts)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 10)
      .map(([ip, count]) => ({ ip, count }));
    
    res.json({
      time_range,
      total_alerts: recentAlerts.length,
      severity_counts: severityCounts,
      type_counts: typeCounts,
      status_counts: statusCounts,
      top_source_ips: topSourceIPs,
      timestamp: now
    });
  } catch (error) {
    console.error('Error getting alert stats:', error);
    res.status(500).json({ error: 'Failed to retrieve alert statistics' });
  }
};

/**
 * Clear all alerts
 */
const clearAllAlerts = async (req, res) => {
  try {
    const success = await storage.clearAllAlerts();
    
    if (success) {
      res.json({ message: 'All alerts cleared successfully' });
    } else {
      res.status(500).json({ error: 'Failed to clear alerts' });
    }
  } catch (error) {
    console.error('Error clearing alerts:', error);
    res.status(500).json({ error: 'Failed to clear alerts' });
  }
};

module.exports = {
  getAlerts,
  getAlertById,
  deleteAlert,
  updateAlertStatus,
  getAlertStats,
  clearAllAlerts
};