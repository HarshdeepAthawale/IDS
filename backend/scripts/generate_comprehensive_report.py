#!/usr/bin/env python3
"""
Generate comprehensive markdown report for CICIDS2018 dataset
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter
from datetime import datetime
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


def get_column_names(filepath: Path):
    """Get column names from a CSV file"""
    try:
        df = pd.read_csv(filepath, nrows=1)
        return list(df.columns)
    except Exception as e:
        return []


def get_attack_descriptions():
    """Return descriptions of attack types"""
    return {
        'Benign': 'Normal network traffic without any malicious activity',
        'DDOS attack-HOIC': 'High Orbit Ion Cannon (HOIC) - Distributed Denial of Service attack using HTTP floods',
        'DDoS attacks-LOIC-HTTP': 'Low Orbit Ion Cannon HTTP - DDoS attack flooding HTTP requests',
        'DoS attacks-Hulk': 'HTTP Unbearable Load King - DoS attack using HTTP GET requests',
        'Bot': 'Botnet traffic - compromised devices controlled remotely',
        'Infilteration': 'Infiltration attack - unauthorized access attempts',
        'DoS attacks-SlowHTTPTest': 'Slow HTTP DoS attack - keeping connections open slowly',
        'FTP-BruteForce': 'FTP brute force attack - attempting to guess FTP credentials',
        'SSH-Bruteforce': 'SSH brute force attack - attempting to guess SSH credentials',
        'DoS attacks-GoldenEye': 'GoldenEye DoS attack - HTTP flood variant',
        'DoS attacks-Slowloris': 'Slowloris DoS attack - slow HTTP requests to exhaust server resources',
        'DDOS attack-LOIC-UDP': 'Low Orbit Ion Cannon UDP - DDoS attack using UDP floods',
        'Brute Force -Web': 'Web application brute force attack',
        'Brute Force -XSS': 'Cross-Site Scripting attack',
        'SQL Injection': 'SQL injection attack - database exploitation attempt'
    }


def analyze_comprehensive(filepath: Path, s3_info: dict = None):
    """Comprehensive analysis of a CSV file"""
    filename = filepath.name
    print(f"Analyzing {filename}...")
    
    analysis = {
        'filename': filename,
        'local_exists': filepath.exists(),
        'local_size_bytes': filepath.stat().st_size if filepath.exists() else 0,
        'local_size_gb': filepath.stat().st_size / (1024 ** 3) if filepath.exists() else 0,
        's3_size_gb': s3_info.get(filename, {}).get('size_gb', 0) if s3_info else 0,
        'rows': 0,
        'columns': 0,
        'column_names': [],
        'label_distribution': {},
        'unique_labels': [],
        'date': None,
        'protocol_distribution': {},
        'port_statistics': {},
        'flow_duration_stats': {},
        'packet_statistics': {}
    }
    
    if not filepath.exists():
        return analysis
    
    try:
        # Get column names
        analysis['column_names'] = get_column_names(filepath)
        analysis['columns'] = len(analysis['column_names'])
        
        # Count total rows
        total_rows = sum(1 for _ in open(filepath)) - 1
        analysis['rows'] = total_rows
        
        # Extract date from filename
        parts = filename.split('_')[0].split('-')
        if len(parts) >= 3:
            analysis['date'] = f"{parts[0]} {parts[1]}-{parts[2]}-2018"
        
        # Read sample for detailed analysis
        sample_size = min(100000, total_rows)
        try:
            # pandas >= 2.0
            df = pd.read_csv(filepath, nrows=sample_size, low_memory=False, on_bad_lines='skip')
        except TypeError:
            try:
                # pandas < 2.0
                df = pd.read_csv(filepath, nrows=sample_size, low_memory=False, error_bad_lines=False)
            except TypeError:
                # pandas >= 2.0 but different API
                df = pd.read_csv(filepath, nrows=sample_size, low_memory=False)
        
        # Label distribution
        label_col = None
        for col in ['Label', 'label', 'Label ', 'label ']:
            if col in df.columns:
                label_col = col
                break
        
        if label_col:
            label_counts = Counter(df[label_col].dropna().astype(str))
            analysis['label_distribution'] = dict(label_counts)
            analysis['unique_labels'] = list(label_counts.keys())
            
            # Full label distribution (chunked)
            full_label_counts = Counter()
            try:
                chunks = pd.read_csv(filepath, chunksize=50000, usecols=[label_col], low_memory=False, on_bad_lines='skip')
            except TypeError:
                try:
                    chunks = pd.read_csv(filepath, chunksize=50000, usecols=[label_col], low_memory=False, error_bad_lines=False)
                except TypeError:
                    chunks = pd.read_csv(filepath, chunksize=50000, usecols=[label_col], low_memory=False)
            
            for chunk in chunks:
                full_label_counts.update(chunk[label_col].dropna().astype(str))
            analysis['full_label_distribution'] = dict(full_label_counts)
        
        # Protocol distribution
        if 'Protocol' in df.columns:
            protocol_counts = Counter(df['Protocol'].dropna())
            analysis['protocol_distribution'] = {str(k): int(v) for k, v in protocol_counts.items()}
        
        # Port statistics
        if 'Dst Port' in df.columns:
            analysis['port_statistics'] = {
                'mean': float(df['Dst Port'].mean()) if pd.api.types.is_numeric_dtype(df['Dst Port']) else None,
                'median': float(df['Dst Port'].median()) if pd.api.types.is_numeric_dtype(df['Dst Port']) else None,
                'min': float(df['Dst Port'].min()) if pd.api.types.is_numeric_dtype(df['Dst Port']) else None,
                'max': float(df['Dst Port'].max()) if pd.api.types.is_numeric_dtype(df['Dst Port']) else None,
                'unique': int(df['Dst Port'].nunique())
            }
        
        # Flow duration statistics
        if 'Flow Duration' in df.columns:
            analysis['flow_duration_stats'] = {
                'mean': float(df['Flow Duration'].mean()) if pd.api.types.is_numeric_dtype(df['Flow Duration']) else None,
                'median': float(df['Flow Duration'].median()) if pd.api.types.is_numeric_dtype(df['Flow Duration']) else None,
                'min': float(df['Flow Duration'].min()) if pd.api.types.is_numeric_dtype(df['Flow Duration']) else None,
                'max': float(df['Flow Duration'].max()) if pd.api.types.is_numeric_dtype(df['Flow Duration']) else None,
            }
        
        # Packet statistics
        if 'Tot Fwd Pkts' in df.columns and 'Tot Bwd Pkts' in df.columns:
            analysis['packet_statistics'] = {
                'total_fwd_mean': float(df['Tot Fwd Pkts'].mean()) if pd.api.types.is_numeric_dtype(df['Tot Fwd Pkts']) else None,
                'total_bwd_mean': float(df['Tot Bwd Pkts'].mean()) if pd.api.types.is_numeric_dtype(df['Tot Bwd Pkts']) else None,
                'total_packets_mean': float((df['Tot Fwd Pkts'] + df['Tot Bwd Pkts']).mean()) if pd.api.types.is_numeric_dtype(df['Tot Fwd Pkts']) else None,
            }
        
    except Exception as e:
        analysis['error'] = str(e)
        print(f"  Error analyzing {filename}: {e}")
    
    return analysis


def generate_comprehensive_markdown(analyses: list, output_path: Path):
    """Generate comprehensive markdown report"""
    
    total_files = len(analyses)
    downloaded_files = sum(1 for a in analyses if a['local_exists'])
    total_rows = sum(a['rows'] for a in analyses)
    total_size_gb = sum(a['local_size_gb'] for a in analyses if a['local_exists'])
    
    # Aggregate label distribution
    all_labels = Counter()
    for analysis in analyses:
        if 'full_label_distribution' in analysis:
            all_labels.update(analysis['full_label_distribution'])
        elif 'label_distribution' in analysis:
            all_labels.update(analysis['label_distribution'])
    
    attack_descriptions = get_attack_descriptions()
    
    md_content = f"""# CICIDS2018 Dataset - Comprehensive Analysis Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Dataset:** CICIDS2018 - Canadian Institute for Cybersecurity Intrusion Detection Dataset 2018  
