# Phase 1: Project Setup

## Overview

This phase covers the complete environment setup for the IDS project, including Python and Node.js dependencies, database configuration, and verification that all services can start correctly.

## Prerequisites

- **Python**: 3.8 or higher
- **Node.js**: 18 or higher
- **Operating System**: Linux, macOS, or Windows
- **Administrator/Root privileges**: Required for packet capture (optional for initial setup)

## Step 1: Verify Prerequisites

### Check Python Version
```bash
python3 --version
# Should show Python 3.8 or higher
```

### Check Node.js Version
```bash
node --version
# Should show v18 or higher
npm --version
```

If either is missing, install them:
- **Python**: https://www.python.org/downloads/
- **Node.js**: https://nodejs.org/

## Step 2: Backend Setup

### 2.1 Navigate to Backend Directory
```bash
cd backend
```

### 2.2 Create Virtual Environment
```bash
# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 2.3 Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Expected output**: All packages should install successfully. If you see errors, check:
- Python version compatibility
- Internet connection for package downloads
- System dependencies (e.g., `libpcap` for Scapy on Linux)

### 2.4 Create Environment Configuration File
```bash
cp env.example .env
```

### 2.5 Configure Environment Variables

Edit `.env` file with the following settings optimized for hackathon/local training:

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-change-this
DEBUG=true

# Database (SQLite for hackathon - no setup required)
DATABASE_URL=sqlite:///ids.db
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE_NAME=ids_db

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

# Classification Settings (for hackathon)
CLASSIFICATION_ENABLED=true
CLASSIFICATION_MODEL_TYPE=random_forest
MIN_TRAINING_SAMPLES_CLASSIFICATION=1000
TRAIN_TEST_SPLIT_RATIO=0.7
HYPERPARAMETER_TUNING_ENABLED=false
MAX_TRAINING_SAMPLES=100000
BATCH_LOADING_ENABLED=true
CLASSIFICATION_CONFIDENCE_THRESHOLD=0.7

# Whitelist IPs
WHITELIST_IPS=127.0.0.1,10.0.0.0/8,192.168.0.0/16

# Logging
LOG_LEVEL=INFO
```

**Key settings for hackathon:**
- `MAX_TRAINING_SAMPLES=100000`: Limits training to 100K samples
- `BATCH_LOADING_ENABLED=true`: Memory-efficient loading
- `HYPERPARAMETER_TUNING_ENABLED=false`: Faster training
- `DATABASE_URL=sqlite:///ids.db`: Simple SQLite database

### 2.6 Initialize Database

```bash
python -c "from models.db_models import init_db; from app import create_app; app = create_app(); init_db(app)"
```

**Expected output**: Database tables created successfully.

## Step 3: Frontend Setup

### 3.1 Navigate to Project Root
```bash
cd ..
```

### 3.2 Install Node.js Dependencies
```bash
npm install
```

**Expected output**: All npm packages installed. This may take 2-5 minutes.

### 3.3 Create Frontend Environment File

Create `.env.local` in the project root:

```bash
NEXT_PUBLIC_FLASK_API_URL=http://localhost:3002
NEXT_PUBLIC_POLL_INTERVAL=10000
NEXT_PUBLIC_ENABLE_REAL_TIME=true
```

## Step 4: Verify Installation

### 4.1 Test Backend Startup

```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
python app.py
```

**Expected output:**
- Flask server starts on `http://localhost:3002`
- No critical errors in console
- Health check available at `http://localhost:3002/api/health`

**Test health endpoint:**
```bash
curl http://localhost:3002/api/health
```

Should return JSON with status information.

**Note**: Packet capture may require admin privileges. This is normal - the system will work in analysis-only mode without it.

### 4.2 Test Frontend Startup

In a new terminal:
```bash
cd /path/to/IDS
npm run dev
```

**Expected output:**
- Next.js dev server starts on `http://localhost:3001`
- No critical errors
- Frontend accessible in browser

### 4.3 Verify Integration

1. Open browser to `http://localhost:3001`
2. Check that frontend connects to backend
3. Verify dashboard loads (may show "No data" initially - this is normal)

## Step 5: Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError` when running Python scripts
- **Solution**: Ensure virtual environment is activated
- **Check**: `which python` should point to `venv/bin/python`

**Issue**: Port already in use
- **Solution**: Change ports in `.env` or kill existing process
- **Backend**: Change `FLASK_PORT` in `.env`
- **Frontend**: Change port in `package.json` scripts

**Issue**: Database connection errors
- **Solution**: For SQLite, ensure write permissions in `backend/` directory
- **Check**: `ls -la backend/ids.db` (file will be created on first run)

**Issue**: Scapy permission errors
- **Solution**: Run with `sudo` (Linux/Mac) or Administrator (Windows)
- **Note**: Not required for initial setup - only needed for live packet capture

**Issue**: MongoDB connection errors
- **Solution**: For hackathon, we use SQLite. Ensure `DATABASE_URL=sqlite:///ids.db` in `.env`
- MongoDB is optional and only needed if you want to use it instead of SQLite

## Step 6: Quick Start Scripts

### Automated Startup (Recommended)

**Linux/Mac:**
```bash
./start-dev.sh
```

**Windows:**
```bash
start-dev.bat
```

These scripts start both backend and frontend automatically.

### Manual Startup

**Terminal 1 (Backend):**
```bash
cd backend
source venv/bin/activate
python app.py
```

**Terminal 2 (Frontend):**
```bash
npm run dev
```

## Verification Checklist

- [ ] Python 3.8+ installed and verified
- [ ] Node.js 18+ installed and verified
- [ ] Virtual environment created and activated
- [ ] Python dependencies installed (`pip list` shows all packages)
- [ ] Node.js dependencies installed (`npm list` shows packages)
- [ ] `.env` file created and configured
- [ ] `.env.local` file created for frontend
- [ ] Database initialized successfully
- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] Health endpoint responds correctly
- [ ] Frontend can connect to backend

## Next Steps

Once all items in the checklist are complete, proceed to:
- **Phase 2**: Data Preparation - Download and prepare CICIDS2018 dataset subset

## Estimated Time

- **Setup time**: 15-30 minutes
- **Dependency installation**: 5-10 minutes
- **Verification**: 5 minutes

**Total**: 25-45 minutes

## Notes

- SQLite is used for simplicity in hackathon - no database server setup required
- Packet capture requires admin privileges but is optional for initial setup
- All configuration is optimized for local development and hackathon demo
- The system will work in analysis-only mode without packet capture permissions
