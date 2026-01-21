# Phase 3: Data Preprocessing

## Overview

This phase covers preprocessing the CICIDS2018 subset data: extracting features, cleaning data, handling missing values, and preparing it for model training. The preprocessing will convert the CSV subset into a format suitable for machine learning.

## Input/Output

- **Input**: `backend/data/cicids2018_subset.csv` (50K-100K samples)
- **Output**: `backend/data/cicids2018_preprocessed_subset.json` (~200-400 MB)
- **Processing Time**: 10-20 minutes for 100K samples

## Step 1: Review Preprocessing Requirements

The preprocessing script will:
1. Load CSV subset file
2. Extract 80+ features from network flow data
3. Handle missing values and invalid data
4. Normalize feature names
5. Convert to JSON format for efficient loading
6. Validate data integrity

## Step 2: Run Preprocessing Script

### 2.1 Basic Preprocessing

```bash
cd backend
source venv/bin/activate
python scripts/preprocess_cicids2018.py \
    --input-file ./data/cicids2018_subset.csv \
    --output-file ./data/cicids2018_preprocessed_subset.json \
    --chunk-size 10000
```

**Parameters:**
- `--input-file`: Input CSV subset file
- `--output-file`: Output JSON file for preprocessed data
- `--chunk-size`: Process in chunks to manage memory (default: 10000)

### 2.2 Monitor Progress

The script will display progress:
```
Preprocessing CICIDS2018 subset...
Loading data from: ./data/cicids2018_subset.csv
Total samples: 100,000

Processing chunks...
[████████████████████] 100% | 100,000/100,000 samples

Extracting features...
[████████████████████] 100% | 100,000/100,000 samples

Cleaning data...
Removed 0 invalid samples
Removed 0 samples with missing critical features

Saving preprocessed data...
Writing to: ./data/cicids2018_preprocessed_subset.json

Preprocessing complete!
  Input samples: 100,000
  Output samples: 100,000
  Features per sample: 80
  Output file size: 350 MB
```

### 2.3 Expected Output

- **File**: `backend/data/cicids2018_preprocessed_subset.json`
- **Format**: JSON array of samples
- **Size**: 200-400 MB (depending on sample count)
- **Structure**: Each sample contains features and label

## Step 3: Verify Preprocessing Output

### 3.1 Check File Exists and Size

```bash
cd backend/data
ls -lh cicids2018_preprocessed_subset.json
```

**Expected:**
- File exists
- Size: 200-400 MB

### 3.2 Validate JSON Structure

```bash
cd backend
source venv/bin/activate
python -c "
import json
with open('data/cicids2018_preprocessed_subset.json', 'r') as f:
    data = json.load(f)
    print(f'Total samples: {len(data):,}')
    print(f'Sample keys: {list(data[0].keys())[:10]}')
    print(f'Features count: {len([k for k in data[0].keys() if k != \"label\"])}')
    print(f'Label: {data[0].get(\"label\", \"N/A\")}')
"
```

**Expected output:**
```
Total samples: 100,000
Sample keys: ['label', 'feature_1', 'feature_2', ...]
Features count: 80
Label: Benign
```

### 3.3 Check Label Distribution

```bash
python -c "
import json
from collections import Counter

with open('data/cicids2018_preprocessed_subset.json', 'r') as f:
    data = json.load(f)
    labels = [sample['label'] for sample in data]
    label_counts = Counter(labels)
    
    print('Label distribution:')
    for label, count in label_counts.most_common():
        pct = (count / len(labels)) * 100
        print(f'  {label}: {count:,} ({pct:.1f}%)')
"
```

**Expected:**
- ~60% Benign samples
- ~40% Malicious samples (various attack types)
- Balanced distribution

## Step 4: Feature Extraction Details

### 4.1 Core Features Extracted

The preprocessing extracts 80+ features including:

**Flow Features:**
- Source/Destination IP and Port
- Protocol type
- Flow duration
- Packet counts (forward/backward)
- Byte counts (forward/backward)

**Statistical Features:**
- Packet size statistics (mean, std, min, max)
- Inter-arrival time statistics
- Flow rate statistics

**TCP Features:**
- TCP flags
- Window size
- Segment statistics

