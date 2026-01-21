#!/usr/bin/env python3
"""
Analyze CICIDS2018 dataset files and generate comprehensive markdown report
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


def get_s3_file_info():
    """Get file information from S3"""
    if not BOTO3_AVAILABLE:
        return {}
    
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
        
        file_info = {}
        for obj in response.get('Contents', []):
            if obj['Key'].endswith('.csv') and 'TrafficForML_CICFlowMeter' in obj['Key']:
                filename = obj['Key'].split('/')[-1]
                file_info[filename] = {
                    'size_bytes': obj['Size'],
                    'size_gb': obj['Size'] / (1024 ** 3),
                    'last_modified': obj['LastModified'].isoformat() if 'LastModified' in obj else None
                }
        return file_info
    except Exception as e:
        print(f"Warning: Could not fetch S3 info: {e}")
        return {}


def analyze_file(filepath: Path, s3_info: dict = None):
    """Analyze a single CSV file"""
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
        'dtypes': {},
        'missing_values': {},
        'label_distribution': {},
        'unique_labels': [],
        'sample_data': None,
        'statistics': {}
    }
    
    if not filepath.exists():
        return analysis
    
    try:
        # Read first chunk to get structure
        chunk_size = 10000
        first_chunk = pd.read_csv(filepath, nrows=chunk_size, low_memory=False)
        
        analysis['columns'] = len(first_chunk.columns)
        analysis['column_names'] = list(first_chunk.columns)
        analysis['dtypes'] = {col: str(dtype) for col, dtype in first_chunk.dtypes.items()}
        
        # Count total rows (efficiently)
        total_rows = sum(1 for _ in open(filepath)) - 1  # Subtract header
        analysis['rows'] = total_rows
        
        # Analyze missing values from first chunk
        analysis['missing_values'] = {col: int(first_chunk[col].isna().sum()) 
                                     for col in first_chunk.columns}
        
        # Find label column (common names)
        label_col = None
        for col in ['Label', 'label', 'Label ', 'label ']:
            if col in first_chunk.columns:
                label_col = col
                break
        
        if label_col:
            # Read full file for label distribution (chunked)
            label_counts = Counter()
            for chunk in pd.read_csv(filepath, chunksize=50000, usecols=[label_col], low_memory=False):
                label_counts.update(chunk[label_col].dropna().astype(str))
            
            analysis['label_distribution'] = dict(label_counts)
            analysis['unique_labels'] = list(label_counts.keys())
        
        # Basic statistics for numeric columns
        numeric_cols = first_chunk.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            stats_chunk = pd.read_csv(filepath, nrows=min(100000, total_rows), 
                                     usecols=list(numeric_cols[:10]), low_memory=False)
            analysis['statistics'] = {
                col: {
                    'mean': float(stats_chunk[col].mean()) if pd.api.types.is_numeric_dtype(stats_chunk[col]) else None,
                    'std': float(stats_chunk[col].std()) if pd.api.types.is_numeric_dtype(stats_chunk[col]) else None,
                    'min': float(stats_chunk[col].min()) if pd.api.types.is_numeric_dtype(stats_chunk[col]) else None,
                    'max': float(stats_chunk[col].max()) if pd.api.types.is_numeric_dtype(stats_chunk[col]) else None,
                }
                for col in numeric_cols[:10]
            }
        
        # Sample data (first 3 rows)
        analysis['sample_data'] = first_chunk.head(3).to_dict('records')
        
    except Exception as e:
        analysis['error'] = str(e)
        print(f"  Error analyzing {filename}: {e}")
    
    return analysis


def generate_markdown_report(analyses: list, output_path: Path):
    """Generate comprehensive markdown report"""
    
    total_files = len(analyses)
    downloaded_files = sum(1 for a in analyses if a['local_exists'])
    total_rows = sum(a['rows'] for a in analyses)
    total_size_gb = sum(a['local_size_gb'] for a in analyses if a['local_exists'])
    
    # Aggregate label distribution
    all_labels = Counter()
    for analysis in analyses:
        all_labels.update(analysis.get('label_distribution', {}))
    
    md_content = f"""# CICIDS2018 Dataset Analysis Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

