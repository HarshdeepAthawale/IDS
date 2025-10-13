const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const { createServer } = require('http');
const packetCaptureService = require('./services/packetCapture');
const idsEngine = require('./services/idsEngine');
const WebSocketService = require('./services/websocket');

// Load environment variables
dotenv.config();

const app = express();
const server = createServer(app);

// Middleware
app.use(cors({
  origin: process.env.FRONTEND_URL || "http://localhost:3000",
  credentials: true
}));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Routes
const apiRoutes = require('./routes/api');
app.use('/api', apiRoutes);

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Error:', err);
  res.status(500).json({ 
    error: 'Internal Server Error',
    message: process.env.NODE_ENV === 'development' ? err.message : 'Something went wrong'
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({ error: 'Route not found' });
});

// Initialize WebSocket service
const webSocketService = new WebSocketService(server);

// Make WebSocket service available to other modules
app.set('webSocketService', webSocketService);

// Connect WebSocket service to packet capture service
packetCaptureService.setWebSocketService(webSocketService);

const PORT = process.env.PORT || 5000;

// Initialize services
packetCaptureService.initialize().then((success) => {
  if (success) {
    console.log('✅ Packet capture service initialized');
  } else {
    console.log('⚠️  Packet capture service initialization failed - some features may not work');
  }
});

// Start IDS engine with WebSocket integration
idsEngine.start(webSocketService).then((success) => {
  if (success) {
    console.log('✅ IDS Engine started');
  } else {
    console.log('⚠️  IDS Engine failed to start');
  }
});

server.listen(PORT, () => {
  console.log(`🚀 IDS Backend Server running on port ${PORT}`);
  console.log(`📡 WebSocket server ready for connections`);
  console.log(`🌐 Health check: http://localhost:${PORT}/health`);
  console.log(`📊 API endpoints: http://localhost:${PORT}/api`);
  console.log(`🔗 WebSocket connection: ws://localhost:${PORT}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully');
  Promise.all([
    packetCaptureService.stopCapture(),
    idsEngine.stop(),
    webSocketService.destroy()
  ]).then(() => {
    server.close(() => {
      console.log('Process terminated');
    });
  });
});

process.on('SIGINT', () => {
  console.log('SIGINT received, shutting down gracefully');
  Promise.all([
    packetCaptureService.stopCapture(),
    idsEngine.stop(),
    webSocketService.destroy()
  ]).then(() => {
    server.close(() => {
      console.log('Process terminated');
    });
  });
});

module.exports = { app, server, webSocketService };
