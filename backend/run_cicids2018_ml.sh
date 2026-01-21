#!/bin/bash
# Complete CICIDS2018 ML Pipeline Script
# Downloads dataset, preprocesses, imports to MongoDB, and trains model

set -e  # Exit on error

echo "=========================================="
echo "CICIDS2018 ML Pipeline - Complete Automation"
echo "=========================================="
echo ""

# Configuration
DOWNLOAD_DIR="./data/cicids2018"
PREPROCESS_OUTPUT="./data/cicids2018_preprocessed.json"
MIN_SPACE=5.0  # Adjust based on your available space

# Change to backend directory
cd "$(dirname "$0")"

echo "Step 1: Downloading CICIDS2018 dataset..."
python scripts/cicids2018_pipeline.py \
    --download-dir "$DOWNLOAD_DIR" \
    --preprocess-output "$PREPROCESS_OUTPUT" \
    --import-batch-size 1000 \
    --chunk-size 10000 \
    --min-space "$MIN_SPACE" \
    --allow-partial-download \
    --auto-train

echo ""
echo "=========================================="
echo "✓ ML Pipeline completed successfully!"
echo "=========================================="
