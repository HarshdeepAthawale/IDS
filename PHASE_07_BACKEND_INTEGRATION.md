# Phase 7: Backend Integration

## Overview

This phase covers integrating the trained classification model into the Flask backend, enabling real-time packet classification and alert generation. The model will be used alongside existing signature-based and anomaly detection.

## Prerequisites

- Phase 6 completed (model evaluated and verified)
- Model file exists: `backend/models/classification_model.pkl`
- Backend services running

## Step 1: Verify Model Integration Points

### 1.1 Check Current Detection Services

```bash
cd backend
ls -lh services/analyzer.py
ls -lh services/classifier.py
```

The backend should have:
- `services/analyzer.py`: Main analyzer with signature and anomaly detection
- `services/classifier.py`: Classification detector (if exists)

### 1.2 Verify Model File

```bash
ls -lh models/classification_model.pkl
```

## Step 2: Configure Classification

### 2.1 Verify Environment Configuration

```bash
cat .env | grep CLASSIFICATION
```

**Required settings:**
```bash
CLASSIFICATION_ENABLED=true
CLASSIFICATION_MODEL_TYPE=random_forest
CLASSIFICATION_CONFIDENCE_THRESHOLD=0.7
```

### 2.2 Update Configuration if Needed

Edit `backend/.env`:
```bash
CLASSIFICATION_ENABLED=true
CLASSIFICATION_CONFIDENCE_THRESHOLD=0.7
```

## Step 3: Test Model Loading

### 3.1 Test Classification Service

```bash
cd backend
source venv/bin/activate
python -c "
from services.classifier import ClassificationDetector
from config import Config

config = Config()
classifier = ClassificationDetector(config)

# Test model loading
print('Model loaded:', classifier.model is not None)
print('Feature extractor ready:', classifier.feature_extractor is not None)
"
```

**Expected**: Model loads without errors

### 3.2 Test Prediction

```bash
python -c "
from services.classifier import ClassificationDetector
from config import Config

config = Config()
classifier = ClassificationDetector(config)

# Create sample features
test_features = {
    'packet_size': 1500,
    'protocol': 6,  # TCP
    'src_port': 80,
    'dst_port': 443,
    'flow_duration': 1000000,
    'tot_fwd_pkts': 10,
    'tot_bwd_pkts': 8,
    # Add other required features
}

result = classifier.classify(test_features)
print('Prediction:', result.get('prediction'))
print('Confidence:', result.get('confidence', 0))
print('Success:', result.get('success', False))
"
```

**Expected**: Prediction made successfully

## Step 4: Integrate with Packet Analyzer

### 4.1 Verify Analyzer Integration

The `services/analyzer.py` should call the classifier:

```python
# In analyzer.py
from services.classifier import ClassificationDetector

class PacketAnalyzer:
    def __init__(self, config):
        # ... existing code ...
        if config.CLASSIFICATION_ENABLED:
            self.classifier = ClassificationDetector(config)
    
    def analyze_packet(self, packet_data):
        detections = []
        
        # Existing signature detection
        sig_detections = self.signature_detector.detect(packet_data)
        detections.extend(sig_detections)
        
        # Existing anomaly detection
        anomaly_detections = self.anomaly_detector.detect(packet_data)
        detections.extend(anomaly_detections)
        
        # NEW: Classification detection
        if self.classifier:
            class_result = self.classifier.classify(packet_data)
            if class_result.get('prediction') == 'malicious':
                detections.append({
                    'type': 'classification',
                    'severity': 'high',
                    'confidence': class_result.get('confidence', 0),
                    'description': f"ML Classification: {class_result.get('prediction')}"
                })
        
        return detections
```

### 4.2 Verify Integration Code

Check if integration exists:
```bash
grep -n "classifier" backend/services/analyzer.py
```

If not present, the integration may need to be added (check existing code structure).

## Step 5: Test Backend API

### 5.1 Start Backend

```bash
cd backend
source venv/bin/activate
python app.py
```

**Expected**: Backend starts without errors

### 5.2 Test Health Endpoint

```bash
curl http://localhost:3002/api/health
```

**Expected**: Returns JSON with status including classifier info

### 5.3 Test Analysis Endpoint

```bash
curl -X POST http://localhost:3002/api/analyze \
    -H "Content-Type: application/json" \
    -d '{
        "packet_size": 1500,
        "protocol": 6,
        "src_port": 80,
        "dst_port": 443
    }'
```

**Expected**: Returns analysis with classification results

### 5.4 Test Model Info Endpoint

```bash
curl http://localhost:3002/api/analyze/model-info
```

**Expected**: Returns model information (accuracy, features, etc.)

## Step 6: Verify Real-Time Detection

### 6.1 Test Packet Processing

If packet capture is enabled:

```bash
# Backend should be running
# Check logs for classification detections
tail -f ids_backend.log | grep -i classification
```

**Expected**: Classification detections appear in logs

### 6.2 Test WebSocket Alerts

Connect to WebSocket and monitor for classification alerts:

```bash
# Use WebSocket client or check frontend
# Classification alerts should appear in real-time
```

