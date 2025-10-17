# Flask IDS Backend

A production-ready Flask backend for network intrusion detection with signature-based detection, ML-based anomaly detection, and insider threat monitoring.

## Features

- **Real-time Packet Capture**: Live packet analysis using Scapy
- **Signature-based Detection**: Pattern matching for known attacks
- **ML Anomaly Detection**: Isolation Forest for detecting unusual traffic patterns
- **Insider Threat Detection**: User activity monitoring and analysis
- **Traffic Statistics**: Protocol distribution, connection tracking, and metrics
- **REST API**: Complete REST API for frontend integration
- **Database Integration**: SQLAlchemy with PostgreSQL/SQLite support
- **AWS Ready**: Environment-based configuration for cloud deployment

## Project Structure

```
backend/
├── app.py                    # Main Flask application
├── config.py                 # Configuration management
├── requirements.txt          # Python dependencies
├── env.example              # Environment variables template
├── README.md                # This file
├── routes/
│   ├── alerts.py            # Alert management endpoints
│   ├── stats.py             # Traffic statistics endpoints
│   ├── analyze.py           # Packet analysis endpoints
│   └── insider.py           # Insider threat endpoints
├── services/
│   ├── packet_sniffer.py    # Real-time packet capture
│   ├── analyzer.py          # Detection engines
│   └── logger.py            # Database operations
└── models/
    └── db_models.py         # SQLAlchemy models
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd backend
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize database**:
   ```bash
   python -c "from app import create_app; from models.db_models import init_db; app = create_app(); init_db(app)"
   ```

## Configuration

### Environment Variables

Copy `env.example` to `.env` and configure:

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
DEBUG=true

# Database (SQLite for development)
DATABASE_URL=sqlite:///ids.db

# Database (PostgreSQL for production)
# DATABASE_URL=postgresql://username:password@your-rds-endpoint.amazonaws.com:5432/ids_db

# Detection Thresholds
PACKET_RATE_THRESHOLD=1000
CONNECTION_LIMIT=100
ANOMALY_SCORE_THRESHOLD=0.5

# Packet Capture
CAPTURE_INTERFACE=any
CAPTURE_TIMEOUT=1

# Alert Settings
ALERT_DEDUP_WINDOW=300
MAX_ALERTS_PER_HOUR=100

# ML Model Settings
MODEL_RETRAIN_INTERVAL=3600
MIN_SAMPLES_FOR_TRAINING=100

# Whitelist IPs (comma-separated)
WHITELIST_IPS=127.0.0.1,10.0.0.0/8,192.168.0.0/16
```

## Running the Application

### Development Mode

```bash
python app.py
```

The server will start on `http://localhost:5000`

### Production Mode

```bash
export FLASK_ENV=production
python app.py
```

## API Endpoints

### Health Check
- `GET /api/health` - System health status
- `GET /api/system/info` - System information

### Alerts
- `GET /api/alerts` - Get recent alerts with filtering
- `GET /api/alerts/history` - Get historical alerts by date range
- `PATCH /api/alerts/<id>` - Update alert (resolve/unresolve)
- `DELETE /api/alerts/<id>` - Delete alert
- `GET /api/alerts/summary` - Alert summary statistics
- `POST /api/alerts/bulk-resolve` - Bulk resolve alerts

### Traffic Statistics
- `GET /api/stats/traffic` - Current traffic metrics
- `GET /api/stats/protocols` - Protocol distribution
- `GET /api/stats/connections` - Connection statistics
- `GET /api/stats/anomalies` - Anomaly statistics

### Analysis
- `POST /api/analyze` - Analyze single packet
- `POST /api/analyze/bulk` - Analyze multiple packets
- `POST /api/analyze/flow` - Analyze network flow
- `GET /api/analyze/model-info` - Model information

### Insider Threats
- `GET /api/insider-threats` - Get suspicious user activities
- `GET /api/insider-threats/users/<user_id>` - Get user-specific activities
- `GET /api/insider-threats/summary` - Insider threat summary
- `POST /api/insider-threats/log` - Log user activity

## Detection Capabilities

### Signature-based Detection

Detects known attack patterns:

- **SQL Injection**: Pattern matching for SQL injection attempts
- **XSS Attacks**: Cross-site scripting detection
- **Port Scanning**: Multiple port access patterns
- **DoS Attacks**: High packet rate detection
- **Brute Force**: Failed authentication attempts
- **Malware Communication**: Suspicious payload patterns
- **Data Exfiltration**: Large data transfers

### ML Anomaly Detection

Uses Isolation Forest to detect:

- Unusual traffic patterns
- Anomalous packet characteristics
- Suspicious connection behaviors
- Protocol anomalies

### Insider Threat Detection

Monitors user activities:

- Off-hours access
- File access patterns
- Privilege escalation attempts
- Data exfiltration
- Suspicious commands

## Database Models

### Alert
- Security alerts with source/destination IPs
- Detection type (signature/anomaly)
- Severity levels and confidence scores
- Timestamps and resolution tracking

### TrafficStat
- Traffic metrics and protocol distribution
- Connection counts and packet rates
- Top talkers and destination ports
- Anomaly counts

### UserActivity
- User activity logging for insider threats
- Activity types and severity levels
- Source IPs and session tracking
- Geolocation data

## AWS Deployment

### Prerequisites

1. **EC2 Instance**: With admin privileges for packet capture
2. **RDS Database**: PostgreSQL instance
3. **Security Groups**: Allow HTTP/HTTPS and database access
4. **IAM Roles**: For RDS access

### Deployment Steps

1. **Launch EC2 Instance**:
   ```bash
   # Use Ubuntu 20.04 LTS or similar
   sudo apt update
   sudo apt install python3-pip postgresql-client
   ```

2. **Install Dependencies**:
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Configure Environment**:
   ```bash
   export FLASK_ENV=production
   export DATABASE_URL=postgresql://user:pass@rds-endpoint:5432/ids_db
   export SECRET_KEY=your-production-secret-key
   ```

4. **Run Application**:
   ```bash
   python3 app.py
   ```

### Security Considerations

- Run with elevated privileges for packet capture
- Use HTTPS in production
- Implement authentication/authorization
- Regular security updates
- Monitor system resources

## Development

### Adding New Signatures

Edit `services/analyzer.py` to add new attack patterns:

```python
'signature_name': {
    'patterns': [r'regex_pattern'],
    'severity': 'medium',
    'description': 'Attack description'
}
```

### Customizing Detection

Modify thresholds in `config.py`:

```python
PACKET_RATE_THRESHOLD = 1000  # Packets per second
ANOMALY_SCORE_THRESHOLD = 0.5  # ML confidence threshold
```

### Database Migrations

For schema changes, update models and run:

```bash
python -c "from app import create_app; from models.db_models import db; app = create_app(); app.app_context().push(); db.create_all()"
```

## Troubleshooting

### Common Issues

1. **Permission Denied for Packet Capture**:
   ```bash
   sudo python app.py
   ```

2. **Database Connection Errors**:
   - Check DATABASE_URL format
   - Verify database credentials
   - Ensure database exists

3. **High CPU Usage**:
   - Adjust CAPTURE_TIMEOUT
   - Reduce PACKET_RATE_THRESHOLD
   - Implement packet filtering

### Logs

Check application logs:
```bash
tail -f ids_backend.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Create GitHub issues
- Check documentation
- Review logs for debugging