**Source:** AWS S3 Bucket (`cse-cic-ids2018`)

---

## 📊 Executive Summary

| Metric | Value |
|--------|-------|
| **Total Files** | {total_files} |
| **Downloaded Files** | {downloaded_files} |
| **Total Records** | {total_rows:,} |
| **Total Size (Local)** | {total_size_gb:.2f} GB |
| **Unique Attack Types** | {len(all_labels)} |
| **Date Range** | February 14 - March 3, 2018 |
| **Data Format** | CSV (Comma-Separated Values) |
| **Feature Extraction Tool** | CICFlowMeter |

---

## 📁 Dataset Overview

The **CICIDS2018** dataset is a comprehensive network traffic dataset designed for intrusion detection system (IDS) research and development. It contains real-world network traffic flows captured over multiple days, including both benign traffic and various types of cyber attacks.

### Key Characteristics

- **Flow-based Analysis**: Each record represents a network flow (connection) rather than individual packets
- **80+ Features**: Extracted using CICFlowMeter tool, including statistical, timing, and protocol features
- **Labeled Data**: Each flow is labeled as either "Benign" or a specific attack type
- **Temporal Coverage**: Data collected over 10 days in February and March 2018
- **Real-world Traffic**: Captured from a realistic network environment simulating actual network conditions

