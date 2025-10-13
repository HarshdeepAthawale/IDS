# 🛡️ Custom Intrusion Detection System (IDS)

A comprehensive, real-time network intrusion detection system built with Node.js and Next.js, featuring packet capture, threat detection, and a modern web dashboard.

![IDS Dashboard](https://img.shields.io/badge/Status-Production%20Ready-green)
![Node.js](https://img.shields.io/badge/Node.js-16+-blue)
![Next.js](https://img.shields.io/badge/Next.js-14+-black)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [API Documentation](#-api-documentation)
- [Testing](#-testing)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

### 🎯 Core Detection Capabilities
- **DoS/DDoS Detection** - High packet rate monitoring
- **Port Scan Detection** - Multiple port access tracking
- **Suspicious Volume Detection** - Unusual data transfer monitoring
- **Real-time Alerting** - Instant threat notifications
- **Traffic Analysis** - Protocol and flow analysis

### 🖥️ Dashboard Features
- **Real-time Monitoring** - Live packet and alert streams
- **Interactive Charts** - Traffic patterns and statistics
- **Alert Management** - Filter, acknowledge, and resolve alerts
- **System Status** - Health monitoring and diagnostics
- **Network Flow Visualization** - Active connection tracking

### 🔧 Technical Features
- **Raw Packet Capture** - Direct network interface access
- **WebSocket Integration** - Real-time data streaming
- **RESTful API** - Complete programmatic access
- **Modular Architecture** - Extensible detection engines
- **Data Persistence** - JSON-based storage with rotation
- **Error Handling** - Comprehensive error management

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Network       │
│   (Next.js)     │◄──►│   (Node.js)     │◄──►│   Interface     │
│                 │    │                 │    │                 │
│ • Dashboard     │    │ • Packet Capture│    │ • Raw Packets   │
│ • Real-time UI  │    │ • IDS Engine    │    │ • BPF Filters   │
│ • Charts        │    │ • WebSocket     │    │ • Interface     │
│ • Alerts        │    │ • REST API      │    │   Monitoring    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Browser       │    │   Data Storage  │    │   Detection     │
│                 │    │                 │    │   Results       │
│ • Live Updates  │    │ • Packets JSON  │    │ • Alerts        │
│ • Notifications │    │ • Alerts JSON   │    │ • Statistics    │
│ • Responsive    │    │ • File Rotation │    │ • Metrics       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 Prerequisites

### System Requirements
- **Node.js** 16.0.0 or higher
- **npm** 8.0.0 or higher
- **Administrator/Root privileges** (required for packet capture)

### Platform-Specific Requirements

#### Windows
- **Npcap** or **WinPcap** installed
- Administrator privileges for packet capture
- Windows 10/11 recommended

#### Linux
- **libpcap** development libraries
- Root privileges or `CAP_NET_RAW` capability
- `sudo apt-get install libpcap-dev` (Ubuntu/Debian)

#### macOS
- **libpcap** development libraries
- Root privileges for packet capture
- `brew install libpcap`

## 📦 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd IDS
```

### 2. Install Backend Dependencies
```bash
cd backend
npm install
```

### 3. Install Frontend Dependencies
```bash
cd ../frontend
npm install
```

### 4. Environment Configuration
```bash
# Copy environment template
cp env.example .env

# Edit configuration
nano .env  # or your preferred editor
```

### 5. Create Data Directories
```bash
# Backend data directory
mkdir -p backend/data
mkdir -p backend/logs
```

## ⚙️ Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Server Configuration
PORT=5000
NODE_ENV=development
FRONTEND_URL=http://localhost:3000

# Packet Capture
CAPTURE_INTERFACE=any
CAPTURE_FILTER=

# Detection Thresholds
DOS_THRESHOLD_PACKETS_PER_SEC=100
PORT_SCAN_THRESHOLD_PORTS=20
SUSPICIOUS_VOLUME_THRESHOLD_MB=10

# Alert Configuration
ALERT_DEDUPLICATION_WINDOW_MS=60000
```

### Detection Thresholds

Customize detection sensitivity:

| Detection Type | Default Threshold | Description |
|----------------|------------------|-------------|
| DoS | 100 packets/sec | High packet rate detection |
| Port Scan | 20 ports | Multiple port access detection |
| Volume | 10 MB/sec | High data volume detection |

## 🚀 Usage

### Starting the System

#### 1. Start Backend Server
```bash
cd backend

# Development mode
npm run dev

# Production mode
npm start
```

**Important**: Run with administrator/root privileges for packet capture:
```bash
# Windows (PowerShell as Administrator)
sudo npm start

# Linux/macOS
sudo npm start
```

#### 2. Start Frontend Dashboard
```bash
cd frontend

# Development mode
npm run dev

# Production mode
npm run build
npm start
```

#### 3. Access the Dashboard
Open your browser and navigate to:
- **Dashboard**: http://localhost:3000
- **API**: http://localhost:5000/api
- **Health Check**: http://localhost:5000/health

### Basic Operations

#### Start Packet Capture
```bash
# Via API
curl -X POST http://localhost:5000/api/packets/start \
  -H "Content-Type: application/json" \
  -d '{"interface": "any", "filter": ""}'

# Via Dashboard
Navigate to the System Status panel and click "Start Capture"
```

#### View Alerts
```bash
# Via API
curl http://localhost:5000/api/alerts

# Via Dashboard
Check the "Recent Alerts" table
```

#### Get Statistics
```bash
# Via API
curl http://localhost:5000/api/stats

# Via Dashboard
View the statistics cards and charts
```

## 📚 API Documentation

### Authentication
Currently no authentication required. All endpoints are publicly accessible.

### Base URL
```
http://localhost:5000/api
```

### Endpoints

#### Alerts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/alerts` | Get paginated alerts |
| GET | `/alerts/:id` | Get specific alert |
| PUT | `/alerts/:id` | Update alert status |
| DELETE | `/alerts/:id` | Delete alert |
| DELETE | `/alerts` | Clear all alerts |

#### Statistics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stats` | Get real-time statistics |
| GET | `/stats/summary` | Get summary statistics |
| GET | `/stats/historical` | Get historical data |

#### Packets
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/packets` | Get paginated packets |
| POST | `/packets` | Create test packet |
| GET | `/packets/recent` | Get recent packets |
| GET | `/packets/export` | Export packets (CSV) |

#### System Control
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/packets/status` | Get capture status |
| POST | `/packets/start` | Start packet capture |
| POST | `/packets/stop` | Stop packet capture |
| GET | `/interfaces` | Get network interfaces |

### Example API Calls

#### Get Recent Alerts
```bash
curl "http://localhost:5000/api/alerts?limit=10&severity=high"
```

#### Start Packet Capture with Filter
```bash
curl -X POST http://localhost:5000/api/packets/start \
  -H "Content-Type: application/json" \
  -d '{"interface": "eth0", "filter": "tcp port 80"}'
```

#### Get System Statistics
```bash
curl http://localhost:5000/api/stats
```

## 🧪 Testing

### Automated Testing Scripts

#### 1. Test Packet Injection
```bash
cd backend
node scripts/testPackets.js
```

This script injects various types of test packets to verify system functionality.

#### 2. Attack Simulation
```bash
cd backend

# Simulate DoS attack
node scripts/simulateAttack.js dos

# Simulate port scan
node scripts/simulateAttack.js portscan

# Simulate mixed attack
node scripts/simulateAttack.js mixed
```

### Manual Testing

#### Test DoS Detection
1. Start the IDS system
2. Run: `node scripts/simulateAttack.js dos`
3. Check dashboard for DoS alerts
4. Verify alert details and severity

#### Test Port Scan Detection
1. Start the IDS system
2. Run: `node scripts/simulateAttack.js portscan`
3. Check dashboard for port scan alerts
4. Verify source IP and port information

#### Test WebSocket Connection
1. Open browser developer tools
2. Navigate to dashboard
3. Check for WebSocket connection in Network tab
4. Verify real-time updates

### Performance Testing

#### Load Testing
```bash
# High packet rate test
node scripts/simulateAttack.js dos

# Monitor system resources
htop  # or Task Manager on Windows
```

#### Memory Usage
```bash
# Check memory usage
curl http://localhost:5000/api/stats/health
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Packet Capture Permission Denied
**Error**: `Permission denied` or `Access denied`

**Solution**:
```bash
# Run with administrator privileges
sudo npm start  # Linux/macOS
# Or run PowerShell as Administrator on Windows
```

#### 2. Npcap/WinPcap Not Found
**Error**: `No such device` or `pcap not found`

**Solution**:
- **Windows**: Install Npcap or WinPcap
- **Linux**: `sudo apt-get install libpcap-dev`
- **macOS**: `brew install libpcap`

#### 3. Network Interface Not Found
**Error**: `No interfaces found`

**Solution**:
```bash
# List available interfaces
node -e "const pcap = require('pcap'); console.log(pcap.findalldevs());"

# Use 'any' interface in configuration
CAPTURE_INTERFACE=any
```

#### 4. WebSocket Connection Failed
**Error**: WebSocket connection errors in browser

**Solution**:
1. Check backend server is running
2. Verify CORS configuration
3. Check firewall settings
4. Ensure ports 5000 and 3000 are open

#### 5. High Memory Usage
**Symptoms**: System slows down, memory usage increases

**Solution**:
1. Reduce `MAX_PACKETS_PER_FILE` and `MAX_ALERTS_PER_FILE`
2. Increase packet buffer rotation frequency
3. Monitor with `htop` or Task Manager

### Debug Mode

Enable debug logging:
```bash
# Set debug environment
export DEBUG=ids:*
export LOG_LEVEL=debug

# Start with debug output
npm start
```

### Log Files

Check log files for errors:
```bash
# Backend logs
tail -f backend/logs/ids.log

# System logs (Linux/macOS)
tail -f /var/log/syslog | grep ids
```

## 🚀 Performance Optimization

### Backend Optimization

1. **Adjust Buffer Sizes**:
   ```bash
   # Reduce memory usage
   MAX_PACKETS_PER_FILE=5000
   MAX_ALERTS_PER_FILE=2500
   ```

2. **Optimize Detection Thresholds**:
   ```bash
   # More sensitive detection
   DOS_THRESHOLD_PACKETS_PER_SEC=50
   PORT_SCAN_THRESHOLD_PORTS=10
   ```

3. **Use Specific Filters**:
   ```bash
   # Capture only relevant traffic
   CAPTURE_FILTER="tcp port 80 or tcp port 443"
   ```

### Frontend Optimization

1. **Reduce Update Frequency**:
   - Modify WebSocket update intervals
   - Limit real-time data points

2. **Optimize Charts**:
   - Reduce chart data points
   - Use data sampling

## 🔮 Future Enhancements

### Planned Features
- [ ] Database integration (PostgreSQL/MongoDB)
- [ ] Machine learning-based detection
- [ ] Email/Slack notifications
- [ ] Mobile app dashboard
- [ ] Geographic IP analysis
- [ ] Advanced threat intelligence
- [ ] Multi-tenant support
- [ ] API authentication
- [ ] Prometheus metrics
- [ ] Docker containerization

### Extensibility

The system is designed for easy extension:

1. **New Detection Types**: Add to `backend/config/thresholds.js`
2. **Custom Alerts**: Extend `backend/models/schemas.js`
3. **Additional APIs**: Add to `backend/routes/api.js`
4. **Dashboard Components**: Create in `frontend/components/`

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Fork and clone the repository
git clone <your-fork-url>
cd IDS

# Install dependencies
cd backend && npm install
cd ../frontend && npm install

# Create feature branch
git checkout -b feature/your-feature

# Make changes and test
npm test

# Submit pull request
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check this README and inline code comments
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Join GitHub Discussions for questions
- **Email**: Contact the maintainers for critical issues

## 🙏 Acknowledgments

- **pcap** library for packet capture functionality
- **Socket.io** for real-time WebSocket communication
- **Next.js** for the modern React framework
- **Tailwind CSS** for utility-first styling
- **Recharts** for beautiful data visualizations

---

**⚠️ Security Notice**: This system is designed for legitimate network monitoring and security testing. Ensure you have proper authorization before deploying on any network.

**🔒 Legal Disclaimer**: Users are responsible for complying with local laws and regulations regarding network monitoring and data collection.