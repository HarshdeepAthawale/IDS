const storage = require('../utils/storage');

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
      end_date 
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
    
    if (start_date) {
      const startTime = new Date(start_date).getTime();
      filteredAlerts = filteredAlerts.filter(alert => alert.timestamp >= startTime);
    }
    
    if (end_date) {
      const endTime = new Date(end_date).getTime();
      filteredAlerts = filteredAlerts.filter(alert => alert.timestamp <= endTime);
    }

    // Sort by timestamp (newest first)
    filteredAlerts.sort((a, b) => b.timestamp - a.timestamp);

    // Pagination
    const startIndex = (page - 1) * limit;
    const endIndex = startIndex + parseInt(limit);
    const paginatedAlerts = filteredAlerts.slice(startIndex, endIndex);

    res.json({
      alerts: paginatedAlerts,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total: filteredAlerts.length,
        pages: Math.ceil(filteredAlerts.length / limit)
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
 * Clear all alerts
 */
const clearAllAlerts = async (req, res) => {
  try {
    await storage.clearAllAlerts();
    res.json({ message: 'All alerts cleared successfully' });
  } catch (error) {
    console.error('Error clearing alerts:', error);
    res.status(500).json({ error: 'Failed to clear alerts' });
  }
};

module.exports = {
  getAlerts,
  getAlertById,
  deleteAlert,
  clearAllAlerts
};
