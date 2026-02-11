from config.log import logger
import time
import threading
from typing import Optional, List, Set, Any
from redis import Redis
from redis.exceptions import RedisError, ConnectionError, TimeoutError
from config.redis_config import RedisConfig


class RedisClient:
    """Thread-safe Singleton Redis Client for Redis Cloud"""
    
    _instance: Optional['RedisClient'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Ensure only one instance exists"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize connection (only once)"""
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._initialized = False
        self.client: Optional[Redis] = None
        self._connect()
        self._initialized = True
    
    def _connect(self):
        """Internal connection method"""
        try:
            logger.info(f"Connecting to Redis at {RedisConfig.HOST}:{RedisConfig.PORT}...")
            
            # Create Redis client (single instance, NOT cluster)
            self.client = Redis(**RedisConfig.get_connection_params())
            
            # Test connection
            self.client.ping()
            logger.info("✅ Connected to Redis successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise
    
    @staticmethod
    def get_instance() -> 'RedisClient':
        """Get singleton instance"""
        if RedisClient._instance is None:
            RedisClient()
        return RedisClient._instance
    
    @staticmethod
    def reset():
        """Reconnect to Redis (keep instance alive)"""
        with RedisClient._lock:
            if RedisClient._instance:
                try:
                    logger.info("♻️ Reconnecting to Redis...")
                    if RedisClient._instance.client:
                        RedisClient._instance.client.close()
                    
                    # Reconnect - keep instance
                    RedisClient._instance._initialized = False
                    RedisClient._instance._connect()
                    RedisClient._instance._initialized = True
                    
                    logger.info("♻️ Redis reconnected successfully")
                except Exception as e:
                    logger.error(f"Reset failed: {e}")
                    raise
    
    def _retry_operation(self, func, *args, max_retries=3, **kwargs):
        """Execute operation with retry on transient errors"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except (ConnectionError, TimeoutError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 0.1 * (2 ** attempt)
                    logger.warning(f"Retry {attempt+1}/{max_retries} after {wait_time}s: {e}")
                    time.sleep(wait_time)
        
        raise last_error
    
    def health_check(self) -> bool:
        """Check if connection is alive"""
        try:
            self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    # ======================= String Operations =======================
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Set key-value with optional TTL"""
        try:
            return self._retry_operation(self.client.set, key, value, ex=timeout)
        except RedisError as e:
            logger.error(f"Error SET key {key}: {e}")
            return False
    
    def set_if_absent(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Set key-value only if key doesn't exist (SETNX)"""
        try:
            result = self._retry_operation(self.client.set, key, value, ex=timeout, nx=True)
            return result or False
        except RedisError as e:
            logger.error(f"Error SETNX key {key}: {e}")
            return False
    
    def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        try:
            return self._retry_operation(self.client.get, key)
        except RedisError as e:
            logger.error(f"Error GET key {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete key"""
        try:
            return self._retry_operation(self.client.delete, key) > 0
        except RedisError as e:
            logger.error(f"Error DELETE key {key}: {e}")
            return False
    
    def has_key(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return self._retry_operation(self.client.exists, key) > 0
        except RedisError as e:
            logger.error(f"Error EXISTS key {key}: {e}")
            return False
    
    def expire(self, key: str, timeout: int) -> bool:
        """Set TTL for key"""
        try:
            return self._retry_operation(self.client.expire, key, timeout)
        except RedisError as e:
            logger.error(f"Error EXPIRE key {key}: {e}")
            return False
    
    def get_expire(self, key: str) -> int:
        """Get TTL of key (-1 if no TTL, -2 if not exists)"""
        try:
            return self._retry_operation(self.client.ttl, key)
        except RedisError as e:
            logger.error(f"Error TTL key {key}: {e}")
            return -2
    
    # ======================= List Operations =======================
    
    def lpush(self, key: str, value: Any) -> int:
        """Push value to left of list"""
        try:
            return self._retry_operation(self.client.lpush, key, value)
        except RedisError as e:
            logger.error(f"Error LPUSH key {key}: {e}")
            return 0
    
    def rpush(self, key: str, value: Any) -> int:
        """Push value to right of list"""
        try:
            return self._retry_operation(self.client.rpush, key, value)
        except RedisError as e:
            logger.error(f"Error RPUSH key {key}: {e}")
            return 0
    
    def lpop(self, key: str) -> Optional[str]:
        """Pop value from left of list"""
        try:
            return self._retry_operation(self.client.lpop, key)
        except RedisError as e:
            logger.error(f"Error LPOP key {key}: {e}")
            return None
    
    def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get range of list elements"""
        try:
            return self._retry_operation(self.client.lrange, key, start, end)
        except RedisError as e:
            logger.error(f"Error LRANGE key {key}: {e}")
            return []
    
    # ======================= Set Operations =======================
    
    def sadd(self, key: str, *values: Any) -> int:
        """Add values to set"""
        try:
            return self._retry_operation(self.client.sadd, key, *values)
        except RedisError as e:
            logger.error(f"Error SADD key {key}: {e}")
            return 0
    
    def smembers(self, key: str) -> Set[str]:
        """Get all members of set"""
        try:
            return self._retry_operation(self.client.smembers, key)
        except RedisError as e:
            logger.error(f"Error SMEMBERS key {key}: {e}")
            return set()
    
    def sremove(self, key: str, *values: Any) -> int:
        """Remove values from set"""
        try:
            return self._retry_operation(self.client.srem, key, *values)
        except RedisError as e:
            logger.error(f"Error SREM key {key}: {e}")
            return 0
    
    # ======================= Scan Keys =======================
    
    def scan_keys(self, pattern: str, limit: int = 1000) -> Set[str]:
        """Scan keys matching pattern (with limit to prevent memory issues)"""
        keys = set()
        count = 0
        try:
            for key in self.client.scan_iter(match=pattern, count=100):
                keys.add(key)
                count += 1
                if count >= limit:
                    logger.warning(f"⚠️ Scan stopped at limit {limit}")
                    break
        except RedisError as e:
            logger.error(f"Error SCAN pattern {pattern}: {e}")
        return keys
    
    # ======================= BLPOP (Blocking Pop) =======================
    
    def blpop(self, key: str, timeout: int = 0) -> Optional[tuple]:
       
        try:
            result = self.client.blpop(key, timeout=timeout)
            return result  # None if timeout, tuple if data
            
        except ConnectionError as e:
            # CRITICAL: Only raise on real connection errors
            logger.error(f"❌ Connection error BLPOP key {key}: {e}")
            raise
            
        except RedisError as e:
            # Other errors: log and return None
            logger.error(f"⚠️ Redis error BLPOP key {key}: {e}")
            return None