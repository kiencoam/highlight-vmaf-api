from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.log import logger
from api.video_routes import router as video_router
from utils.redis_util import RedisClient
from database.connection import MySQLConnectionPool
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup and shutdown)"""
    # Startup
    logger.info("FastAPI application starting...")
    
    # Initialize Redis connection
    try:
        redis_client = RedisClient.get_instance()
        if redis_client.health_check():
            logger.info("Redis connection established successfully")
        else:
            logger.error("Redis health check failed")
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        raise
    
    # Initialize MySQL connection pool
    try:
        app.state.db_pool = MySQLConnectionPool()
        logger.info("MySQL connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize MySQL connection pool: {e}")
        raise
    
    logger.info("FastAPI application started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI application...")
    
    # Close Redis connection
    try:
        redis_client = RedisClient.get_instance()
        if redis_client.client:
            redis_client.client.close()
            logger.info("Redis connection closed")
    except Exception as e:
        logger.error(f"Error closing Redis connection: {e}")
    
    logger.info("FastAPI application shutdown")


# Create FastAPI application
app = FastAPI(
    title="Highlight VMAF API",
    description="API for video highlight evaluation using VMAF",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register routers
app.include_router(video_router)


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "highlight-vmaf-api"
    }


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Highlight VMAF API",
        "docs": "/api/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