- **Total Files:** {total_files}
- **Downloaded Files:** {downloaded_files}
- **Total Rows:** {total_rows:,}
- **Total Size:** {total_size_gb:.2f} GB
- **Unique Attack Types:** {len(all_labels)}

## Dataset Overview

The CICIDS2018 dataset contains network traffic flow data collected over multiple days in February and March 2018. Each file represents traffic captured on a specific day, containing both benign and various attack traffic patterns.

### File Status

| Filename | Status | Local Size | S3 Size | Rows | Columns |
|----------|--------|------------|---------|------|----------|
"""
    
    for analysis in sorted(analyses, key=lambda x: x['filename']):
        status = "✓ Downloaded" if analysis['local_exists'] else "✗ Not Downloaded"
        local_size = f"{analysis['local_size_gb']:.2f} GB" if analysis['local_exists'] else "N/A"
        s3_size = f"{analysis['s3_size_gb']:.2f} GB" if analysis['s3_size_gb'] > 0 else "N/A"
        rows = f"{analysis['rows']:,}" if analysis['rows'] > 0 else "N/A"
        cols = analysis['columns'] if analysis['columns'] > 0 else "N/A"
        
        md_content += f"| `{analysis['filename']}` | {status} | {local_size} | {s3_size} | {rows} | {cols} |\n"
    
    md_content += f"""
## Overall Label Distribution

| Label | Count | Percentage |
|-------|-------|------------|
"""
    
    total_label_count = sum(all_labels.values())
    for label, count in sorted(all_labels.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_label_count * 100) if total_label_count > 0 else 0
        md_content += f"| `{label}` | {count:,} | {percentage:.2f}% |\n"
    
    md_content += f"""
## Detailed File Analysis

"""
    
    for analysis in sorted(analyses, key=lambda x: x['filename']):
        md_content += f"""### {analysis['filename']}

**Status:** {'✓ Downloaded' if analysis['local_exists'] else '✗ Not Downloaded'}

"""
        
        if analysis['local_exists']:
            md_content += f"""
- **Local Size:** {analysis['local_size_gb']:.2f} GB ({analysis['local_size_bytes']:,} bytes)
- **S3 Size:** {analysis['s3_size_gb']:.2f} GB (if available)
- **Total Rows:** {analysis['rows']:,}
- **Total Columns:** {analysis['columns']}

#### Column Information

The dataset contains {analysis['columns']} columns. Key columns include:
"""
            
            # List important columns
            important_cols = ['Flow ID', 'Source IP', 'Destination IP', 'Source Port', 
                            'Destination Port', 'Protocol', 'Timestamp', 'Label']
            found_cols = [col for col in important_cols if col in analysis['column_names']]
            other_cols = [col for col in analysis['column_names'] if col not in important_cols]
            
            if found_cols:
                md_content += "\n**Important Columns:**\n"
                for col in found_cols:
                    dtype = analysis['dtypes'].get(col, 'unknown')
                    md_content += f"- `{col}` ({dtype})\n"
            
            if len(other_cols) > 0:
                md_content += f"\n**Other Columns:** {len(other_cols)} additional feature columns\n"
            
            # Label distribution for this file
            if analysis.get('label_distribution'):
                md_content += "\n#### Label Distribution\n\n"
                md_content += "| Label | Count | Percentage |\n"
                md_content += "|-------|-------|------------|\n"
                
                file_total = sum(analysis['label_distribution'].values())
                for label, count in sorted(analysis['label_distribution'].items(), 
                                         key=lambda x: x[1], reverse=True):
                    pct = (count / file_total * 100) if file_total > 0 else 0
                    md_content += f"| `{label}` | {count:,} | {pct:.2f}% |\n"
            
            # Statistics
            if analysis.get('statistics'):
                md_content += "\n#### Statistical Summary (Sample)\n\n"
                md_content += "| Column | Mean | Std Dev | Min | Max |\n"
                md_content += "|--------|------|---------|-----|-----|\n"
                
                for col, stats in list(analysis['statistics'].items())[:5]:
                    mean = f"{stats['mean']:.2f}" if stats['mean'] is not None else "N/A"
                    std = f"{stats['std']:.2f}" if stats['std'] is not None else "N/A"
                    min_val = f"{stats['min']:.2f}" if stats['min'] is not None else "N/A"
                    max_val = f"{stats['max']:.2f}" if stats['max'] is not None else "N/A"
                    md_content += f"| `{col}` | {mean} | {std} | {min_val} | {max_val} |\n"
        
        else:
            md_content += f"""