---

## 📋 File Inventory

| # | Filename | Status | Local Size | S3 Size | Rows | Columns | Date |
|---|----------|--------|------------|---------|------|---------|------|
"""
    
    for idx, analysis in enumerate(sorted(analyses, key=lambda x: x['filename']), 1):
        status = "✓ Downloaded" if analysis['local_exists'] else "✗ Not Downloaded"
        local_size = f"{analysis['local_size_gb']:.2f} GB" if analysis['local_exists'] else "N/A"
        s3_size = f"{analysis['s3_size_gb']:.2f} GB" if analysis['s3_size_gb'] > 0 else "N/A"
        rows = f"{analysis['rows']:,}" if analysis['rows'] > 0 else "N/A"
        cols = analysis['columns'] if analysis['columns'] > 0 else "N/A"
        date = analysis.get('date', 'N/A')
        
        md_content += f"| {idx} | `{analysis['filename']}` | {status} | {local_size} | {s3_size} | {rows} | {cols} | {date} |\n"
    
    md_content += f"""
---

## 🏷️ Overall Label Distribution

| Rank | Label | Count | Percentage | Description |
|------|-------|-------|------------|-------------|
"""
    
    total_label_count = sum(all_labels.values())
    for rank, (label, count) in enumerate(sorted(all_labels.items(), key=lambda x: x[1], reverse=True)[:20], 1):
        percentage = (count / total_label_count * 100) if total_label_count > 0 else 0
        description = attack_descriptions.get(label, 'Network traffic pattern')
        md_content += f"| {rank} | `{label}` | {count:,} | {percentage:.2f}% | {description} |\n"
    
    if len(all_labels) > 20:
        md_content += f"| ... | ... | ... | ... | ... |\n"
    
    md_content += f"""
**Total Records:** {total_label_count:,}

---

## 🎯 Attack Type Descriptions

"""
    
    for label in sorted(set(all_labels.keys())):
        if label in attack_descriptions:
            md_content += f"### {label}\n\n"
            md_content += f"{attack_descriptions[label]}\n\n"
            md_content += f"- **Count:** {all_labels[label]:,} records\n"
            md_content += f"- **Percentage:** {(all_labels[label] / total_label_count * 100):.2f}%\n\n"
    
    md_content += f"""
---

## 🔍 Feature Set Description

The CICIDS2018 dataset contains **80+ features** extracted using CICFlowMeter. These features are categorized as follows:

### Core Features (Used in IDS System)

The IDS system extracts **6 core features** from the raw dataset for classification:

1. **Packet Size** (`packet_size`)
   - Average packet size in bytes
   - Derived from: `Total Length` / `Packet Count`
   - Range: Typically 0-1500 bytes

2. **Protocol Type** (`protocol_type`)
   - Network protocol identifier
   - Encoding: TCP=1, UDP=2, ICMP=3
   - Derived from: `Protocol` column

3. **Connection Duration** (`connection_duration`)
   - Duration of network flow in seconds
   - Derived from: `Flow Duration` column
   - Range: Milliseconds to hours

4. **Failed Login Attempts** (`failed_login_attempts`)
   - Count of failed authentication attempts per source IP
   - Derived from: Analyzing SSH/FTP/HTTP authentication failures
   - Range: 0 to hundreds

