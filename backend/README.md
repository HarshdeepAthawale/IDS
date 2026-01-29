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

5. **Train Anomaly Detection Model** (Optional but recommended):
   ```bash
   python scripts/train_anomaly_model.py
   ```
   This will generate synthetic packet data and train the Isolation Forest model for anomaly detection. The model will also auto-train when enough real packet data is collected (100+ samples).

### Running tests

Minimal API tests (health, model-info) use pytest. From the `backend` directory:

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

Requires full dependencies (including TensorFlow if using SecIDS-CNN). In Docker: `docker compose exec backend python -m pytest tests/ -v`.

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

# Optional: SecIDS-CNN pre-trained classifier (set CLASSIFICATION_MODEL_TYPE=secids_cnn)
# Requires TensorFlow and SecIDS-CNN.h5; see docs/SECIDS_CNN.md
# CLASSIFICATION_MODEL_TYPE=random_forest   # or secids_cnn
# SECIDS_MODEL_PATH=   # optional path to SecIDS-CNN.h5

# Whitelist IPs (comma-separated)
WHITELIST_IPS=127.0.0.1,10.0.0.0/8,192.168.0.0/16
```

### SecIDS-CNN (optional)

To use the pre-trained SecIDS-CNN model instead of the trainable sklearn classifier, set `CLASSIFICATION_MODEL_TYPE=secids_cnn` and `CLASSIFICATION_ENABLED=true`. You must install TensorFlow and place `SecIDS-CNN.h5` (from [Hugging Face](https://huggingface.co/Keyven/SecIDS-CNN)) at `SecIDS-CNN/SecIDS-CNN.h5` or set `SECIDS_MODEL_PATH`. See [docs/SECIDS_CNN.md](docs/SECIDS_CNN.md) for setup and feature mapping.

## Packet Capture Permissions Setup

The IDS Backend requires elevated privileges to capture network packets. For production use, you need to set up packet capture permissions.

### Quick Start (Development)

**Option 1: Automated Setup (Recommended)**

```bash
# Make scripts executable (first time only)
chmod +x setup_permissions.sh start.sh

# Use smart startup script (automatically sets up permissions)
./start.sh
```

**Option 2: Manual Setup**

```bash
# One-time setup
./setup_permissions.sh

# Then run normally
python app.py
```

### Production Setup

For production deployments, use the systemd service file:

```bash
# Copy service file
sudo cp ids-backend.service /etc/systemd/system/

# Edit service file to match your deployment paths
sudo nano /etc/systemd/system/ids-backend.service

# Install and start service
sudo systemctl daemon-reload
sudo systemctl enable ids-backend.service
sudo systemctl start ids-backend.service
```

**See [SETUP_PERMISSIONS.md](SETUP_PERMISSIONS.md) for detailed instructions.**

## Running the Application

### Development Mode

**With Permission Setup (Recommended):**

```bash
# Use smart startup script
./start.sh
```

**Or manually:**

```bash
# First time: Set up permissions
./setup_permissions.sh

# Then run normally
python app.py
```

**Without Permission Setup (Requires sudo):**

```bash
sudo python app.py
```

The server will start on `http://localhost:3002` (or the port specified in FLASK_PORT environment variable)

### Production Mode

**Using Systemd Service (Recommended):**

```bash
sudo systemctl start ids-backend.service
sudo systemctl status ids-backend.service
```

**Or manually:**

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

4. **Set Up Packet Capture Permissions**:
   ```bash
   # Set up capabilities for packet capture
   ./setup_permissions.sh
   
   # Or use systemd service (recommended)
   sudo cp ids-backend.service /etc/systemd/system/
   sudo systemctl enable ids-backend.service
   sudo systemctl start ids-backend.service
   ```

5. **Run Application**:
   ```bash
   # With capabilities set up (recommended)
   python3 app.py
   
   # Or using systemd service
   sudo systemctl start ids-backend.service
   ```

### Security Considerations

- **Packet Capture Permissions**: Use Linux capabilities (`cap_net_raw`, `cap_net_admin`) instead of running entire backend as root
  - Development: Use `setup_permissions.sh` script
  - Production: Use systemd service with `AmbientCapabilities` (see `ids-backend.service`)
- Use HTTPS in production
- Implement authentication/authorization
- Run backend as dedicated non-root user (for systemd service)
- Regular security updates
- Monitor system resources
- See [SETUP_PERMISSIONS.md](SETUP_PERMISSIONS.md) for detailed security guidance

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

   **Quick Fix (Development):**
   ```bash
   # Run setup script
   ./setup_permissions.sh
   
   # Then run normally
   python app.py
   ```

   **Alternative (Requires sudo each time):**
   ```bash
   sudo python app.py
   ```

   **For Production:**
   - Use systemd service with `AmbientCapabilities` (see `ids-backend.service`)
   - Or set capabilities on Python binary: `sudo setcap cap_net_raw,cap_net_admin=eip /path/to/python3`

   **See [SETUP_PERMISSIONS.md](SETUP_PERMISSIONS.md) for detailed troubleshooting.**

2. **Database Connection Errors**:
   - Check DATABASE_URL format
   - Verify database credentials
   - Ensure database exists

3. **High CPU Usage**:
   - Adjust CAPTURE_TIMEOUT
   - Reduce PACKET_RATE_THRESHOLD
   - Implement packet filtering

4. **Capabilities Not Working**:
   - Verify capabilities: `getcap /path/to/python3`
   - Should show: `cap_net_raw,cap_net_admin=eip`
   - Re-run setup script: `./setup_permissions.sh`
   - Ensure using correct Python binary (check `which python3`)

5. **No Packets Captured**:
   - Verify capabilities are set correctly
   - Check network interface: `ip link show` or `ifconfig`
   - Verify interface in `.env`: `CAPTURE_INTERFACE=eth0` (replace with your interface)
   - Test with network traffic: `curl http://example.com` or `ping 8.8.8.8`
   - Check backend logs for permission errors

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