- **Status:** Not downloaded locally
- **S3 Size:** {analysis['s3_size_gb']:.2f} GB
- **Reason:** File not available in local directory

"""
        
        if analysis.get('error'):
            md_content += f"\n⚠ **Error:** {analysis['error']}\n"
        
        md_content += "\n---\n\n"
    
    md_content += f"""
## Dataset Characteristics

### Temporal Coverage

The dataset spans multiple days in February and March 2018:
- **February 2018:** 14th, 15th, 16th, 20th, 21st, 22nd, 23rd, 28th
- **March 2018:** 1st, 2nd, 3rd

### Data Format

- **Format:** CSV (Comma-Separated Values)
- **Encoding:** UTF-8
- **Headers:** First row contains column names
- **Flow-based:** Each row represents a network flow

### Feature Set

The dataset contains 80+ features extracted using CICFlowMeter, including:
- Flow identifiers (Flow ID, Source/Destination IP/Port)
- Protocol information
- Flow duration and timing statistics
- Packet counts and sizes
- TCP flags and window sizes
- Statistical features (mean, std, min, max)
- Label (attack type or benign)

### Attack Types

Based on label analysis, the dataset includes various attack types:
"""
    
    attack_types = sorted(set(all_labels.keys()))
    for attack_type in attack_types[:20]:  # Limit to first 20
        md_content += f"- `{attack_type}`\n"
    
    if len(attack_types) > 20:
        md_content += f"- ... and {len(attack_types) - 20} more\n"
    
    md_content += f"""
## Usage Recommendations

1. **Preprocessing:** Use the provided `preprocess_cicids2018.py` script to extract the 6 core features required by the IDS system.

2. **Training:** The dataset is suitable for:
   - Supervised binary classification (Benign vs Malicious)
   - Multi-class attack type classification
   - Anomaly detection model training

3. **Memory Management:** For large files, use chunked processing:
   ```python
   for chunk in pd.read_csv(file, chunksize=10000):
       # Process chunk
   ```

4. **Data Splitting:** Recommended split:
   - Training: 70%
   - Validation: 15%
   - Testing: 15%

## Notes

- Some files may be very large (up to 3.78 GB)
- Ensure sufficient disk space before downloading
- Use `--allow-partial-download` flag if disk space is limited
- The dataset requires preprocessing before use with the IDS system

---
*Report generated by CICIDS2018 Analysis Script*
"""
    
    output_path.write_text(md_content)
    print(f"\n✓ Report generated: {output_path}")


def main():
    data_dir = Path(__file__).parent.parent / 'data' / 'cicids2018'
    output_file = Path(__file__).parent.parent / 'data' / 'CICIDS2018_Analysis.md'
    
    print("="*60)
    print("CICIDS2018 Dataset Analysis")
    print("="*60)
    print(f"\nData directory: {data_dir}")
    print(f"Output file: {output_file}\n")
    
    # Get S3 file info
    print("Fetching S3 file information...")
    s3_info = get_s3_file_info()
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
        analysis = analyze_file(filepath, s3_info)
        analyses.append(analysis)
    
    # Generate markdown report
    print("\n" + "="*60)
    print("Generating markdown report...")
    print("="*60)
    generate_markdown_report(analyses, output_file)
    
    print("\n" + "="*60)
    print("Analysis Complete!")
    print("="*60)


if __name__ == '__main__':
    main()
