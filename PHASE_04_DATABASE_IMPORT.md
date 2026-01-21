# Phase 4: Database Import

## Overview

This phase covers importing the preprocessed subset data into the database (SQLite for hackathon) for efficient access during model training. The import process is optimized for memory efficiency and includes progress monitoring.

## Input/Output

- **Input**: `backend/data/cicids2018_preprocessed_subset.json` (200-400 MB)
- **Output**: Database records in `ids_db` (SQLite)
- **Import Time**: 5-15 minutes for 100K samples

## Step 1: Verify Database Configuration

### 1.1 Check Environment Configuration

```bash
cd backend
cat .env | grep DATABASE
```

**Expected:**
```bash
DATABASE_URL=sqlite:///ids.db
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE_NAME=ids_db
```

**For hackathon**: We'll use SQLite (no MongoDB setup required)

### 1.2 Verify Database File

```bash
ls -lh backend/ids.db
```

**Note**: Database file will be created during import if it doesn't exist.

## Step 2: Prepare Import Script

### 2.1 Verify Import Script Exists

```bash
ls -lh backend/scripts/import_cicids2018.py
```

The import script should:
- Load JSON data in batches
- Insert into database efficiently
- Show progress
- Handle errors gracefully
- Support resume functionality

## Step 3: Run Import

### 3.1 Basic Import Command

```bash
cd backend
source venv/bin/activate
python scripts/import_cicids2018.py \
    --input-file ./data/cicids2018_preprocessed_subset.json \
    --batch-size 5000 \
    --labeled-by hackathon_subset
```

**Parameters:**
- `--input-file`: Preprocessed JSON file
- `--batch-size`: Records per batch (5000 recommended for 16GB RAM)
- `--labeled-by`: Label source identifier

### 3.2 Monitor Import Progress

**Expected output:**
```
Importing CICIDS2018 preprocessed subset...
Input file: ./data/cicids2018_preprocessed_subset.json
Batch size: 5,000
Database: sqlite:///ids.db

Loading data...
Total samples: 100,000

Importing batches...
[████████████████████] 100% | 100,000/100,000 samples

Import complete!
  Total imported: 100,000
  Benign: 60,000
  Malicious: 40,000
  Time elapsed: 8m 32s
  Average rate: 1,923 samples/second
```

### 3.3 Progress Indicators

The script shows:
- Current batch number
- Total batches
- Samples imported
- Estimated time remaining
- Import rate (samples/second)

## Step 4: Verify Import

### 4.1 Check Database Records

```bash
cd backend
source venv/bin/activate
python -c "
from config import Config
from services.data_collector import DataCollector

config = Config()
collector = DataCollector(config)
stats = collector.get_statistics()

print('Database Statistics:')
print(f'  Total samples: {stats.get(\"total_samples\", 0):,}')
print(f'  Labeled samples: {stats.get(\"labeled_samples\", 0):,}')
print(f'  Benign: {stats.get(\"benign_count\", 0):,}')
print(f'  Malicious: {stats.get(\"malicious_count\", 0):,}')
"
```

**Expected output:**
```
Database Statistics:
  Total samples: 100,000
  Labeled samples: 100,000
  Benign: 60,000
  Malicious: 40,000
```

### 4.2 Verify Sample Quality

```bash
python -c "
from config import Config
from services.data_collector import DataCollector

config = Config()
collector = DataCollector(config)

# Get a sample record
sample = collector.get_labeled_samples(label='benign', limit=1)[0]
print('Sample record structure:')
print(f'  Keys: {list(sample.keys())[:10]}...')
print(f'  Features count: {len([k for k in sample.keys() if k != \"label\"])}')
print(f'  Label: {sample.get(\"label\")}')
"
```

**Expected:**
- Sample has all features
- Label is correct
- No missing critical data

### 4.3 Check Database Size

```bash
ls -lh backend/ids.db
```

**Expected:**
- Database file: 50-150 MB (SQLite with 100K samples)
- Size depends on feature count and compression

## Step 5: Optimize Database

### 5.1 Create Indexes

Indexes improve query performance during training:

```bash
python -c "
from config import Config
from services.data_collector import DataCollector

config = Config()
collector = DataCollector(config)

# Indexes are created automatically by DataCollector
# Verify they exist
print('Indexes created automatically')
"
```

### 5.2 Verify Indexes

```bash
# For SQLite
sqlite3 backend/ids.db ".indices training_data"
```

**Expected indexes:**
- `label_1`
- `timestamp_-1`
- `source_ip_1`
- `label_1_timestamp_-1`

## Step 6: Memory Optimization

### 6.1 Batch Size Tuning

