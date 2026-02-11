import os
import socket
import logging


logger = logging.getLogger(__name__)

class RedisConfig:
    """
    Redis Cloud Configuration (Single Instance)
    Uses individual environment variables
    """
    
    # =========================================================================
    # 1. CONNECTION INFO
    # =========================================================================
    HOST = os.getenv("REDIS_HOST")
    PORT = int(os.getenv("REDIS_PORT", "6379"))
    USERNAME = os.getenv("REDIS_USERNAME", "default")
    DB = int(os.getenv("REDIS_DB", "0"))
    
    # Validate required fields
    if not HOST:
        raise ValueError(
            "REDIS_HOST is required.\n"
            "Set it in .env file: REDIS_HOST=redis-15129.c9.us-east-1-4.ec2.cloud.redislabs.com"
        )
    
    # =========================================================================
    # 2. PASSWORD & SECURITY
    # =========================================================================
    @staticmethod
    def _get_password() -> str:
        """Get and optionally decrypt Redis password"""
        raw_password = os.getenv("REDIS_PASSWORD")
        
        if not raw_password:
            raise ValueError(
                "REDIS_PASSWORD is required.\n"
                "Set it in .env file: REDIS_PASSWORD=your_password"
            )
        
        # Check if password needs decryption
        decrypt_enabled = os.getenv("REDIS_PASSWORD_ENCRYPTED", "false").lower() == "true"
        
        if decrypt_enabled:
            try:
                logger.info("Decrypting Redis password...")
                return raw_password  # Replace with actual decryption logic
            except Exception as e:
                logger.error(f"Password decryption failed: {e}")
                raise ValueError("Invalid encrypted password") from e
        
        # Return raw password
        logger.info("Using plaintext password (REDIS_PASSWORD_ENCRYPTED=false)")
        return raw_password
    
    PASSWORD = _get_password.__func__()
    
    # =========================================================================
    # 3. SSL/TLS (Important for Redis Cloud Production)
    # =========================================================================
    SSL_ENABLED = os.getenv("REDIS_SSL", "false").lower() == "true"
    SSL_CERT_REQS = "required" if SSL_ENABLED else None
    
    # =========================================================================
    # 4. TIMEOUTS & POOL
    # =========================================================================
    # Socket timeout for operations (seconds)
    SOCKET_TIMEOUT = float(os.getenv("REDIS_SOCKET_TIMEOUT", "10"))
    
    # Connection timeout (seconds)
    SOCKET_CONNECT_TIMEOUT = float(os.getenv("REDIS_CONNECT_TIMEOUT", "15"))
    
    # Max connections in pool
    MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
    
    # Auto decode bytes to UTF-8
    DECODE_RESPONSES = True
    
    # Retry settings
    MAX_RETRIES = int(os.getenv("REDIS_MAX_RETRIES", "3"))
    RETRY_ON_TIMEOUT = True
    
    # =========================================================================
    # 5. TCP KEEPALIVE (Critical for BLPOP long connections)
    # =========================================================================
    SOCKET_KEEPALIVE = True
    SOCKET_KEEPALIVE_OPTIONS = {}
    
    # Linux/Docker only - detect dead connections faster
    if hasattr(socket, 'TCP_KEEPIDLE'):
        SOCKET_KEEPALIVE_OPTIONS = {
            socket.TCP_KEEPIDLE: int(os.getenv("TCP_KEEPIDLE", "60")),
            socket.TCP_KEEPINTVL: int(os.getenv("TCP_KEEPINTVL", "10")),
            socket.TCP_KEEPCNT: int(os.getenv("TCP_KEEPCNT", "3"))
        }
        logger.info("✅ TCP Keepalive enabled with custom settings")
    else:
        logger.warning("⚠️ TCP_KEEPIDLE not available (Windows?), using OS defaults")
    
    # =========================================================================
    # 6. HEALTH CHECK
    # =========================================================================
    HEALTH_CHECK_INTERVAL = int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30"))
    
    # =========================================================================
    # 7. VALIDATION & CONNECTION PARAMS
    # =========================================================================
    @classmethod
    def validate(cls) -> bool:
        """Validate all configuration settings"""
        try:
            assert cls.HOST, "REDIS_HOST is not set"
            assert cls.PORT > 0, "Invalid REDIS_PORT"
            assert cls.PASSWORD, "REDIS_PASSWORD is not set"
            assert cls.SOCKET_TIMEOUT > 0, "Invalid REDIS_SOCKET_TIMEOUT"
            assert cls.MAX_CONNECTIONS > 0, "Invalid REDIS_MAX_CONNECTIONS"
            
            logger.info("✅ Redis configuration validated successfully")
            logger.info(f"📊 Connection Info:")
            logger.info(f"   Host: {cls.HOST}:{cls.PORT}")
            logger.info(f"   Username: {cls.USERNAME}")
            logger.info(f"   Database: {cls.DB}")
            logger.info(f"   SSL: {'Enabled' if cls.SSL_ENABLED else 'Disabled'}")
            logger.info(f"   Max Connections: {cls.MAX_CONNECTIONS}")
            logger.info(f"   Socket Timeout: {cls.SOCKET_TIMEOUT}s")
            logger.info(f"   Health Check Interval: {cls.HEALTH_CHECK_INTERVAL}s")
            
            return True
            
        except AssertionError as e:
            logger.error(f"❌ Redis configuration validation failed: {e}")
            raise
    
    @classmethod
    def get_connection_params(cls) -> dict:
        """
        Get all connection parameters for Redis client
        
        Returns:
            dict: Connection parameters ready for Redis(**params)
        """
        params = {
            "host": cls.HOST,
            "port": cls.PORT,
            "username": cls.USERNAME,
            "password": cls.PASSWORD,
            "db": cls.DB,
            "decode_responses": cls.DECODE_RESPONSES,
            "socket_timeout": cls.SOCKET_TIMEOUT,
            "socket_connect_timeout": cls.SOCKET_CONNECT_TIMEOUT,
            "max_connections": cls.MAX_CONNECTIONS,
            "socket_keepalive": cls.SOCKET_KEEPALIVE,
            "socket_keepalive_options": cls.SOCKET_KEEPALIVE_OPTIONS,
            "health_check_interval": cls.HEALTH_CHECK_INTERVAL,
        }
        
        # Add SSL if enabled
        if cls.SSL_ENABLED:
            params["ssl"] = True
            params["ssl_cert_reqs"] = cls.SSL_CERT_REQS
            logger.info("🔒 SSL/TLS enabled for Redis connection")
        
        return params
    
    # ✅ THÊM method này
    @classmethod
    def get_connection_info(cls) -> dict:
        """
        Get connection info for debugging/monitoring
        
        Returns:
            dict: Connection information (without sensitive data)
        """
        return {
            "host": cls.HOST,
            "port": cls.PORT,
            "username": cls.USERNAME,
            "db": cls.DB,
            "ssl": cls.SSL_ENABLED,
            "max_connections": cls.MAX_CONNECTIONS,
            "socket_timeout": cls.SOCKET_TIMEOUT,
            "health_check_interval": cls.HEALTH_CHECK_INTERVAL
        }