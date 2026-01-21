#!/bin/bash
# Quick script to verify import and start training

cd "$(dirname "$0")/.."

echo "=========================================="
echo "CICIDS2018 Training Pipeline"
echo "=========================================="
echo ""

# Activate virtual environment
source venv/bin/activate

# Step 1: Verify MongoDB import
echo "Step 1: Verifying MongoDB import..."
python scripts/verify_and_train.py

if [ $? -eq 0 ]; then
    echo ""
    echo "Step 2: Starting model training..."
    echo "=========================================="
    python scripts/train_from_cicids2018.py
else
    echo ""
    echo "⚠ Import verification failed!"
    echo "Please ensure:"
    echo "  1. MongoDB is running: sudo systemctl start mongod"
    echo "  2. Data was imported successfully"
    echo ""
    exit 1
fi
