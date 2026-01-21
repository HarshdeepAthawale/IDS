#!/usr/bin/env python3
"""
Validate preprocessed CICIDS2018 JSON file
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any
import logging
import ijson

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_preprocessed_json(json_file: Path) -> Dict[str, Any]:
    """Validate preprocessed JSON file and return statistics"""
    logger.info(f"Validating preprocessed JSON file: {json_file}")
    
    validation_results = {
        'valid': False,
        'total_samples': 0,
        'benign_count': 0,
        'malicious_count': 0,
        'feature_count': 0,
        'files_seen': set(),
        'errors': [],
        'warnings': []
    }
    
    if not json_file.exists():
        validation_results['errors'].append(f"File does not exist: {json_file}")
        return validation_results
    
    try:
        # Check file size
        file_size_gb = json_file.stat().st_size / (1024**3)
        logger.info(f"File size: {file_size_gb:.2f} GB")
        
        # Use streaming JSON parser for large files
        logger.info("Streaming JSON file (this may take a while for large files)...")
        feature_counts = {}
        idx = 0
        
        try:
            # Try using ijson for streaming
            with open(json_file, 'rb') as f:
                parser = ijson.items(f, 'item')
                for sample in parser:
                    idx += 1
        except (ImportError, NameError):
            # Fallback: manual streaming parser for JSON arrays
            logger.info("Using manual streaming parser...")
            with open(json_file, 'r', encoding='utf-8') as f:
                # Skip opening bracket
                char = f.read(1)
                if char != '[':
                    validation_results['errors'].append("JSON file does not start with '['")
                    return validation_results
                
                # Read samples one by one
                buffer = ""
                depth = 0
                in_string = False
                escape_next = False
                
                while True:
                    char = f.read(1)
                    if not char:
                        break
                    
                    if escape_next:
                        buffer += char
                        escape_next = False
                        continue
                    
                    if char == '\\':
                        buffer += char
                        escape_next = True
                        continue
                    
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        buffer += char
                        continue
                    
                    if not in_string:
                        if char == '{':
                            depth += 1
                            buffer += char
                        elif char == '}':
                            depth -= 1
                            buffer += char
                            if depth == 0:
                                # Complete sample found
                                try:
                                    sample = json.loads(buffer.strip().rstrip(','))
                                    # Process sample (same as before)
                                    idx += 1
                                    buffer = ""
                                    # Skip comma and whitespace
                                    while True:
                                        peek = f.read(1)
                                        if not peek or peek == ']':
                                            break
                                        if peek not in [' ', '\n', '\t', ',']:
                                            f.seek(f.tell() - 1)
                                            break
                                    if peek == ']':
                                        break
                                    continue
                                except json.JSONDecodeError as e:
                                    validation_results['errors'].append(f"Error parsing sample {idx}: {e}")
                                    buffer = ""
                                    continue
                        else:
                            buffer += char
                    else:
                        buffer += char
        
        validation_results['total_samples'] = idx
        
        # Reset for actual validation
        logger.info(f"Found {validation_results['total_samples']:,} samples. Validating...")
        
        # Now validate samples using streaming
        idx = 0
        try:
            with open(json_file, 'rb') as f:
                parser = ijson.items(f, 'item')
                for sample in parser:
                    try:
                        # Check required fields
                        if 'features' not in sample:
                            validation_results['errors'].append(f"Sample {idx} missing 'features'")
                            idx += 1
                            continue
                        if 'label' not in sample:
                            validation_results['errors'].append(f"Sample {idx} missing 'label'")
                            idx += 1
                            continue
                        
                        # Validate label
                        label = sample.get('label')
                        if label not in ['benign', 'malicious']:
                            validation_results['warnings'].append(
                                f"Sample {idx} has invalid label: {label}"
                            )
                        
                        # Count labels
                        if label == 'benign':
                            validation_results['benign_count'] += 1
                        elif label == 'malicious':
                            validation_results['malicious_count'] += 1
                        
                        # Check feature count
                        features = sample.get('features', {})
                        if isinstance(features, dict):
                            feature_count = len(features)
                            feature_counts[feature_count] = feature_counts.get(feature_count, 0) + 1
                            
                            if validation_results['feature_count'] == 0:
                                validation_results['feature_count'] = feature_count
                            elif feature_count < 50:  # Warn if less than 50 features
                                validation_results['warnings'].append(
                                    f"Sample {idx} has only {feature_count} features (expected 80+)"
                                )
                        
                        # Track source files
                        source_file = sample.get('metadata', {}).get('source_file', 'unknown')
                        validation_results['files_seen'].add(source_file)
                        
                        # Progress update
                        if (idx + 1) % 100000 == 0:
                            logger.info(f"  Validated {idx + 1:,} samples...")
                        
                        idx += 1
                    except Exception as e:
                        validation_results['errors'].append(f"Error validating sample {idx}: {e}")
                        idx += 1
        except (ImportError, NameError):
            # Fallback: use simple validation without full parsing
            logger.warning("ijson not available, using basic validation...")
            # Just check JSON structure is valid
            with open(json_file, 'r') as f:
                # Count samples by counting opening braces
                content = f.read(1024*1024)  # Read first 1MB
                sample_count = content.count('"label"')
                validation_results['total_samples'] = sample_count
                logger.info(f"Estimated samples: {validation_results['total_samples']:,}")
                validation_results['warnings'].append("Full validation skipped (ijson not available). Install with: pip install ijson")
        
        validation_results['valid'] = len(validation_results['errors']) == 0
        
        # Print summary
        logger.info("="*60)
        logger.info("Validation Summary")
        logger.info("="*60)
        logger.info(f"Valid: {validation_results['valid']}")
        logger.info(f"Total samples: {validation_results['total_samples']:,}")
        logger.info(f"Benign: {validation_results['benign_count']:,} "
                   f"({validation_results['benign_count']/validation_results['total_samples']*100:.1f}%)")
        logger.info(f"Malicious: {validation_results['malicious_count']:,} "
                   f"({validation_results['malicious_count']/validation_results['total_samples']*100:.1f}%)")
        
        if feature_counts:
            most_common_features = max(feature_counts.items(), key=lambda x: x[1])
            logger.info(f"Most common feature count: {most_common_features[0]} "
                       f"({most_common_features[1]:,} samples)")
            if len(feature_counts) > 1:
                logger.warning(f"Feature count varies: {list(feature_counts.keys())}")
        
        logger.info(f"Source files: {len(validation_results['files_seen'])}")
        for file_name in sorted(validation_results['files_seen']):
            logger.info(f"  - {file_name}")
        
        if validation_results['errors']:
            logger.warning(f"Validation errors: {len(validation_results['errors'])}")
            for error in validation_results['errors'][:20]:  # Show first 20 errors
                logger.warning(f"  - {error}")
            if len(validation_results['errors']) > 20:
                logger.warning(f"  ... and {len(validation_results['errors']) - 20} more errors")
        
        if validation_results['warnings']:
            logger.warning(f"Validation warnings: {len(validation_results['warnings'])}")
            for warning in validation_results['warnings'][:10]:  # Show first 10 warnings
                logger.warning(f"  - {warning}")
            if len(validation_results['warnings']) > 10:
                logger.warning(f"  ... and {len(validation_results['warnings']) - 10} more warnings")
        
        logger.info("="*60)
        
        return validation_results
        
    except json.JSONDecodeError as e:
        validation_results['errors'].append(f"Invalid JSON: {e}")
        logger.error(f"JSON file is invalid: {e}")
        return validation_results
    except Exception as e:
        validation_results['errors'].append(f"Error reading file: {e}")
        logger.error(f"Error validating JSON file: {e}")
        import traceback
        traceback.print_exc()
        return validation_results


def main():
    parser = argparse.ArgumentParser(description='Validate preprocessed CICIDS2018 JSON file')
    parser.add_argument('--input-file', type=str, required=True,
                       help='Preprocessed JSON file to validate')
    parser.add_argument('--output-report', type=str,
                       help='Output file for validation report (JSON format)')
    
    args = parser.parse_args()
    
    json_file = Path(args.input_file)
    if not json_file.exists():
        logger.error(f"JSON file does not exist: {json_file}")
        sys.exit(1)
    
    # Run validation
    results = validate_preprocessed_json(json_file)
    
    # Save report if requested
    if args.output_report:
        report_file = Path(args.output_report)
        report_data = {
            'valid': results['valid'],
            'total_samples': results['total_samples'],
            'benign_count': results['benign_count'],
            'malicious_count': results['malicious_count'],
            'feature_count': results['feature_count'],
            'files_seen': list(results['files_seen']),
            'error_count': len(results['errors']),
            'warning_count': len(results['warnings']),
            'errors': results['errors'][:100],  # Limit to first 100 errors
            'warnings': results['warnings'][:100]  # Limit to first 100 warnings
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"Validation report saved to: {report_file}")
    
    # Exit with error code if validation failed
    if not results['valid']:
        sys.exit(1)
    else:
        logger.info("✓ Validation passed!")
        sys.exit(0)


if __name__ == '__main__':
    main()