**Application Layer:**
- HTTP methods
- DNS query types
- SSH/FTP command patterns

### 4.2 Feature Normalization

- **Numeric features**: Converted to float
- **Missing values**: Handled (filled with 0 or mean)
- **Invalid values**: Removed or corrected
- **Feature names**: Standardized format

## Step 5: Data Quality Checks

### 5.1 Run Validation Script

```bash
python scripts/validate_preprocessed.py \
    --input-file ./data/cicids2018_preprocessed_subset.json \
    --output-report validation_report_subset.json
```

**Expected output:**
```json
{
  "valid_json": true,
  "total_samples": 100000,
  "features_per_sample": 80,
  "label_distribution": {
    "Benign": 60000,
    "DoS attacks-Hulk": 15000,
    "DDoS attacks-LOIC-HTTP": 10000,
    ...
  },
  "missing_values": 0,
  "invalid_samples": 0
}
```

### 5.2 Check for Issues

**Common issues to check:**
- Missing critical features
- Invalid label values
- Out-of-range numeric values
- Duplicate samples

## Step 6: Memory Optimization

### 6.1 Chunk Processing

If memory is limited, process in smaller chunks:

```bash
python scripts/preprocess_cicids2018.py \
    --input-file ./data/cicids2018_subset.csv \
    --output-file ./data/cicids2018_preprocessed_subset.json \
    --chunk-size 5000
```

### 6.2 Monitor Memory Usage

```bash
# Linux/Mac
top -p $(pgrep -f preprocess_cicids2018)

# Or use htop
htop -p $(pgrep -f preprocess_cicids2018)
```

**Expected memory usage:**
- 2-4 GB during processing
- Should stay within 16GB RAM limit

## Step 7: Troubleshooting

### Issue: Out of Memory

**Solution**: Reduce chunk size
```bash
--chunk-size 5000  # Use smaller chunks
```

### Issue: Invalid JSON Output

**Solution**: Check for corrupted input file
```bash
python -c "import pandas as pd; df = pd.read_csv('data/cicids2018_subset.csv', nrows=10); print(df.head())"
```

### Issue: Missing Features

**Solution**: Verify input CSV has all required columns
```bash
head -1 data/cicids2018_subset.csv | tr ',' '\n' | wc -l
# Should show 80+ columns
```

### Issue: Processing Too Slow

**Solution**: 
- Use smaller subset (50K instead of 100K)
- Increase chunk size if memory allows
- Close other applications

### Issue: Labels Not Preserved

**Solution**: Verify 'Label' column exists in input CSV
```bash
head -1 data/cicids2018_subset.csv | grep -i label
```

## Step 8: Backup Preprocessed Data

```bash
cd backend/data
cp cicids2018_preprocessed_subset.json cicids2018_preprocessed_subset.json.backup
```

**Why backup?**
- Preprocessing takes time
- Backup allows quick recovery if needed
- Can experiment with different preprocessing settings

## Verification Checklist

- [ ] Preprocessing script executed successfully
- [ ] Output file created: `backend/data/cicids2018_preprocessed_subset.json`
- [ ] Output file size: 200-400 MB
- [ ] JSON structure valid (can be loaded)
- [ ] Sample count matches input (50K-100K)
- [ ] Features per sample: 80+
- [ ] Label distribution verified (60% benign, 40% malicious)
- [ ] No missing critical features
- [ ] Validation report generated successfully
- [ ] Backup created

## File Locations

- **Input**: `backend/data/cicids2018_subset.csv`
- **Output**: `backend/data/cicids2018_preprocessed_subset.json`
- **Validation Report**: `backend/validation_report_subset.json`
- **Preprocessing Script**: `backend/scripts/preprocess_cicids2018.py`

## Next Steps

Once preprocessing is complete and verified, proceed to:
- **Phase 4**: Database Import - Import preprocessed data to database for training

## Estimated Time

- **Preprocessing**: 10-20 minutes (for 100K samples)
- **Verification**: 5 minutes
- **Total**: 15-25 minutes

## Notes

- Preprocessing is a one-time operation
- Output JSON is optimized for fast loading during training
- Feature extraction preserves all important network flow characteristics
- Data quality checks ensure training data integrity
- Backup recommended before proceeding to next phase