## Step 7: Verify Alert Generation

### 7.1 Check Alert Endpoint

```bash
curl http://localhost:3002/api/alerts?type=classification
```

**Expected**: Returns classification-based alerts

### 7.2 Verify Alert Structure

```bash
curl http://localhost:3002/api/alerts | python -m json.tool | head -20
```

**Expected**: Alerts include classification type

## Step 8: Performance Testing

### 8.1 Test Classification Speed

```bash
python -c "
import time
from services.classifier import ClassificationDetector
from config import Config

config = Config()
classifier = ClassificationDetector(config)

# Time classification
start = time.time()
for i in range(100):
    test_features = {'packet_size': 1500, 'protocol': 6, ...}
    classifier.classify(test_features)
end = time.time()

print(f'100 classifications in {end-start:.2f}s')
print(f'Average: {(end-start)/100*1000:.2f}ms per classification')
"
```

**Expected**: <10ms per classification

### 8.2 Monitor Resource Usage

```bash
# Monitor CPU and memory during classification
top -p $(pgrep -f app.py)
```

**Expected**: 
- CPU: <20% during classification
- Memory: Stable (no leaks)

## Step 9: Error Handling

### 9.1 Test Error Cases

**Missing features:**
```bash
python -c "
from services.classifier import ClassificationDetector
from config import Config

config = Config()
classifier = ClassificationDetector(config)

# Test with missing features
result = classifier.classify({'packet_size': 1500})
print('Handles missing features:', result.get('success', False) or 'error' in result)
"
```

**Invalid model:**
- Test behavior if model file is missing
- Test behavior if model is corrupted

### 9.2 Verify Graceful Degradation

If classification fails, system should:
- Continue with signature and anomaly detection
- Log error but don't crash
- Return appropriate error message

## Step 10: Configuration Options

### 10.1 Confidence Threshold

Adjust in `.env`:
```bash
CLASSIFICATION_CONFIDENCE_THRESHOLD=0.7
```

**Lower threshold (0.5)**: More detections, more false positives
**Higher threshold (0.9)**: Fewer detections, fewer false positives

### 10.2 Enable/Disable Classification

```bash
# Enable
CLASSIFICATION_ENABLED=true

# Disable (fallback to signature/anomaly only)
CLASSIFICATION_ENABLED=false
```

## Step 11: Troubleshooting

### Issue: Model Not Loading

**Symptoms**: Classification not working, errors in logs

**Solutions**:
1. Verify model file exists: `ls -lh models/classification_model.pkl`
2. Check file permissions: `chmod 644 models/classification_model.pkl`
3. Verify model format: Try loading with pickle directly
4. Check logs for specific error messages

### Issue: Classification Always Returns Same Result

**Symptoms**: All packets classified the same way

**Solutions**:
1. Check feature extraction: Verify features are being extracted correctly
2. Check feature normalization: Ensure features match training data format
3. Verify model: Test model with known samples

### Issue: Slow Classification

**Symptoms**: High latency in classification

**Solutions**:
1. Optimize feature extraction
2. Cache model predictions if appropriate
3. Use batch processing for multiple packets
4. Profile code to find bottlenecks

### Issue: Memory Leaks

**Symptoms**: Memory usage increases over time

**Solutions**:
1. Ensure model is loaded once, not per request
2. Clear feature caches periodically
3. Monitor memory usage: `ps aux | grep app.py`

### Issue: Integration Not Working

**Symptoms**: Classification not called in analyzer

**Solutions**:
1. Verify `CLASSIFICATION_ENABLED=true` in config
2. Check analyzer code includes classifier calls
3. Verify classifier is initialized in analyzer
4. Check logs for initialization errors

## Step 12: Verification Checklist

- [ ] Model file exists and is accessible
- [ ] Classification service loads model successfully
- [ ] Test predictions work correctly
- [ ] Analyzer integrates classification
- [ ] Backend starts without errors
- [ ] Health endpoint shows classifier status
- [ ] Analysis endpoint returns classification results
- [ ] Model info endpoint works
- [ ] Real-time detection includes classifications
- [ ] Alerts generated for classification detections
- [ ] Performance acceptable (<10ms per classification)
- [ ] Error handling works correctly
- [ ] Configuration options work
- [ ] No memory leaks
- [ ] Logs show classification activity

## File Locations

- **Model**: `backend/models/classification_model.pkl`
- **Classifier Service**: `backend/services/classifier.py`
- **Analyzer Service**: `backend/services/analyzer.py`
- **Backend App**: `backend/app.py`
- **Configuration**: `backend/.env`

## Next Steps

Once backend integration is complete and verified, proceed to:
- **Phase 8**: Frontend Integration - Display classification results in UI

## Estimated Time

- **Integration**: 15-30 minutes
- **Testing**: 15-20 minutes
- **Total**: 30-50 minutes

## Notes

- Classification works alongside signature and anomaly detection
- All three detection methods complement each other
- Classification provides ML-based attack detection
- Confidence threshold can be adjusted based on needs
- System gracefully degrades if classification fails
