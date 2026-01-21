# Pre-Demo Checklist

This checklist should be completed before the hackathon demo to ensure everything works correctly.

**Last Updated**: 2026-01-21

---

## Pre-Demo Setup (30 minutes before demo)

### Environment Setup

- [ ] **Backend Environment**
  - [ ] Virtual environment activated (`source backend/venv/bin/activate` or equivalent)
  - [ ] Dependencies installed (`pip install -r backend/requirements.txt`)
  - [ ] `.env` file exists in `backend/` directory
  - [ ] `CLASSIFICATION_ENABLED=true` in `.env` (if using ML features)
  - [ ] MongoDB connection string configured in `.env`
  - [ ] Model file exists: `backend/classification_model.pkl` (47.33 MB)

- [ ] **Frontend Environment**
  - [ ] Node.js dependencies installed (`npm install`)
  - [ ] `.env.local` file exists (optional, uses defaults if not)
  - [ ] `NEXT_PUBLIC_FLASK_API_URL=http://localhost:3002` set (if custom)

### Service Startup

- [ ] **Backend Server**
  - [ ] Backend starts without errors: `cd backend && python app.py`
  - [ ] Server running on `http://localhost:3002`
  - [ ] Health check works: `curl http://localhost:3002/api/health`
  - [ ] No critical errors in console/logs

- [ ] **Frontend Server**
  - [ ] Frontend starts without errors: `npm run dev`
  - [ ] Server running on `http://localhost:3000`
  - [ ] No build errors
  - [ ] No critical console errors

### System Verification

- [ ] **Model Loading**
  - [ ] Model file exists and is readable
  - [ ] Model loads without errors (check backend logs)
  - [ ] Classification endpoint responds: `curl http://localhost:3002/api/training/metrics`

- [ ] **Database Connection**
  - [ ] MongoDB connection successful
  - [ ] Database accessible (check backend logs)
  - [ ] Training data collection working (if enabled)

- [ ] **API Endpoints**
  - [ ] `/api/health` - Health check
  - [ ] `/api/training/statistics` - Training stats
  - [ ] `/api/training/model-info` - Model information
  - [ ] `/api/training/metrics` - Model metrics
  - [ ] `/api/training/evaluate` - Model evaluation
  - [ ] `/api/stats/traffic` - Traffic statistics
  - [ ] `/api/alerts` - Alerts list

---

## Frontend Pages Verification

### Dashboard Page (`/`)

- [ ] Page loads without errors
- [ ] Stats cards display (may show 0 if no data)
- [ ] Backend connection status visible
- [ ] Alerts overview component loads
- [ ] Traffic stats component loads
- [ ] No console errors

### Analysis Page (`/analysis`)

- [ ] Page loads without errors
- [ ] **ML Training Tab**:
  - [ ] Training dashboard displays
  - [ ] Statistics show (may be 0 if no data)
  - [ ] Training history displays (if available)
  - [ ] Train button works (if sufficient data)
  
- [ ] **Bulk Packet Analysis Tab**:
  - [ ] Form displays correctly
  - [ ] Analysis type selector works
  - [ ] Analyze button functional

- [ ] **Flow Analysis Tab**:
  - [ ] Form displays correctly
  - [ ] Duration selector works
  - [ ] Analyze button functional

- [ ] **Model Metrics Tab**:
  - [ ] Classification metrics component loads
  - [ ] Metrics display (if model trained)
  - [ ] Error handling works (shows message if model not trained)
  - [ ] Confusion matrix displays
  - [ ] ROC curve displays
  - [ ] Feature importance displays

### Alerts Page (`/alerts`)

- [ ] Page loads without errors
- [ ] Alerts list displays (may be empty)
- [ ] Filtering works
- [ ] Pagination works (if many alerts)

### Stats Page (`/stats`)

- [ ] Page loads without errors
- [ ] Traffic statistics display
- [ ] Protocol distribution chart displays
- [ ] Connection stats display

### Real-time Page (`/realtime`)

- [ ] Page loads without errors
- [ ] WebSocket connection attempts (may fail if backend not broadcasting)
- [ ] Real-time dashboard displays
- [ ] Error handling for disconnected state

---

## Demo Flow Verification

