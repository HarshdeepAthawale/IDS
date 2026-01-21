"""
Data collection service for supervised ML training data
Handles collection, storage, and labeling of training samples
"""

import logging
import warnings
from datetime import datetime
from typing import Dict, List, Any, Optional, Iterator
from models.db_models import get_db

# Suppress pymongo SSL warnings
warnings.filterwarnings('ignore', category=UserWarning, module='pymongo')
logging.getLogger('pymongo').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


class DataCollector:
    """
    Service for collecting and managing training data
    """
    
    def __init__(self, config):
        """
        Initialize data collector
        
        Args:
            config: Configuration object
        """
        self.config = config
        try:
            self.db = get_db(config)
            self.training_collection = self.db['training_data']
            
            # Create indexes
            self._create_indexes()
            
            logger.info("DataCollector initialized")
        except Exception as e:
            # MongoDB connection may fail due to SSL issues, but training can use JSON file
            logger.warning(f"MongoDB connection failed (training can use JSON file): {e}")
            self.db = None
            self.training_collection = None
    
    def _create_indexes(self):
        """Create database indexes for efficient queries"""
        try:
            if self.training_collection is not None:
                self.training_collection.create_index([("label", 1)])
                self.training_collection.create_index([("timestamp", -1)])
                self.training_collection.create_index([("source_ip", 1)])
                self.training_collection.create_index([("label", 1), ("timestamp", -1)])
                logger.info("Created indexes for training_data collection")
        except Exception as e:
            # Suppress SSL errors - they don't affect functionality
            if 'SSL' not in str(e) and 'TLS' not in str(e):
                logger.error(f"Error creating indexes: {e}")
    
    def collect_sample(self, features: Dict[str, float], packet_data: Dict[str, Any],
                      label: Optional[str] = None, labeled_by: str = "auto",
                      confidence: float = 1.0) -> Dict[str, Any]:
        """
        Collect a training sample with features
        
        Args:
            features: Extracted features dictionary
            packet_data: Original packet data
            label: Label ("benign" or "malicious"), None if unlabeled
            labeled_by: Source of label ("user", "auto", "import")
            confidence: Confidence in label (0.0-1.0)
            
        Returns:
            Created training sample document
        """
        try:
            sample_doc = {
                'features': features,
                'label': label,
                'labeled_by': labeled_by,
                'confidence': confidence,
                'timestamp': datetime.utcnow(),
                'source_ip': packet_data.get('src_ip', 'unknown'),
                'dest_ip': packet_data.get('dst_ip', 'unknown'),
                'protocol': packet_data.get('protocol', 'unknown'),
                'dst_port': packet_data.get('dst_port'),
                'metadata': {
                    'raw_size': packet_data.get('raw_size'),
                    'payload_size': packet_data.get('payload_size'),
                    'flags': packet_data.get('flags'),
                    'user_agent': packet_data.get('user_agent'),
                    'uri': packet_data.get('uri')
                }
            }
            
            result = self.training_collection.insert_one(sample_doc)
            sample_doc['_id'] = result.inserted_id
            
            logger.debug(f"Collected training sample: {result.inserted_id}")
            return sample_doc
            
        except Exception as e:
            logger.error(f"Error collecting training sample: {e}")
            return {}
    
    def label_sample(self, sample_id: str, label: str, labeled_by: str = "user",
                    confidence: float = 1.0) -> bool:
        """
        Label an existing training sample
        
        Args:
            sample_id: Sample ID (string or ObjectId)
            label: Label ("benign" or "malicious")
            labeled_by: Source of label
            confidence: Confidence in label
            
        Returns:
            True if successful
        """
        try:
            from models.db_models import to_object_id
            obj_id = to_object_id(sample_id)
            if not obj_id:
                logger.warning(f"Invalid sample ID format: {sample_id}")
                return False
            
            if label not in ['benign', 'malicious']:
                logger.warning(f"Invalid label: {label}")
                return False
            
            result = self.training_collection.update_one(
                {'_id': obj_id},
                {
                    '$set': {
                        'label': label,
                        'labeled_by': labeled_by,
                        'confidence': confidence,
                        'labeled_at': datetime.utcnow()
                    }
                }
            )
            
            if result.matched_count == 0:
                logger.warning(f"Sample {sample_id} not found")
                return False
            
            logger.info(f"Labeled sample {sample_id} as {label}")
            return True
            
        except Exception as e:
            logger.error(f"Error labeling sample: {e}")
            return False
    
    def get_labeled_samples(self, label: Optional[str] = None, limit: Optional[int] = 1000,
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get labeled training samples
        
        Args:
            label: Filter by label ("benign" or "malicious"), None for all
            limit: Maximum number of samples to return (None = all samples)
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            List of training sample documents
        """
        try:
            query = {'label': {'$ne': None}}  # Only labeled samples
            
            if label:
                query['label'] = label
            
            if start_date or end_date:
                query['timestamp'] = {}
                if start_date:
                    query['timestamp']['$gte'] = start_date
                if end_date:
                    query['timestamp']['$lte'] = end_date
            
            cursor = self.training_collection.find(query).sort('timestamp', -1)
            
            if limit is not None:
                cursor = cursor.limit(limit)
            
            samples = list(cursor)
            
            return samples
            
        except Exception as e:
            logger.error(f"Error getting labeled samples: {e}")
            return []
    
    def get_all_labeled_samples_batch(self, label: Optional[str] = None, 
                                      batch_size: int = 100000) -> Iterator[List[Dict[str, Any]]]:
        """
        Get all labeled samples in batches for memory-efficient loading
        
        Args:
            label: Filter by label ("benign" or "malicious"), None for all
            batch_size: Number of samples per batch
            
        Yields:
            List of sample dictionaries for each batch
        """
        import time
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                query = {'label': {'$ne': None}}  # Only labeled samples
                
                if label:
                    query['label'] = label
                
                cursor = self.training_collection.find(query).sort('timestamp', -1)
                
                batch = []
                for sample in cursor:
                    batch.append(sample)
                    if len(batch) >= batch_size:
                        yield batch
                        batch = []
                
                # Yield remaining samples
                if batch:
                    yield batch
                
                # Success - break out of retry loop
                break
                    
            except Exception as e:
                error_msg = str(e)
                # Check if it's an SSL error that we can retry
                if 'SSL' in error_msg or 'TLS' in error_msg or 'handshake' in error_msg:
                    if attempt < max_retries - 1:
                        logger.warning(f"SSL error during batch loading (attempt {attempt + 1}/{max_retries}), retrying...")
                        time.sleep(2)
                        # Reconnect by getting a fresh db reference
                        from models.db_models import get_db
                        self.db = get_db(self.config)
                        self.training_collection = self.db['training_data']
                        continue
                    else:
                        logger.error(f"SSL error persisted after {max_retries} attempts: {e}")
                        yield []
                        break
                else:
                    logger.error(f"Error getting labeled samples in batches: {e}")
                    yield []
                    break
    
    def get_unlabeled_samples(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get unlabeled training samples
        
        Args:
            limit: Maximum number of samples to return
            
        Returns:
            List of unlabeled training sample documents
        """
        try:
            samples = list(self.training_collection.find({'label': None})
                          .sort('timestamp', -1)
                          .limit(limit))
            
            return samples
            
        except Exception as e:
            logger.error(f"Error getting unlabeled samples: {e}")
            return []
    
    def delete_sample(self, sample_id: str) -> bool:
        """
        Delete a training sample
        
        Args:
            sample_id: Sample ID (string or ObjectId)
            
        Returns:
            True if successful
        """
        try:
            from models.db_models import to_object_id
            obj_id = to_object_id(sample_id)
            if not obj_id:
                logger.warning(f"Invalid sample ID format: {sample_id}")
                return False
            
            result = self.training_collection.delete_one({'_id': obj_id})
            
            if result.deleted_count == 0:
                logger.warning(f"Sample {sample_id} not found")
                return False
            
            logger.info(f"Deleted sample {sample_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting sample: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about training data
        
        Returns:
            Dictionary with statistics
        """
        try:
            total_samples = self.training_collection.count_documents({})
            labeled_samples = self.training_collection.count_documents({'label': {'$ne': None}})
            unlabeled_samples = total_samples - labeled_samples
            
            # Count by label
            benign_count = self.training_collection.count_documents({'label': 'benign'})
            malicious_count = self.training_collection.count_documents({'label': 'malicious'})
            
            # Count by label source
            auto_labeled = self.training_collection.count_documents({'labeled_by': 'auto'})
            user_labeled = self.training_collection.count_documents({'labeled_by': 'user'})
            imported = self.training_collection.count_documents({'labeled_by': 'import'})
            # Count CICIDS2018 imports (and other import sources)
            cicids2018_imported = self.training_collection.count_documents({'labeled_by': 'cicids2018'})
            # Total imported samples (any import source)
            total_imported = self.training_collection.count_documents({
                'labeled_by': {'$in': ['import', 'cicids2018']}
            })
            
            return {
                'total_samples': total_samples,
                'labeled_samples': labeled_samples,
                'unlabeled_samples': unlabeled_samples,
                'benign_count': benign_count,
                'malicious_count': malicious_count,
                'auto_labeled': auto_labeled,
                'user_labeled': user_labeled,
                'imported': total_imported,  # Total imported (includes cicids2018)
                'cicids2018_imported': cicids2018_imported,  # Specifically CICIDS2018
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    def import_dataset(self, samples: List[Dict[str, Any]], labeled_by: str = "import") -> int:
        """
        Import external labeled dataset using bulk insert for performance
        
        Args:
            samples: List of sample dictionaries with features and labels
            labeled_by: Source identifier for imported data
            
        Returns:
            Number of samples imported
        """
        try:
            # Prepare documents for bulk insert
            documents = []
            skipped_count = 0
            
            for sample in samples:
                if 'features' not in sample or 'label' not in sample:
                    skipped_count += 1
                    continue
                
                if sample['label'] not in ['benign', 'malicious']:
                    skipped_count += 1
                    continue
                
                sample_doc = {
                    'features': sample['features'],
                    'label': sample['label'],
                    'labeled_by': labeled_by,
                    'confidence': sample.get('confidence', 1.0),
                    'timestamp': sample.get('timestamp', datetime.utcnow()),
                    'source_ip': sample.get('source_ip', 'unknown'),
                    'dest_ip': sample.get('dest_ip', 'unknown'),
                    'protocol': sample.get('protocol', 'unknown'),
                    'dst_port': sample.get('dst_port'),
                    'metadata': sample.get('metadata', {})
                }
                
                documents.append(sample_doc)
            
            # Bulk insert with ordered=False for parallel processing and write concern optimization
            if documents:
                try:
                    # Use write concern for better performance on powerful systems
                    result = self.training_collection.insert_many(
                        documents, 
                        ordered=False,  # Allow parallel inserts
                        bypass_document_validation=False  # Keep validation but allow parallel processing
                    )
                    imported_count = len(result.inserted_ids)
                    logger.debug(f"Bulk imported {imported_count} samples from {labeled_by}")
                    return imported_count
                except Exception as bulk_error:
                    # If bulk insert fails, fall back to individual inserts
                    # This handles duplicate key errors gracefully
                    logger.warning(f"Bulk insert had some errors, processing individually: {bulk_error}")
                    imported_count = 0
                    for doc in documents:
                        try:
                            self.training_collection.insert_one(doc)
                            imported_count += 1
                        except Exception:
                            skipped_count += 1
                    logger.info(f"Imported {imported_count} samples (skipped {skipped_count}) from {labeled_by}")
                    return imported_count
            else:
                logger.warning(f"No valid samples to import from {labeled_by}")
                return 0
            
        except Exception as e:
            logger.error(f"Error importing dataset: {e}")
            import traceback
            traceback.print_exc()
            return 0