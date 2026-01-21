"""
Redis-based caching service for improved performance
Falls back to in-memory cache if Redis is not available
"""

import logging
import json
import time
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CacheService:
    """
    Caching service with Redis backend and in-memory fallback
    """
    
    def __init__(self, config):
        """
        Initialize cache service
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.redis_client = None
        self.memory_cache = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        
        # Try to connect to Redis
        self._init_redis()
        
        logger.info(f"Cache service initialized with {'Redis' if self.redis_client else 'memory'} backend")
    
    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            import redis
            redis_url = getattr(self.config, 'REDIS_URL', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established")
            
        except Exception as e:
            # Redis is optional - silently fall back to memory cache
            logger.debug(f"Redis not available, using memory cache: {e}")
            self.redis_client = None
    
    def _get_cache_key(self, prefix: str, key: str) -> str:
        """Generate cache key"""
        return f"{prefix}:{key}"
    
    def get(self, prefix: str, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            prefix: Cache prefix
            key: Cache key
            
        Returns:
            Cached value or None
        """
        cache_key = self._get_cache_key(prefix, key)
        
        try:
            if self.redis_client:
                value = self.redis_client.get(cache_key)
                if value:
                    self.cache_stats['hits'] += 1
                    return json.loads(value)
                else:
                    self.cache_stats['misses'] += 1
                    return None
            else:
                # Memory cache
                if cache_key in self.memory_cache:
                    entry = self.memory_cache[cache_key]
                    if entry['expires'] > time.time():
                        self.cache_stats['hits'] += 1
                        return entry['value']
                    else:
                        del self.memory_cache[cache_key]
                
                self.cache_stats['misses'] += 1
                return None
                
        except Exception as e:
            logger.error(f"Error getting from cache: {e}")
            self.cache_stats['misses'] += 1
            return None
    
    def set(self, prefix: str, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Set value in cache
        
        Args:
            prefix: Cache prefix
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        cache_key = self._get_cache_key(prefix, key)
        
        try:
            if self.redis_client:
                serialized = json.dumps(value, default=str)
                self.redis_client.setex(cache_key, ttl, serialized)
                self.cache_stats['sets'] += 1
                return True
            else:
                # Memory cache
                self.memory_cache[cache_key] = {
                    'value': value,
                    'expires': time.time() + ttl
                }
                self.cache_stats['sets'] += 1
                return True
                
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False
    
    def delete(self, prefix: str, key: str) -> bool:
        """
        Delete value from cache
        
        Args:
            prefix: Cache prefix
            key: Cache key
            
        Returns:
            True if successful
        """
        cache_key = self._get_cache_key(prefix, key)
        
        try:
            if self.redis_client:
                result = self.redis_client.delete(cache_key)
                self.cache_stats['deletes'] += 1
                return result > 0
            else:
                # Memory cache
                if cache_key in self.memory_cache:
                    del self.memory_cache[cache_key]
                    self.cache_stats['deletes'] += 1
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Error deleting from cache: {e}")
            return False
    
    def clear_prefix(self, prefix: str) -> int:
        """
        Clear all keys with given prefix
        
        Args:
            prefix: Prefix to clear
            
        Returns:
            Number of keys cleared
        """
        try:
            if self.redis_client:
                pattern = f"{prefix}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
            else:
                # Memory cache
                keys_to_delete = [key for key in self.memory_cache.keys() if key.startswith(f"{prefix}:")]
                for key in keys_to_delete:
                    del self.memory_cache[key]
                return len(keys_to_delete)
                
        except Exception as e:
            logger.error(f"Error clearing cache prefix: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        stats = {
            'backend': 'redis' if self.redis_client else 'memory',
            'hit_rate': round(hit_rate, 2),
            'total_requests': total_requests,
            'memory_cache_size': len(self.memory_cache) if not self.redis_client else 0,
            **self.cache_stats
        }
        
        if self.redis_client:
            try:
                info = self.redis_client.info()
                stats.update({
                    'redis_memory_used': info.get('used_memory_human', 'N/A'),
                    'redis_connected_clients': info.get('connected_clients', 0),
                    'redis_total_commands_processed': info.get('total_commands_processed', 0)
                })
            except:
                pass
        
        return stats
    
    def cleanup_expired(self):
        """Clean up expired entries from memory cache"""
        if not self.redis_client:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self.memory_cache.items()
                if entry['expires'] <= current_time
            ]
            for key in expired_keys:
                del self.memory_cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

# Cache prefixes
class CachePrefixes:
    ALERTS = "alerts"
    TRAFFIC_STATS = "traffic"
    USER_ACTIVITIES = "users"
    SYSTEM_INFO = "system"
    ALERT_SUMMARY = "alert_summary"
    TRAFFIC_SUMMARY = "traffic_summary"
    INSIDER_SUMMARY = "insider_summary"

# Cache TTL constants (in seconds)
class CacheTTL:
    SHORT = 60      # 1 minute
    MEDIUM = 300    # 5 minutes
    LONG = 1800     # 30 minutes
    VERY_LONG = 3600  # 1 hour
