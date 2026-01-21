"""
Memory management utilities for large dataset training
"""

import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def check_available_memory() -> Optional[float]:
    """
    Check available system RAM in GB
    
    Returns:
        Available memory in GB, or None if psutil not available
    """
    try:
        import psutil
        available_bytes = psutil.virtual_memory().available
        available_gb = available_bytes / (1024**3)
        return available_gb
    except ImportError:
        logger.warning("psutil not available. Install with: pip install psutil")
        return None
    except Exception as e:
        logger.warning(f"Error checking memory: {e}")
        return None


def estimate_memory_usage(samples: int, features: int = 81, dtype_bytes: int = 8) -> float:
    """
    Estimate memory usage for dataset
    
    Args:
        samples: Number of samples
        features: Number of features per sample
        dtype_bytes: Bytes per value (8 for float64, 4 for float32)
    
    Returns:
        Estimated memory usage in GB
    """
    # Memory = samples × features × bytes_per_value
    # Add 20% overhead for pandas/processing
    base_memory = samples * features * dtype_bytes
    estimated_memory = base_memory * 1.2
    return estimated_memory / (1024**3)


def recommend_batch_size(available_memory_gb: Optional[float], 
                        total_samples: int, 
                        features: int = 81) -> int:
    """
    Recommend batch size based on available memory
    
    Args:
        available_memory_gb: Available RAM in GB
        total_samples: Total number of samples
        features: Number of features per sample
    
    Returns:
        Recommended batch size
    """
    if available_memory_gb is None:
        # Default to 100K if we can't check memory
        return 100000
    
    # Use 50% of available memory for safety
    usable_memory_gb = available_memory_gb * 0.5
    
    # Estimate memory per sample (with overhead)
    memory_per_sample_gb = (features * 8 * 1.2) / (1024**3)
    
    # Calculate batch size
    batch_size = int(usable_memory_gb / memory_per_sample_gb)
    
    # Clamp to reasonable values
    batch_size = max(10000, min(batch_size, 500000))
    
    return batch_size


def check_memory_sufficient(estimated_memory_gb: float, 
                           available_memory_gb: Optional[float],
                           threshold: float = 0.8) -> Tuple[bool, str]:
    """
    Check if estimated memory usage is within safe limits
    
    Args:
        estimated_memory_gb: Estimated memory needed
        available_memory_gb: Available RAM
        threshold: Warning threshold (0.8 = 80%)
    
    Returns:
        Tuple of (is_sufficient, warning_message)
    """
    if available_memory_gb is None:
        return True, "Cannot verify memory (psutil not available)"
    
    usage_ratio = estimated_memory_gb / available_memory_gb
    
    if usage_ratio > threshold:
        warning = (f"Estimated memory usage ({estimated_memory_gb:.2f} GB) exceeds "
                  f"{threshold*100:.0f}% of available RAM ({available_memory_gb:.2f} GB). "
                  f"Consider enabling batch loading.")
        return False, warning
    
    return True, "Memory check passed"
