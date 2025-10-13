const packetCaptureService = require('../services/packetCapture');
const captureConfig = require('../config/capture');

/**
 * Get packet capture status
 */
const getCaptureStatus = async (req, res) => {
  try {
    const status = packetCaptureService.getStatus();
    res.json({
      ...status,
      timestamp: Date.now()
    });
  } catch (error) {
    console.error('Error getting capture status:', error);
    res.status(500).json({ error: 'Failed to get capture status' });
  }
};

/**
 * Start packet capture
 */
const startCapture = async (req, res) => {
  try {
    const { interface: interfaceName, filter } = req.body;
    
    // Validate filter if provided
    if (filter) {
      const validation = captureConfig.validateFilter(filter);
      if (!validation.valid) {
        return res.status(400).json({ 
          error: 'Invalid filter syntax', 
          details: validation.error 
        });
      }
    }
    
    const success = await packetCaptureService.startCapture(interfaceName, filter);
    
    if (success) {
      res.json({ 
        message: 'Packet capture started successfully',
        status: packetCaptureService.getStatus()
      });
    } else {
      res.status(400).json({ error: 'Failed to start packet capture' });
    }
  } catch (error) {
    console.error('Error starting capture:', error);
    res.status(500).json({ error: 'Failed to start packet capture' });
  }
};

/**
 * Stop packet capture
 */
const stopCapture = async (req, res) => {
  try {
    const success = await packetCaptureService.stopCapture();
    
    if (success) {
      res.json({ 
        message: 'Packet capture stopped successfully',
        status: packetCaptureService.getStatus()
      });
    } else {
      res.status(400).json({ error: 'Failed to stop packet capture' });
    }
  } catch (error) {
    console.error('Error stopping capture:', error);
    res.status(500).json({ error: 'Failed to stop packet capture' });
  }
};

/**
 * Get available network interfaces
 */
const getInterfaces = async (req, res) => {
  try {
    const interfaces = packetCaptureService.getInterfaces();
    res.json({
      interfaces,
      count: interfaces.length,
      timestamp: Date.now()
    });
  } catch (error) {
    console.error('Error getting interfaces:', error);
    res.status(500).json({ error: 'Failed to get network interfaces' });
  }
};

/**
 * Get available capture filters
 */
const getAvailableFilters = async (req, res) => {
  try {
    const filters = captureConfig.getAvailableFilters();
    const recommended = captureConfig.getRecommendedFilters();
    
    res.json({
      predefined_filters: filters,
      recommended_filters: recommended,
      timestamp: Date.now()
    });
  } catch (error) {
    console.error('Error getting filters:', error);
    res.status(500).json({ error: 'Failed to get available filters' });
  }
};

module.exports = {
  getCaptureStatus,
  startCapture,
  stopCapture,
  getInterfaces,
  getAvailableFilters
};
