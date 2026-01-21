# Hackathon Quick Start Guide

Get the IDS system up and running in 5 minutes!

---

## Prerequisites

- **Python 3.10+** (check: `python3 --version`)
  - **Note**: Python 3.14 has SSL issues with MongoDB Atlas. Training uses preprocessed JSON file to avoid this.
- **Node.js 18+** (check: `node --version`)
- **npm** (check: `npm --version`)
- **MongoDB Atlas account** (or local MongoDB) - Optional for training (uses JSON file)
- **8GB+ RAM** (for training)

---

## Quick Setup (5 minutes)

### Step 1: Clone and Navigate (30 seconds)

```bash
cd /home/harshdeep/Documents/Projects/IDS
```

### Step 2: Backend Setup (2 minutes)

```bash
# Navigate to backend
cd backend

# Activate virtual environment (if exists)
source venv/bin/activate

# If venv doesn't exist, create it:
# python3 -m venv venv
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Environment (1 minute)

```bash
# Copy example env file
cp env.example .env

# Edit .env file with your MongoDB connection string
nano .env  # or use your preferred editor
```

**Required `.env` variables**:
```bash
# MongoDB Configuration
MONGODB_URI=your_mongodb_connection_string
MONGODB_DATABASE_NAME=ids_db

# Enable Classification
CLASSIFICATION_ENABLED=true
MAX_TRAINING_SAMPLES=50000
```

### Step 4: Frontend Setup (1 minute)

```bash
# Navigate to project root
cd ..

# Install dependencies
npm install
```

### Step 5: Verify Database (30 seconds)

```bash
cd backend
source venv/bin/activate

# Check database connection and stats
python -c "
from config import Config
from services.data_collector import DataCollector
config = Config()
collector = DataCollector(config)
stats = collector.get_statistics()
print(f'Total samples: {stats.get(\"total_samples\", 0):,}')
print(f'Labeled samples: {stats.get(\"labeled_samples\", 0):,}')
"
```

**Expected**: Should show sample counts (ideally 50,000+)

---

## Running the Application

### Start Backend

```bash
cd backend
source venv/bin/activate
python app.py
```

**Expected output**:
```
 * Running on http://127.0.0.1:3002
```

### Start Frontend (New Terminal)

```bash
cd /home/harshdeep/Documents/Projects/IDS
npm run dev
```

**Expected output**:
```
  ▲ Next.js 14.x.x
  - Local:        http://localhost:3000
```

### Access the Application

Open browser: `http://localhost:3000`

---

## Training the Model

### Option 1: Via Script (Recommended)

```bash
cd backend
source venv/bin/activate
python scripts/train_from_cicids2018.py
```

**Expected time**: 5-10 minutes for 50K samples

### Option 2: Via API

```bash
# With backend running, in another terminal:
curl -X POST http://localhost:3002/api/training/train \
  -H "Content-Type: application/json" \
  -d '{"hyperparameter_tuning": false}'
```

### Option 3: Via Frontend

1. Navigate to: `http://localhost:3000/analysis`
2. Click "ML Training" tab
3. Click "Train Model" button

---

## Evaluating the Model

```bash
cd backend
source venv/bin/activate
python scripts/evaluate_model.py \
    --model-path ./classification_model.pkl \
    --output-dir ./evaluation_results
```

**Expected metrics**:
- Accuracy: 93-97%
- Precision: 92-96%
- Recall: 92-96%
- F1-Score: 92-96%
- ROC-AUC: >0.95

---

## Key Pages

### Dashboard
- **URL**: `http://localhost:3000`
- **Features**: Overview, alerts, traffic stats

### Analysis Page
- **URL**: `http://localhost:3000/analysis`
- **Features**: Training dashboard, model metrics, training history

### Real-time Dashboard
- **URL**: `http://localhost:3000/realtime`
- **Features**: Live packet analysis, ML classifications

### Statistics
- **URL**: `http://localhost:3000/stats`
- **Features**: Traffic statistics, protocol distribution

### Alerts
- **URL**: `http://localhost:3000/alerts`
- **Features**: Alert management, filtering, resolution