**For 16GB RAM:**
- **Recommended**: 5,000 samples per batch
- **If memory issues**: Reduce to 2,000-3,000
- **If plenty of RAM**: Increase to 10,000 for faster import

```bash
# Smaller batches (if memory constrained)
python scripts/import_cicids2018.py \
    --input-file ./data/cicids2018_preprocessed_subset.json \
    --batch-size 2000 \
    --labeled-by hackathon_subset

# Larger batches (if memory available)
python scripts/import_cicids2018.py \
    --input-file ./data/cicids2018_preprocessed_subset.json \
    --batch-size 10000 \
    --labeled-by hackathon_subset
```

### 6.2 Monitor Memory Usage

```bash
# Linux/Mac
top -p $(pgrep -f import_cicids2018)

# Check memory usage
free -h  # Linux
vm_stat  # Mac
```

**Expected:**
- Peak memory: 2-4 GB during import
- Should stay well within 16GB limit

## Step 7: Resume Import (If Interrupted)

### 7.1 Check Import Status

```bash
python scripts/check_import_progress.py
```

### 7.2 Resume Import

If import was interrupted, resume from last checkpoint:

```bash
python scripts/import_cicids2018.py \
    --input-file ./data/cicids2018_preprocessed_subset.json \
    --batch-size 5000 \
    --labeled-by hackathon_subset \
    --resume
```

**Note**: Resume functionality skips already imported samples.

## Step 8: Troubleshooting

### Issue: Database Locked

**Solution**: Close other database connections
```bash
# Check for other processes
ps aux | grep python | grep import
# Kill if needed
kill <process_id>
```

### Issue: Out of Memory

**Solution**: Reduce batch size
```bash
--batch-size 2000  # Use smaller batches
```

### Issue: Import Too Slow

**Solution**: 
- Increase batch size (if memory allows)
- Close other applications
- Use SSD storage for database

### Issue: Duplicate Records

**Solution**: Use `--resume` flag to skip existing records
```bash
--resume
```

### Issue: SQLite Error

**Solution**: Check database file permissions
```bash
chmod 644 backend/ids.db
chmod 755 backend/
```

### Issue: Missing Features in Database

**Solution**: Verify preprocessing output
```bash
python -c "import json; data = json.load(open('data/cicids2018_preprocessed_subset.json')); print(list(data[0].keys())[:10])"
```

## Step 9: Verify Data Integrity

### 9.1 Compare Counts

```bash
# Count in JSON file
python -c "import json; data = json.load(open('data/cicids2018_preprocessed_subset.json')); print(f'JSON samples: {len(data):,}')"

# Count in database
python -c "
from config import Config
from services.data_collector import DataCollector
config = Config()
collector = DataCollector(config)
stats = collector.get_statistics()
print(f'Database samples: {stats.get(\"total_samples\", 0):,}')
"
```

**Expected**: Counts should match

### 9.2 Verify Label Distribution

```bash
python -c "
from config import Config
from services.data_collector import DataCollector
from collections import Counter

config = Config()
collector = DataCollector(config)

# Get all labels
benign = collector.get_labeled_samples(label='benign', limit=None)
malicious = collector.get_labeled_samples(label='malicious', limit=None)

print(f'Benign: {len(benign):,}')
print(f'Malicious: {len(malicious):,}')
print(f'Total: {len(benign) + len(malicious):,}')
"
```

**Expected**: Matches original distribution (60% benign, 40% malicious)

## Verification Checklist

- [ ] Import script executed successfully
- [ ] All samples imported (50K-100K)
- [ ] Database file created/updated
- [ ] Database statistics verified
- [ ] Sample records verified (structure and content)
- [ ] Label distribution matches expected (60/40)
- [ ] Indexes created successfully
- [ ] No duplicate records
- [ ] Data integrity verified (JSON count = DB count)
- [ ] Memory usage within limits

## File Locations

- **Input**: `backend/data/cicids2018_preprocessed_subset.json`
- **Database**: `backend/ids.db` (SQLite)
- **Import Script**: `backend/scripts/import_cicids2018.py`
- **Progress Check**: `backend/scripts/check_import_progress.py`

## Next Steps

Once import is complete and verified, proceed to:
- **Phase 5**: Model Training - Train Random Forest classifier on imported data

## Estimated Time

- **Import**: 5-15 minutes (for 100K samples)
- **Verification**: 5 minutes
- **Total**: 10-20 minutes

## Notes

- SQLite is used for simplicity (no server setup)
- Batch import optimizes memory usage
- Progress monitoring helps track long imports
- Resume functionality allows recovery from interruptions
- Indexes improve training query performance
- Database will be used for model training in next phase
