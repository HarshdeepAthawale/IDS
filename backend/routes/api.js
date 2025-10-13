const express = require('express');
const router = express.Router();

// Import controllers
const alertController = require('../controllers/alertController');
const statsController = require('../controllers/statsController');
const packetController = require('../controllers/packetController');
const captureController = require('../controllers/captureController');
const idsController = require('../controllers/idsController');

// Alert routes
router.get('/alerts', alertController.getAlerts);
router.get('/alerts/stats', alertController.getAlertStats);
router.get('/alerts/:id', alertController.getAlertById);
router.put('/alerts/:id', alertController.updateAlertStatus);
router.delete('/alerts/:id', alertController.deleteAlert);
router.delete('/alerts', alertController.clearAllAlerts);

// Statistics routes
router.get('/stats', statsController.getStats);
router.get('/stats/summary', statsController.getSummary);
router.get('/stats/historical', statsController.getHistoricalStats);
router.get('/stats/health', statsController.getSystemHealth);

// Packet routes
router.get('/packets', packetController.getPackets);
router.get('/packets/stats', packetController.getPacketStats);
router.get('/packets/export', packetController.exportPackets);
router.post('/packets', packetController.createPacket);
router.get('/packets/recent', packetController.getRecentPackets);

// Capture control routes
router.get('/capture/status', captureController.getCaptureStatus);
router.post('/capture/start', captureController.startCapture);
router.post('/capture/stop', captureController.stopCapture);
router.get('/capture/interfaces', captureController.getInterfaces);
router.get('/capture/filters', captureController.getAvailableFilters);

// IDS Engine control routes
router.get('/ids/status', idsController.getEngineStatus);
router.post('/ids/start', idsController.startEngine);
router.post('/ids/stop', idsController.stopEngine);
router.get('/ids/thresholds', idsController.getThresholds);
router.put('/ids/thresholds', idsController.updateThresholds);
router.post('/ids/reset', idsController.resetEngine);

// System routes
router.get('/status', (req, res) => {
  res.json({
    status: 'operational',
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

module.exports = router;
