#!/usr/bin/env python3
"""Monitor MongoDB import progress with ETA"""
import sys
import time
from datetime import datetime, timedelta
from config import Config
from services.data_collector import DataCollector

TARGET_SAMPLES = 8_034_453

def format_time(seconds):
    """Format seconds into human-readable time"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

try:
    config = Config()
    data_collector = DataCollector(config)
    
    # Get initial stats
    stats = data_collector.get_statistics()
    initial_count = stats.get('total_samples', 0)
    initial_time = time.time()
    
    print("="*70)
    print("MongoDB Import Monitor")
    print("="*70)
    print(f"Target: {TARGET_SAMPLES:,} samples")
    print(f"Current: {initial_count:,} samples")
    print(f"Progress: {(initial_count / TARGET_SAMPLES * 100):.2f}%")
    print("="*70)
    
    if initial_count == 0:
        print("Waiting for import to start...")
        sys.exit(0)
    
    # Monitor progress
    print("\nMonitoring import progress (Ctrl+C to stop)...")
    print("-"*70)
    
    last_count = initial_count
    last_time = initial_time
    
    try:
        while True:
            time.sleep(30)  # Check every 30 seconds
            
            stats = data_collector.get_statistics()
            current_count = stats.get('total_samples', 0)
            current_time = time.time()
            
            if current_count > last_count:
                # Calculate rate
                elapsed = current_time - last_time
                samples_added = current_count - last_count
                rate = samples_added / elapsed if elapsed > 0 else 0
                
                # Calculate ETA
                remaining = TARGET_SAMPLES - current_count
                if rate > 0:
                    eta_seconds = remaining / rate
                    eta = format_time(eta_seconds)
                else:
                    eta = "calculating..."
                
                progress_pct = (current_count / TARGET_SAMPLES) * 100
                
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] Samples: {current_count:,} ({progress_pct:.2f}%) | "
                      f"Rate: {rate:.0f} samples/sec | ETA: {eta}")
                print(f"  Benign: {stats.get('benign_count', 0):,} | "
                      f"Malicious: {stats.get('malicious_count', 0):,}")
                
                if current_count >= TARGET_SAMPLES:
                    print("\n" + "="*70)
                    print("Import completed!")
                    print("="*70)
                    break
                
                last_count = current_count
                last_time = current_time
            else:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] No new samples imported (waiting...)")
                
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
        stats = data_collector.get_statistics()
        final_count = stats.get('total_samples', 0)
        print(f"\nFinal count: {final_count:,} samples")
        print(f"Progress: {(final_count / TARGET_SAMPLES * 100):.2f}%")
    
    sys.exit(0)
except Exception as e:
    print(f"Error monitoring import: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