### Complete Demo Flow Test

Follow the demo script (`DEMO_SCRIPT.md`) and verify:

1. **Introduction** (2 min)
   - [ ] Can explain problem statement
   - [ ] Can explain solution
   - [ ] Key features ready to show

2. **Training Dashboard Demo** (2 min)
   - [ ] Navigate to `/analysis` → ML Training tab
   - [ ] Training statistics display
   - [ ] Training history shows (if available)
   - [ ] Can explain model training process

3. **Model Metrics Demo** (2 min)
   - [ ] Navigate to Model Metrics tab
   - [ ] Metrics display correctly
   - [ ] Confusion matrix visible
   - [ ] ROC curve visible
   - [ ] Can explain metrics

4. **Real-time Detection** (2 min)
   - [ ] Navigate to `/realtime` or `/`
   - [ ] Dashboard shows data
   - [ ] Can explain real-time processing
   - [ ] Alerts display (if any)

5. **Technical Highlights** (2 min)
   - [ ] Can explain architecture
   - [ ] Can explain dataset
   - [ ] Can explain model performance
   - [ ] Can explain training details

---

## Backup Plan Verification

- [ ] **Screenshots/Videos Ready**
  - [ ] Screenshots of key pages
  - [ ] Video of demo flow (if available)
  - [ ] Architecture diagrams

- [ ] **Documentation Ready**
  - [ ] `DEMO_SCRIPT.md` reviewed
  - [ ] `KNOWN_ISSUES.md` reviewed
  - [ ] `HACKATHON_QUICK_START.md` available
  - [ ] `IMPLEMENTATION_STATUS.md` available

- [ ] **Talking Points Prepared**
  - [ ] Problem statement clear
  - [ ] Solution explanation ready
  - [ ] Technical highlights prepared
  - [ ] Q&A answers prepared

---

## Known Issues Acknowledgment

- [ ] **Model Accuracy**: 69.74% (below 90% target)
  - [ ] Can explain this is acceptable for demo
  - [ ] Can explain improvement plan at deadline
  - [ ] Can demonstrate system works despite lower accuracy

- [ ] **Feature Mismatch**: 81 vs 70 features
  - [ ] Can explain system handles this gracefully
  - [ ] Can explain fix plan at deadline

- [ ] **Training Data**: May need more samples
  - [ ] Can explain data collection process
  - [ ] Can show existing model works

---

## Quick Commands Reference

### Start Services

```bash
# Option 1: Use startup script
./start-dev.sh

# Option 2: Manual start
# Terminal 1: Backend
cd backend
source venv/bin/activate  # or: . venv/bin/activate
python app.py

# Terminal 2: Frontend
npm run dev
```

### Verify Services

```bash
# Backend health check
curl http://localhost:3002/api/health

# Training statistics
curl http://localhost:3002/api/training/statistics

# Model info
curl http://localhost:3002/api/training/model-info
```

### Check Model

```bash
# Check model file
ls -lh backend/classification_model.pkl

# Verify model loads (in Python)
cd backend
python -c "from services.classifier import ClassificationDetector; from config import DevelopmentConfig; c = ClassificationDetector(DevelopmentConfig()); print('Model loaded:', c.model is not None)"
```

---

## Troubleshooting

### Backend Won't Start

- Check MongoDB connection in `.env`
- Check port 3002 is available
- Check virtual environment is activated
- Check dependencies are installed
- Review `ids_backend.log` for errors

### Frontend Won't Load

- Check Next.js dev server is running
- Check port 3000 is available
- Check API endpoints are accessible
- Review browser console for errors
- Check `NEXT_PUBLIC_FLASK_API_URL` is correct

### Model Not Found

- Verify `backend/classification_model.pkl` exists
- Check file permissions
- Try reloading model in backend

### API Errors

- Check backend is running
- Check CORS settings
- Check API endpoint URLs
- Review backend logs for errors

---

## Final Status

**System Ready**: [ ] Yes [ ] No

**Issues Found**: 
- 

**Notes**: 
- 

---

## Post-Demo Notes

After the demo, document:
- What worked well
- What didn't work
- Questions asked
- Feedback received
- Improvements needed

---

**Good luck with your demo! 🚀**
