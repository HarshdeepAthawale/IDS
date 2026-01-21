# Known Issues and Workarounds

This document lists known issues in the IDS system and their workarounds for the hackathon demo.

**Last Updated**: 2026-01-21

---

## Model Performance Issues

### 1. Model Accuracy Below Target (69.74% vs 90% target)

**Status**: Known limitation, acceptable for demo

**Details**:
- Current model accuracy: **69.74%**
- Target accuracy: 90%+
- Reason: Model trained on 26K samples instead of full 50K dataset
- Training samples: 26,385 (instead of 50,000)
- Validation samples: 7,196
- Test samples: 14,393

**Impact**: 
- Model still functional and makes predictions
- Lower accuracy means more false positives/negatives
- Acceptable for demo purposes

**Workaround**: 
- For demo: Explain that accuracy will be improved at hackathon deadline
- Model is functional and demonstrates the system capabilities
- Focus on showing the complete workflow rather than perfect accuracy

**Plan for Improvement** (at hackathon deadline):
- Retrain with full 50K samples from JSON file
- Fix feature alignment issue (see below)
- Consider hyperparameter tuning
- Expected improvement: 69.74% → 90%+ accuracy

---

## Feature Alignment Issues

### 2. Feature Count Mismatch (81 vs 70 features)

**Status**: Known issue, handled gracefully

**Details**:
- Model expects: 70 features
- Feature extractor provides: 81 features
- System handles mismatch by padding/truncating features
- Warning logged but doesn't prevent classification

**Impact**:
- May affect classification accuracy
- System continues to function
- Some features may be ignored or padded with zeros

**Workaround**:
- System automatically handles mismatch
- Features are padded/truncated as needed
- Classification still works

**Plan for Fix** (at hackathon deadline):
- Align feature extraction with model training features
- Ensure consistent feature count during training and inference
- Update feature extractor to match model expectations

---

## Data Collection Issues

### 3. Training Data Collection

**Status**: Functional but may need more data

**Details**:
- Minimum required: 1,000 labeled samples
- Current status: Depends on database state
- Auto-labeling based on signature detection
- Manual labeling via API available

**Impact**:
- Training may not be possible if insufficient data
- System collects data automatically during packet capture

**Workaround**:
- Use pre-trained model (classification_model.pkl exists)
- Import CICIDS2018 dataset if needed
- System can work with existing model

---

## Python Environment Issues

### 4. Python 3.14 SSL Compatibility with MongoDB

**Status**: Workaround implemented

**Details**:
- Python 3.14 has SSL/TLS compatibility issues with MongoDB Atlas
- Training script uses JSON file instead of direct MongoDB connection
- MongoDB connection still works for other operations (with warnings)

**Impact**:
- Training must use preprocessed JSON file
- Other MongoDB operations work normally

**Workaround**:
- Training uses: `backend/data/cicids2018_preprocessed_50k.json`
- Avoids SSL issues during training
- MongoDB still used for data collection and storage

---

## Frontend-Backend Integration

### 5. API Endpoint Format Differences

**Status**: Fixed

**Details**:
- Some API endpoints return different formats than frontend expects
- Model info endpoint format mismatch

**Impact**:
- Frontend may show incorrect or missing data
- Some components may not display properly

**Workaround**:
- Fixed: Added `/api/training/model-info` endpoint
- Frontend updated to handle different response formats
- Error handling improved

---

## Performance Considerations

### 6. Model File Size (47.33 MB)

**Status**: Normal, no issue

**Details**:
- Model file: `classification_model.pkl` (47.33 MB)
- Large size is normal for Random Forest with many trees
- Loading time: <1 second typically

**Impact**: 
- None - model loads quickly
- File size is acceptable

---

## Demo-Specific Notes

### 7. Backend Dependencies Not Installed

**Status**: Expected - requires virtual environment

**Details**:
- System verification script may show import errors
- This is expected if virtual environment not activated
- Dependencies need to be installed: `pip install -r requirements.txt`

**Workaround**:
- Activate virtual environment before running
- Install dependencies: `pip install -r backend/requirements.txt`
- Use `start-dev.sh` script which handles setup

---

## Recommended Demo Approach

Given the known issues, here's the recommended approach for the hackathon demo:

1. **Focus on Working Features**:
   - Show training dashboard (even if model not perfect)
   - Display classification metrics (current accuracy is acceptable)
   - Demonstrate packet analysis workflow
   - Show real-time detection capabilities

2. **Acknowledge Limitations**:
   - Mention that accuracy will be improved at deadline
   - Explain that system is functional and demonstrates capabilities
   - Highlight that all core features work

3. **Emphasize Architecture**:
   - Show complete ML pipeline
   - Demonstrate real-time processing
   - Highlight modern tech stack
   - Show scalability potential

4. **Backup Plan**:
   - Have screenshots/videos ready
   - Prepare architecture diagrams
   - Document what works and what's being improved
   - Focus on solution explanation if live demo has issues

---

## Summary

**Critical Issues**: None that prevent demo

**Known Limitations**:
- Model accuracy: 69.74% (will improve at deadline)
- Feature mismatch: Handled gracefully
- Training data: May need more samples

**System Status**: 
- ✅ All core features functional
- ✅ Model loads and makes predictions
- ✅ Frontend-backend integration working
- ✅ Training pipeline complete
- ✅ Evaluation system working

**Ready for Demo**: Yes, with acknowledgment of current limitations

---

## Next Steps (At Hackathon Deadline)

1. Retrain model with full 50K samples
2. Fix feature alignment issue
3. Improve accuracy to 90%+
4. Add more training data if needed
5. Fine-tune hyperparameters

---

**Note**: All known issues are documented and have workarounds. The system is functional and ready for demo with current state.
