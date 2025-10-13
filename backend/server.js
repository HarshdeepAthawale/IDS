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
  console.log('\n' + '='.repeat(60));
  console.log('🛡️  CUSTOM INTRUSION DETECTION SYSTEM');
  console.log('='.repeat(60));
  console.log(`🚀 Backend Server: http://localhost:${PORT}`);
  console.log(`📡 WebSocket Server: ws://localhost:${PORT}`);
  console.log(`🌐 Health Check: http://localhost:${PORT}/health`);
  console.log(`📊 API Endpoints: http://localhost:${PORT}/api`);
  console.log(`🖥️  Frontend Dashboard: http://localhost:3000`);
  console.log('='.repeat(60));
  console.log('✅ System ready for network monitoring!');
  console.log('💡 Run "npm run test" to verify all components');
  console.log('🔧 Check README.md for usage instructions');
  console.log('='.repeat(60) + '\n');
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
