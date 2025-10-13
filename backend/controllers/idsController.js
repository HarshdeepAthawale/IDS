const idsEngine = require('../services/idsEngine');
const { getThresholds: getThresholdConfig, updateThreshold, validateThreshold, getDetectionTypes } = require('../config/thresholds');

/**
 * Get IDS engine status
 */
const getEngineStatus = async (req, res) => {
  try {
    const status = idsEngine.getStatus();
    res.json({
      ...status,
      timestamp: Date.now()
    });
  } catch (error) {
    console.error('Error getting IDS engine status:', error);
    res.status(500).json({ error: 'Failed to get IDS engine status' });
  }
};

/**
 * Start IDS engine
 */
const startEngine = async (req, res) => {
  try {
    const success = await idsEngine.start();
    
    if (success) {
      res.json({ 
        message: 'IDS Engine started successfully',
        status: idsEngine.getStatus()
      });
    } else {
      res.status(400).json({ error: 'Failed to start IDS Engine' });
    }
  } catch (error) {
    console.error('Error starting IDS engine:', error);
    res.status(500).json({ error: 'Failed to start IDS Engine' });
  }
};

/**
 * Stop IDS engine
 */
const stopEngine = async (req, res) => {
  try {
    const success = await idsEngine.stop();
    
    if (success) {
      res.json({ 
        message: 'IDS Engine stopped successfully',
        status: idsEngine.getStatus()
      });
    } else {
      res.status(400).json({ error: 'Failed to stop IDS Engine' });
    }
  } catch (error) {
    console.error('Error stopping IDS engine:', error);
    res.status(500).json({ error: 'Failed to stop IDS Engine' });
  }
};

/**
 * Get detection thresholds
 */
const getThresholds = async (req, res) => {
  try {
    const thresholds = getThresholdConfig();
    const detectionTypes = getDetectionTypes();
    
    res.json({
      thresholds,
      detection_types: detectionTypes,
      timestamp: Date.now()
    });
  } catch (error) {
    console.error('Error getting thresholds:', error);
    res.status(500).json({ error: 'Failed to get detection thresholds' });
  }
};

/**
 * Update detection thresholds
 */
const updateThresholds = async (req, res) => {
  try {
    const { detectionType, config } = req.body;
    
    if (!detectionType || !config) {
      return res.status(400).json({ 
        error: 'Detection type and configuration are required' 
      });
    }
    
    // Validate configuration
    const errors = validateThreshold(detectionType, config);
    if (errors.length > 0) {
      return res.status(400).json({ 
        error: 'Invalid configuration', 
        details: errors 
      });
    }
    
    // Update threshold
    const success = updateThreshold(detectionType, config);
    if (!success) {
      return res.status(400).json({ 
        error: 'Invalid detection type' 
      });
    }
    
    // Update engine configuration
    idsEngine.updateConfig({ [detectionType]: config });
    
    res.json({ 
      message: 'Threshold updated successfully',
      detection_type: detectionType,
      config: config
    });
  } catch (error) {
    console.error('Error updating thresholds:', error);
    res.status(500).json({ error: 'Failed to update detection thresholds' });
  }
};

/**
 * Reset IDS engine
 */
const resetEngine = async (req, res) => {
  try {
    idsEngine.resetTrackingData();
    
    res.json({ 
      message: 'IDS Engine reset successfully',
      status: idsEngine.getStatus()
    });
  } catch (error) {
    console.error('Error resetting IDS engine:', error);
    res.status(500).json({ error: 'Failed to reset IDS Engine' });
  }
};

module.exports = {
  getEngineStatus,
  startEngine,
  stopEngine,
  getThresholds,
  updateThresholds,
  resetEngine
};