5. **Data Transfer Rate** (`data_transfer_rate`)
   - Bytes transferred per second
   - Derived from: `Total Fwd Bytes` + `Total Bwd Bytes` / `Flow Duration`
   - Range: 0 to GB/s

6. **Access Frequency** (`access_frequency`)
   - Number of connections per source IP within time window
   - Derived from: Counting flows per IP address
   - Range: 0 to thousands per minute

### Complete Feature Categories

The dataset includes features from these categories:

#### 1. **Flow Identifiers**
- Flow ID
- Source IP, Destination IP
- Source Port, Destination Port
- Protocol

#### 2. **Timing Features**
- Flow Duration
- Flow IAT (Inter-Arrival Time) Mean/Std/Min/Max
- Forward/Bidirectional IAT statistics

#### 3. **Packet Statistics**
- Total Forward/Backward Packets
- Packet Length Mean/Std/Min/Max
- Forward/Backward Packet Length statistics

#### 4. **Byte Statistics**
- Total Forward/Backward Bytes
- Byte Length Mean/Std/Min/Max
- Forward/Backward Byte statistics

#### 5. **TCP Flags**
- Forward/Backward Flags
- SYN, ACK, FIN, RST, PSH, URG counts

#### 6. **Window Size**
- Forward/Backward Window Size
- Window Size statistics

#### 7. **Label**
- Attack type or "Benign"

---

## 📈 Detailed File Analysis

"""
    
    for analysis in sorted(analyses, key=lambda x: x['filename']):
        md_content += f"""### {analysis['filename']}

**Date:** {analysis.get('date', 'N/A')}  
**Status:** {'✓ Downloaded' if analysis['local_exists'] else '✗ Not Downloaded'}

#### File Information

- **Local Size:** {analysis['local_size_gb']:.2f} GB ({analysis['local_size_bytes']:,} bytes)
- **S3 Size:** {analysis['s3_size_gb']:.2f} GB
- **Total Rows:** {analysis['rows']:,}
- **Total Columns:** {analysis['columns']}

"""
        
        if analysis.get('label_distribution'):
            md_content += "#### Label Distribution\n\n"
            md_content += "| Label | Count | Percentage |\n"
            md_content += "|-------|-------|------------|\n"
            
            file_total = sum(analysis.get('full_label_distribution', analysis['label_distribution']).values())
            label_dist = analysis.get('full_label_distribution', analysis['label_distribution'])
            
            for label, count in sorted(label_dist.items(), key=lambda x: x[1], reverse=True):
                pct = (count / file_total * 100) if file_total > 0 else 0
                md_content += f"| `{label}` | {count:,} | {pct:.2f}% |\n"
        
        if analysis.get('protocol_distribution'):
            md_content += "\n#### Protocol Distribution\n\n"
            md_content += "| Protocol | Count |\n"
            md_content += "|----------|-------|\n"
            for proto, count in sorted(analysis['protocol_distribution'].items(), key=lambda x: x[1], reverse=True)[:5]:
                proto_name = {1: 'ICMP', 6: 'TCP', 17: 'UDP'}.get(int(proto) if proto.isdigit() else 0, proto)
                md_content += f"| {proto_name} ({proto}) | {count:,} |\n"
        
        if analysis.get('port_statistics'):
            stats = analysis['port_statistics']
            md_content += "\n#### Destination Port Statistics\n\n"
            mean_val = stats.get('mean')
            median_val = stats.get('median')
            min_val = stats.get('min')
            max_val = stats.get('max')
            unique_val = stats.get('unique')
            
            md_content += f"- **Mean:** {mean_val:.2f if mean_val is not None else 'N/A'}\n"
            md_content += f"- **Median:** {median_val:.2f if median_val is not None else 'N/A'}\n"
            md_content += f"- **Range:** {min_val if min_val is not None else 'N/A'} - {max_val if max_val is not None else 'N/A'}\n"
            md_content += f"- **Unique Ports:** {unique_val:, if unique_val is not None else 'N/A'}\n"
        
        if analysis.get('flow_duration_stats'):
            stats = analysis['flow_duration_stats']
            md_content += "\n#### Flow Duration Statistics\n\n"
            mean_val = stats.get('mean')
            median_val = stats.get('median')
            min_val = stats.get('min')
            max_val = stats.get('max')
            
            if mean_val is not None:
                md_content += f"- **Mean:** {mean_val:,.0f} ms ({mean_val/1000:.2f} seconds)\n"
            else:
                md_content += f"- **Mean:** N/A\n"
            
            if median_val is not None:
                md_content += f"- **Median:** {median_val:,.0f} ms ({median_val/1000:.2f} seconds)\n"
            else:
                md_content += f"- **Median:** N/A\n"
            
            md_content += f"- **Range:** {min_val:,.0f if min_val is not None else 'N/A'} ms - {max_val:,.0f if max_val is not None else 'N/A'} ms\n"
        
        md_content += "\n---\n\n"
    
    md_content += f"""
