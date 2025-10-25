# Intrusion Detection System (IDS)

Real-time network intrusion detection system with Flask backend and Next.js frontend. Features packet capture, signature-based detection, ML anomaly detection, and comprehensive monitoring dashboard.

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Node.js](https://img.shields.io/badge/Node.js-18+-green)
![Flask](https://img.shields.io/badge/Flask-3.0.0-red)
![Next.js](https://img.shields.io/badge/Next.js-15.2.4-black)

## Features

- **Dual Detection**: Signature-based patterns + ML anomaly detection
- **Real-time Processing**: Live packet capture with WebSocket updates
- **Comprehensive Dashboard**: Alerts, traffic stats, insider threat monitoring
- **Production Ready**: Error handling, graceful degradation, health checks

## Quick Start

### Prerequisites
- Python 3.8+ and Node.js 18+
- Administrator privileges for packet capture

### Installation
```bash
git clone <repository-url>
cd IDS

# Backend setup
cd backend
pip install -r requirements.txt
cp env.example .env

# Frontend setup
cd ..
npm install

# Initialize database
cd backend
python -c "from models.db_models import init_db; from app import create_app; init_db(create_app())"
```

### Run
```bash
# Automated (recommended)
start-dev.bat  # Windows
./start-dev.sh  # Linux/Mac

# Manual
# Terminal 1: cd backend && python app.py
# Terminal 2: npm run dev
```

**Access**: http://localhost:3000 (Frontend) | http://localhost:3002 (API)

## Configuration

### Backend (`backend/.env`)
```bash
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///ids.db
PACKET_RATE_THRESHOLD=1000
ANOMALY_SCORE_THRESHOLD=0.5
CAPTURE_INTERFACE=any
WHITELIST_IPS=127.0.0.1,10.0.0.0/8,192.168.0.0/16
```

### Frontend (`.env.local`)
```bash
NEXT_PUBLIC_FLASK_API_URL=http://localhost:3002
NEXT_PUBLIC_POLL_INTERVAL=10000
NEXT_PUBLIC_ENABLE_REAL_TIME=true
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | System health check |
| `/api/alerts` | GET | Recent alerts with filtering |
| `/api/alerts/history` | GET | Historical alerts by date range |
| `/api/alerts/{id}` | PATCH/DELETE | Update/delete alert |
| `/api/stats/traffic` | GET | Traffic statistics |
| `/api/stats/protocols` | GET | Protocol distribution |
| `/api/insider-threats` | GET | User activity monitoring |
| `/api/analyze` | POST | Packet analysis |

## Detection Capabilities

- **Signature Detection**: SQL injection, XSS, port scanning, DoS, brute force, malware communication
- **ML Anomaly Detection**: Isolation Forest algorithm for unusual traffic patterns
- **Insider Threats**: User behavior analysis, off-hours access, data exfiltration
- **Whitelist System**: IP, port, and protocol filtering to reduce false positives

## Troubleshooting

**Permission Denied**: Run with administrator privileges
**Backend Disconnected**: Check Flask is running on port 3002
**No Real-time Data**: Backend unavailable - check logs

```bash
# Debug commands
curl http://localhost:3002/api/health
curl http://localhost:3000/api/stats
```

## Contributing

1. Fork repository
2. Create feature branch
3. Commit changes
4. Push and open PR

## License

MIT License - see [LICENSE](LICENSE) file.