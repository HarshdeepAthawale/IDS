# Phase 2: Data Preparation

## Overview

This phase covers downloading the CICIDS2018 dataset (if not already present) and creating a balanced subset of 50,000 samples optimized for local training on i5 12th gen with 16GB RAM.

## Dataset Information

- **Full Dataset**: CICIDS2018 (8M+ samples, 2.73 GB)
- **Subset Size**: 50,000 samples (optimized for hackathon)
- **Distribution**: 60% benign (30,000), 40% malicious (20,000)
- **Estimated Size**: 100-150 MB preprocessed
- **Training Time**: 5-10 minutes on i5 12th gen

## Step 1: Verify Existing Dataset

### Check if Dataset Files Exist

```bash
cd backend/data/cicids2018
ls -lh *.csv
```

**Expected files** (10 CSV files):
- `Friday-02-03-2018_TrafficForML_CICFlowMeter.csv`
- `Friday-16-02-2018_TrafficForML_CICFlowMeter.csv`
- `Friday-23-02-2018_TrafficForML_CICFlowMeter.csv`
- `Thuesday-20-02-2018_TrafficForML_CICFlowMeter.csv`
- `Thursday-01-03-2018_TrafficForML_CICFlowMeter.csv`
- `Thursday-15-02-2018_TrafficForML_CICFlowMeter.csv`
- `Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv`
- `Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv`
- `Wednesday-21-02-2018_TrafficForML_CICFlowMeter.csv`
- `Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv`

**If files exist**: Skip to Step 3 (Create Subset)

**If files missing**: Proceed to Step 2 (Download)

## Step 2: Download Dataset (If Needed)

### Option A: Manual Download

1. Visit: https://www.unb.ca/cic/datasets/ids-2018.html
2. Download all 10 CSV files
3. Place them in `backend/data/cicids2018/` directory

### Option B: Using Download Script

```bash
cd backend
source venv/bin/activate
python scripts/download_cicids2018.py --output-dir ./data/cicids2018
```

**Note**: Download may take 30-60 minutes depending on internet speed (2.73 GB total).

## Step 3: Create Training Subset

### 3.1 Run Subset Creation Script

```bash
cd backend
source venv/bin/activate
python scripts/create_training_subset.py \
    --input-dir ./data/cicids2018 \
    --output-file ./data/cicids2018_subset_50k.csv \
    --total-samples 50000 \
    --benign-ratio 0.6
```

**Parameters:**
- `--input-dir`: Directory containing CICIDS2018 CSV files
- `--output-file`: Output CSV file for subset
- `--total-samples`: Total number of samples (50000-100000 recommended)
- `--benign-ratio`: Ratio of benign samples (0.6 = 60%)

**Note**: For hackathon, 50K samples provides optimal balance of speed and accuracy.

### 3.2 Verify Subset Creation

The script will:
1. Load all CSV files
2. Identify benign and malicious samples
3. Sample balanced subset maintaining class distribution
4. Save to output CSV file
5. Display statistics

**Expected output:**
```
Creating training subset...
Loading dataset files...
Found 8,034,453 total samples
  Benign: 5,464,680 (68.0%)
  Malicious: 2,569,773 (32.0%)

Creating balanced subset...
  Total samples: 100,000
  Benign samples: 60,000 (60.0%)
  Malicious samples: 40,000 (40.0%)

Saving subset to: ./data/cicids2018_subset.csv
Subset created successfully!
```

### 3.3 Verify Subset File

```bash
cd backend/data
ls -lh cicids2018_subset.csv
wc -l cicids2018_subset.csv
```

**Expected:**
- File size: ~100-150 MB
- Line count: 50,001 (header + 50,000 samples)

## Step 4: Verify Data Quality

### 4.1 Check File Structure

```bash
cd backend
source venv/bin/activate
python -c "
import pandas as pd
df = pd.read_csv('data/cicids2018_subset.csv', nrows=5)
print('Columns:', len(df.columns))
print('Sample rows:')
print(df.head())
print('\nLabel distribution:')
print(df['Label'].value_counts())
"
```

**Expected:**
- 80+ columns (features)
- `Label` column present
- Mix of 'Benign' and attack types

### 4.2 Check Label Distribution

```bash
python scripts/analyze_cicids2018.py --input-file ./data/cicids2018_subset.csv
```

**Expected output:**
- Balanced distribution (60% benign, 40% malicious)
- Multiple attack types represented
- No missing values in critical columns

## Step 5: Sample Selection Strategy

The subset script uses the following strategy:

1. **Stratified Sampling**: Maintains class distribution from original dataset
2. **Random Selection**: Randomly samples from each class
3. **Attack Type Diversity**: Includes various attack types proportionally
4. **Temporal Distribution**: Samples from different days/files

### Attack Types in Subset

The subset will include:
- **Benign**: Normal network traffic
- **DoS attacks**: Hulk, GoldenEye, Slowloris, SlowHTTPTest
- **DDoS attacks**: LOIC-HTTP, LOIC-UDP, HOIC
- **Brute Force**: FTP, SSH, Web, XSS
- **Infiltration**: Network infiltration attempts
- **Bot**: Botnet traffic
- **SQL Injection**: SQL injection attempts

## Step 6: Troubleshooting

### Issue: Out of Memory During Subset Creation

**Solution**: Process files in chunks
```bash
python scripts/create_training_subset.py \
    --input-dir ./data/cicids2018 \
    --output-file ./data/cicids2018_subset.csv \
    --total-samples 50000 \
    --chunk-size 10000
```

### Issue: Missing Label Column

**Solution**: Verify CSV files have 'Label' column
```bash
head -1 backend/data/cicids2018/*.csv | grep -i label
```

### Issue: Imbalanced Subset

**Solution**: Check benign-ratio parameter
- Increase `--benign-ratio` for more benign samples
- Decrease for more malicious samples

### Issue: File Too Large

**Solution**: Reduce total samples
```bash
--total-samples 50000  # Use 50K instead of 100K
```

## Verification Checklist

- [ ] Dataset files present in `backend/data/cicids2018/`
- [ ] Subset creation script executed successfully
- [ ] Subset file created: `backend/data/cicids2018_subset.csv`
- [ ] Subset file size: 100-150 MB
- [ ] Subset contains 50,000 samples
- [ ] Label distribution verified (60% benign, 40% malicious)
- [ ] No missing values in critical columns
- [ ] Multiple attack types represented

## File Locations

- **Full Dataset**: `backend/data/cicids2018/*.csv`
- **Subset File**: `backend/data/cicids2018_subset_50k.csv`
- **Subset Script**: `backend/scripts/create_training_subset.py`

## Next Steps

Once subset is created and verified, proceed to:
- **Phase 3**: Data Preprocessing - Extract features and prepare for training

## Estimated Time

- **Download (if needed)**: 30-60 minutes
- **Subset creation**: 5-10 minutes
- **Verification**: 5 minutes

**Total**: 10-75 minutes (depending on download)

## Notes

- The subset maintains class balance for better model performance
- 50K samples is optimal for hackathon: fast training (~5-10 min) with good accuracy (95%+)
- 60:40 ratio (30K benign, 20K malicious) provides balanced training data