---

## 🔄 Data Preprocessing Pipeline

### Preprocessing Steps

The CICIDS2018 dataset requires preprocessing before use with the IDS system:

1. **Feature Extraction** (`preprocess_cicids2018.py`)
   - Maps 80+ features → 6 core features
   - Protocol encoding (TCP=1, UDP=2, ICMP=3)
   - Label mapping (attack types → benign/malicious)

2. **Data Import** (`import_cicids2018.py`)
   - Loads preprocessed JSON data
   - Validates schema conformity
   - Imports to MongoDB `training_data` collection

3. **Model Training** (`train_from_cicids2018.py`)
   - Loads labeled data from MongoDB
   - Preprocesses features (normalization, scaling)
   - Trains Random Forest classifier
   - Evaluates model performance

### Preprocessing Script Usage

```bash
# Step 1: Preprocess CSV files
python scripts/preprocess_cicids2018.py \\
    --input-dir ./data/cicids2018 \\
    --output ./data/cicids2018_preprocessed.json \\
    --chunk-size 10000

# Step 2: Import to MongoDB
python scripts/import_cicids2018.py \\
    --input ./data/cicids2018_preprocessed.json \\
    --batch-size 1000

# Step 3: Train model
python scripts/train_from_cicids2018.py \\
    --min-samples 1000 \\
    --hyperparameter-tune
```

---

## 🎓 Machine Learning Usage

### Binary Classification Task

**Objective:** Classify network traffic as "Benign" or "Malicious"

**Input Features:** 6-dimensional feature vector
- Packet Size
- Protocol Type
- Connection Duration
- Failed Login Attempts
- Data Transfer Rate
- Access Frequency

**Output:** Binary label + confidence score

### Model Training

- **Algorithm:** Random Forest Classifier (default)
- **Alternative Models:** SVM, Logistic Regression
- **Training Split:** 70% train, 15% validation, 15% test
- **Hyperparameter Tuning:** GridSearchCV / RandomizedSearchCV
- **Cross-Validation:** k-fold (k=5)

### Evaluation Metrics

- Accuracy
- Precision, Recall, F1-Score
- Specificity
- ROC-AUC, PR-AUC
- Confusion Matrix

---

## 📊 Dataset Statistics Summary

### Overall Statistics

- **Total Flows:** {total_rows:,}
- **Benign Flows:** {all_labels.get('Benign', 0):,} ({(all_labels.get('Benign', 0) / total_label_count * 100):.2f}%)
- **Malicious Flows:** {total_label_count - all_labels.get('Benign', 0):,} ({(100 - (all_labels.get('Benign', 0) / total_label_count * 100)):.2f}%)
- **Class Imbalance:** {(total_label_count - all_labels.get('Benign', 0)) / all_labels.get('Benign', 0) * 100:.2f}% malicious vs benign

### Temporal Distribution

The dataset spans **10 days** of network traffic:
- **Weekdays:** Monday through Friday
- **Attack Days:** Various attack types introduced on different days
- **Benign Baseline:** Continuous benign traffic throughout

---

## ⚠️ Data Quality Notes

1. **Label Inconsistencies**
   - Some files contain invalid labels (numeric values, typos)
   - Examples: `0`, `8`, `1874`, `Benig`, `FT`
   - These should be filtered during preprocessing

2. **File Size Variations**
   - Files range from 80 MB to 3.78 GB
   - `Thuesday-20-02-2018` is the largest file (3.78 GB on S3)
   - Some files may be partially downloaded

3. **Column Variations**
   - Most files: 80 columns
   - `Thuesday-20-02-2018`: 84 columns (includes Flow ID)
   - Column names may have trailing spaces

