const express = require('express');
const router = express.Router();

// Import controllers
const alertController = require('../controllers/alertController');
const statsController = require('../controllers/statsController');
const packetController = require('../controllers/packetController');

// Alert routes
router.get('/alerts', alertController.getAlerts);
router.get('/alerts/:id', alertController.getAlertById);
router.delete('/alerts/:id', alertController.deleteAlert);
router.delete('/alerts', alertController.clearAllAlerts);

// Statistics routes
router.get('/stats', statsController.getStats);
router.get('/stats/summary', statsController.getSummary);

// Packet routes
router.get('/packets', packetController.getPackets);
router.post('/packets', packetController.createPacket);
router.get('/packets/recent', packetController.getRecentPackets);

// System routes
router.get('/status', (req, res) => {
  res.json({
    status: 'operational',
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

module.exports = router;