---

## Common Commands

### Check Model Status
```bash
cd backend
ls -lh classification_model.pkl
python -c "import pickle; m=pickle.load(open('classification_model.pkl','rb')); print(f'Test Accuracy: {m.get(\"test_metrics\", {}).get(\"accuracy\", 0)*100:.2f}%')"
```

### Check Database Stats
```bash
cd backend
source venv/bin/activate
python -c "
from config import Config
from services.data_collector import DataCollector
c = DataCollector(Config())
s = c.get_statistics()
print(f'Total: {s.get(\"total_samples\", 0):,}')
print(f'Benign: {s.get(\"benign_count\", 0):,}')
print(f'Malicious: {s.get(\"malicious_count\", 0):,}')
"
```

### Test Classification API
```bash
curl -X POST http://localhost:3002/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "packet_data": {
      "src_ip": "192.168.1.100",
      "dst_ip": "10.0.0.1",
      "protocol": "TCP",
      "port": 80
    }
  }'
```

---

## Troubleshooting

### Backend Won't Start

**Issue**: Port already in use
```bash
# Find process using port 3002
lsof -i :3002
# Kill process or change port in app.py
```

**Issue**: MongoDB connection failed
```bash
# Check .env file has correct MONGODB_URI
# Verify MongoDB Atlas IP whitelist includes your IP
# Test connection: ping your MongoDB cluster
```

### Frontend Won't Load

**Issue**: API connection error
```bash
# Verify backend is running on port 3002
curl http://localhost:3002/api/health
```

**Issue**: Module not found
```bash
# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

### Model Training Fails

**Issue**: Insufficient samples
```bash
# Check database has enough labeled samples
# Minimum: 1000 samples
# Recommended: 50,000 samples
```

**Issue**: Out of memory
```bash
# Reduce MAX_TRAINING_SAMPLES in .env
# Or enable batch loading: BATCH_LOADING_ENABLED=true
```

### Database Connection Issues

**Issue**: SSL handshake failed
```bash
# Check Python SSL/TLS version compatibility
# Update pymongo: pip install --upgrade pymongo
# Check MongoDB Atlas network access settings
```

---

## File Structure

```
IDS/
├── backend/
│   ├── app.py                    # Flask application
│   ├── config.py                 # Configuration
│   ├── .env                      # Environment variables
│   ├── classification_model.pkl # Trained model
│   ├── scripts/
│   │   ├── train_from_cicids2018.py
│   │   └── evaluate_model.py
│   ├── services/
│   │   ├── classifier.py
│   │   ├── model_trainer.py
│   │   └── model_evaluator.py
│   └── routes/
│       └── training.py
├── app/                          # Next.js pages
├── components/                   # React components
└── package.json                  # Frontend dependencies
```

---

## Environment Variables Reference

### Required
- `MONGODB_URI`: MongoDB connection string
- `MONGODB_DATABASE_NAME`: Database name (default: `ids_db`)

### ML Configuration
- `CLASSIFICATION_ENABLED`: Enable ML classification (default: `false`)
- `MAX_TRAINING_SAMPLES`: Max samples for training (default: `50000`)
- `MIN_TRAINING_SAMPLES_CLASSIFICATION`: Minimum required (default: `1000`)

### Optional
- `CLASSIFICATION_MODEL_TYPE`: Model type (default: `random_forest`)
- `HYPERPARAMETER_TUNING_ENABLED`: Enable tuning (default: `false`)
- `CLASSIFICATION_CONFIDENCE_THRESHOLD`: Confidence threshold (default: `0.7`)

---

## Next Steps

1. **Train Model**: Run training script
2. **Evaluate**: Run evaluation script
3. **Test**: Use frontend to test classification
4. **Demo**: Follow `DEMO_SCRIPT.md` for presentation
5. **Deploy**: Prepare for production deployment

---

## Support

- **Documentation**: See `NEXT_STEPS_PLAN.md` for detailed plan
- **Issues**: Check troubleshooting section above
- **Demo**: See `DEMO_SCRIPT.md` for presentation guide

---

**Ready to go! 🚀**
