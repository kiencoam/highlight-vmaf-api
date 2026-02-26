from fastapi import APIRouter, Query, Path, status
from typing import Optional
import math
import json

from models import (
    ApiResponse, 
    CreateVideoRequest,
    BatchCreateVideoRequest,
    VideoCreationResult,
    BatchCreationResponse,
    PaginationData
)
from database.db_access import DBAccess
from utils.redis_util import RedisClient
from config.settings import QUEUE_NAME_V1, QUEUE_NAME_V2, PROCESSOR_VERSION
from config.log import logger


router = APIRouter(prefix="/api/v1", tags=["videos"])

# Initialize dependencies
db = DBAccess()
redis_client = RedisClient.get_instance()


# ==================== Helper Functions ====================

def create_success_response(data: any, message: str = "Success", code: int = 200) -> ApiResponse:
    """Create success response"""
    return ApiResponse(
        code=code,
        status="success",
        message=message,
        data=data
    )


def create_error_response(message: str, code: int = 400) -> ApiResponse:
    """Create error response"""
    return ApiResponse(
        code=code,
        status="failed",
        message=message,
        data=None
    )


def create_pagination_data(items: list, total_items: int, current_page: int, page_size: int) -> PaginationData:
    """Create pagination data structure"""
    total_pages = math.ceil(total_items / page_size) if page_size > 0 else 0
    
    return PaginationData(
        totalItems=total_items,
        totalPages=total_pages,
        currentPage=current_page,
        items=items
    )


# ==================== API 1: Create Video ====================