4. **Missing Values**
   - Some features may contain NaN values
   - Requires imputation or removal during preprocessing

---

## 🚀 Usage Recommendations

### For Training

1. **Minimum Dataset Size:** At least 1,000 labeled samples recommended
2. **Class Balance:** Consider oversampling/undersampling for imbalanced classes
3. **Feature Scaling:** Use StandardScaler or RobustScaler for normalization
4. **Cross-Validation:** Use stratified k-fold to maintain class distribution

### For Production

1. **Real-time Processing:** Extract 6 core features from live network traffic
2. **Model Updates:** Retrain periodically with new labeled data
3. **Ensemble Methods:** Combine with signature-based and anomaly detection
4. **Monitoring:** Track model performance metrics over time

### Memory Management

For large files, use chunked processing:

```python
chunk_size = 10000
for chunk in pd.read_csv(file, chunksize=chunk_size):
    # Process chunk
    process_features(chunk)
```

---

## 📚 References

- **Dataset Source:** [CICIDS2018 on AWS S3](https://www.unb.ca/cic/datasets/ids-2018.html)
- **CICFlowMeter:** [Flow-based Network Traffic Analysis Tool](https://github.com/ahlashkari/CICFlowMeter)
- **Canadian Institute for Cybersecurity:** [University of New Brunswick](https://www.unb.ca/cic/)

---

## 📝 Notes

- This dataset is intended for research and educational purposes
- Ensure compliance with data usage policies
- Some files may require significant disk space (up to 3.78 GB)
- Use `--allow-partial-download` flag if disk space is limited
- Always validate downloaded files before use

---

*Report generated by CICIDS2018 Comprehensive Analysis Script*  
*Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    output_path.write_text(md_content)
    print(f"\n✓ Comprehensive report generated: {output_path}")


def main():
    data_dir = Path(__file__).parent.parent / 'data' / 'cicids2018'
    output_file = Path(__file__).parent.parent / 'data' / 'CICIDS2018_Comprehensive_Report.md'
    
    print("="*60)
    print("CICIDS2018 Comprehensive Dataset Analysis")
    print("="*60)
    print(f"\nData directory: {data_dir}")
    print(f"Output file: {output_file}\n")
    
    # Get S3 file info
    print("Fetching S3 file information...")
    s3_info = {}
    if BOTO3_AVAILABLE:
        try:
            s3_client = boto3.client(
                's3',
                region_name='ca-central-1',
                config=Config(signature_version=UNSIGNED)
            )
            response = s3_client.list_objects_v2(
                Bucket='cse-cic-ids2018',
                Prefix='Processed Traffic Data for ML Algorithms/'
            )
            
            for obj in response.get('Contents', []):
                if obj['Key'].endswith('.csv') and 'TrafficForML_CICFlowMeter' in obj['Key']:
                    filename = obj['Key'].split('/')[-1]
                    s3_info[filename] = {
                        'size_gb': obj['Size'] / (1024 ** 3)
                    }
        except Exception as e:
            print(f"Warning: Could not fetch S3 info: {e}")
    
    print(f"Found {len(s3_info)} files in S3\n")
    
    # Get all expected files
    expected_files = [
        'Friday-02-03-2018_TrafficForML_CICFlowMeter.csv',
        'Friday-16-02-2018_TrafficForML_CICFlowMeter.csv',
        'Friday-23-02-2018_TrafficForML_CICFlowMeter.csv',
        'Thuesday-20-02-2018_TrafficForML_CICFlowMeter.csv',
        'Thursday-01-03-2018_TrafficForML_CICFlowMeter.csv',
        'Thursday-15-02-2018_TrafficForML_CICFlowMeter.csv',
        'Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv',
        'Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv',
        'Wednesday-21-02-2018_TrafficForML_CICFlowMeter.csv',
        'Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv',
    ]
    
    # Analyze each file
    analyses = []
    for filename in expected_files:
        filepath = data_dir / filename
        analysis = analyze_comprehensive(filepath, s3_info)
        analyses.append(analysis)
    
    # Generate comprehensive markdown report
    print("\n" + "="*60)
    print("Generating comprehensive markdown report...")
    print("="*60)
    generate_comprehensive_markdown(analyses, output_file)
    
    print("\n" + "="*60)
    print("Analysis Complete!")
    print("="*60)


if __name__ == '__main__':
    main()