@router.post("/videos", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_video(request: CreateVideoRequest):
    """
    Create new video and push to Redis queue
    
    - **original_url**: URL of the original video
    - **highlight_url**: URL of the highlight video
    - **title**: Video title
    """
    try:
        # 1. Insert into database
        result = db.insert_video_info(
            original_url=request.original_url,
            highlight_url=request.highlight_url,
            title=request.title
        )
        
        if not result:
            logger.error("Failed to insert video into database")
            return create_error_response(
                message="Failed to create video",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        video_id = result.get("id")
        
        # 2. Push to Redis queue
        try:
            if PROCESSOR_VERSION == "v1":
                redis_client.lpush(QUEUE_NAME_V1, str(video_id))
                logger.info(f"Video ID {video_id} pushed to Redis queue: {QUEUE_NAME_V1}")
            elif PROCESSOR_VERSION == "v2":
                video_job_data = {
                    "video_id": video_id,
                    "original_url": request.original_url,
                    "highlight_url": request.highlight_url,
                }
                redis_client.lpush(QUEUE_NAME_V2, json.dumps(video_job_data))
                logger.info(f"Video ID {video_id} pushed to Redis queue: {QUEUE_NAME_V2}")
        except Exception as redis_error:
            logger.error(f"Failed to push to Redis: {redis_error}")
            # Note: Video is already in DB, so we don't fail the request
            # But we log the error for monitoring
        
        # 3. Return success response
        return create_success_response(
            data=result,
            message="Video created successfully",
            code=status.HTTP_201_CREATED
        )
        
    except Exception as e:
        logger.error(f"Error in create_video: {e}")
        return create_error_response(
            message=f"Internal server error: {str(e)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==================== API 2: Batch Create Videos ====================

@router.post("/videos/batch", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def batch_create_videos(request: BatchCreateVideoRequest):
    """
    Create multiple videos at once and push to Redis queue
    
    - **videos**: List of videos to create (max 100 at once)
    
    Returns detailed results for each video creation attempt.
    """
    results = []
    success_count = 0
    failed_count = 0
    
    try:
        # Process each video in the list
        for idx, video_req in enumerate(request.videos):
            try:
                # 1. Insert into database
                result = db.insert_video_info(
                    original_url=video_req.original_url,
                    highlight_url=video_req.highlight_url,
                    title=video_req.title
                )
                
                if not result:
                    failed_count += 1
                    results.append(VideoCreationResult(
                        success=False,
                        error="Failed to insert video into database",
                        video_id=None,
                        video_data=None
                    ))
                    logger.error(f"Failed to insert video #{idx + 1}: {video_req.title}")
                    continue
                
                video_id = result.get("id")
                
                # 2. Push to Redis queue
                try:
                    if PROCESSOR_VERSION == "v1":
                        redis_client.lpush(QUEUE_NAME_V1, str(video_id))
                        logger.info(f"Video ID {video_id} pushed to Redis queue: {QUEUE_NAME_V1}")
                    elif PROCESSOR_VERSION == "v2":
                        video_job_data = {
                            "video_id": video_id,
                            "original_url": video_req.original_url,
                            "highlight_url": video_req.highlight_url,
                        }
                        redis_client.lpush(QUEUE_NAME_V2, json.dumps(video_job_data))
                        logger.info(f"Video ID {video_id} pushed to Redis queue: {QUEUE_NAME_V2}")
                except Exception as redis_error:
                    logger.warning(f"Failed to push video ID {video_id} to Redis: {redis_error}")
                    # Video is already in DB, so we still count it as success
                
                # 3. Record success
                success_count += 1
                results.append(VideoCreationResult(
                    success=True,
                    video_id=video_id,
                    video_data=result,
                    error=None
                ))
                
            except Exception as video_error:
                failed_count += 1
                results.append(VideoCreationResult(
                    success=False,
                    error=str(video_error),
                    video_id=None,
                    video_data=None
                ))
                logger.error(f"Error processing video #{idx + 1}: {video_error}")
        
        # 4. Create batch response
        batch_response = BatchCreationResponse(
            total=len(request.videos),
            success_count=success_count,
            failed_count=failed_count,
            results=results
        )
        
        # 5. Return response based on overall success
        if success_count == len(request.videos):
            message = f"All {success_count} videos created successfully"
        elif success_count > 0:
            message = f"{success_count} videos created, {failed_count} failed"
        else:
            message = "All videos failed to create"
        
        return create_success_response(
            data=batch_response.dict(),
            message=message,
            code=status.HTTP_201_CREATED
        )
        
    except Exception as e:
        logger.error(f"Error in batch_create_videos: {e}")
        return create_error_response(
            message=f"Internal server error: {str(e)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==================== API 3: Get Videos List ====================

@router.get("/videos", response_model=ApiResponse)
async def get_videos(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    order_by: str = Query("id", description="Column to sort by (id, title, status)"),
    order_direction: str = Query("desc", pattern="^(asc|desc)$", description="Sort direction"),
    status_filter: Optional[int] = Query(None, description="Filter by status"),
    query: Optional[str] = Query(None, description="Search by title")
):
    """
    Get paginated list of videos with search and sorting
    
    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 10, max: 100)
    - **order_by**: Sort column (default: id)
    - **order_direction**: asc or desc (default: desc)
    - **status_filter**: Filter by status (optional)
    - **query**: Search in title (optional)
    """
    try:
        # 1. Get videos list
        videos = db.get_video_page(
            page=page,
            size=size,
            order_by=order_by,
            order_direction=order_direction,
            status=status_filter,
            query=query
        )
        
        # 2. Get total count
        total_count = db.get_video_count(
            query=query,
            status=status_filter
        )
        
        # 3. Create pagination data
        pagination_data = create_pagination_data(
            items=videos,
            total_items=total_count,
            current_page=page,
            page_size=size
        )
        
        # 4. Return success response
        return create_success_response(
            data=pagination_data.dict(),
            message="Videos retrieved successfully",
            code=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error in get_videos: {e}")
        return create_error_response(
            message=f"Internal server error: {str(e)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==================== API 4: Get Video Highlights ====================

@router.get("/videos/{video_id}/highlights", response_model=ApiResponse)
async def get_video_highlights(
    video_id: int = Path(..., ge=1, description="Video ID"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    order_by: str = Query("id", description="Column to sort by"),
    order_direction: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction")
):
    """
    Get paginated list of highlights for a specific video
    
    - **video_id**: ID of the video
    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 10, max: 100)
    - **order_by**: Sort column (default: id)
    - **order_direction**: asc or desc (default: desc)
    """
    try:
        # 1. Get highlights list
        highlights = db.get_highlight_page(
            video_id=video_id,
            page=page,
            size=size,
            order_by=order_by,
            order_direction=order_direction
        )
        
        # 2. Get total count
        total_count = db.get_highlight_count(video_id=video_id)
        
        # 3. Create pagination data
        pagination_data = create_pagination_data(
            items=highlights,
            total_items=total_count,
            current_page=page,
            page_size=size
        )
        
        # 4. Return success response
        return create_success_response(
            data=pagination_data.dict(),
            message="Highlights retrieved successfully",
            code=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error in get_video_highlights: {e}")
        return create_error_response(
            message=f"Internal server error: {str(e)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ==================== API 5: Get Highlight Frames ====================

@router.get("/highlights/{highlight_id}/frames", response_model=ApiResponse)
async def get_highlight_frames(
    highlight_id: int = Path(..., ge=1, description="Highlight ID"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    order_by: str = Query("id", description="Column to sort by"),
    order_direction: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction")
):
    """
    Get paginated list of frames for a specific highlight
    
    - **highlight_id**: ID of the highlight
    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 10, max: 100)
    - **order_by**: Sort column (default: id)
    - **order_direction**: asc or desc (default: asc)
    """
    try:
        # 1. Get frames list
        frames = db.get_frame_page(
            highlight_id=highlight_id,
            page=page,
            size=size,
            order_by=order_by,
            order_direction=order_direction
        )
        
        # 2. Get total count
        total_count = db.get_frame_count(highlight_id=highlight_id)
        
        # 3. Create pagination data
        pagination_data = create_pagination_data(
            items=frames,
            total_items=total_count,
            current_page=page,
            page_size=size
        )
        
        # 4. Return success response
        return create_success_response(
            data=pagination_data.dict(),
            message="Frames retrieved successfully",
            code=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error in get_highlight_frames: {e}")
        return create_error_response(
            message=f"Internal server error: {str(e)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )