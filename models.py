from pydantic import BaseModel, Field
from typing import Optional, Any, List, Literal

# ==================== Base Response Models ====================

class ApiResponse(BaseModel):
    """Base API Response"""
    code: int = Field(..., description="HTTP status code")
    status: Literal["success", "failed"] = Field(..., description="Status indicator")
    message: str = Field(..., description="Response message")
    data: Optional[Any] = Field(None, description="Response data")


class PaginationData(BaseModel):
    """Pagination response data"""
    totalItems: int = Field(..., description="Total number of items")
    totalPages: int = Field(..., description="Total number of pages")
    currentPage: int = Field(..., description="Current page number")
    items: List[Any] = Field(default_factory=list, description="List of items")


# ==================== Request Models ====================

class CreateVideoRequest(BaseModel):
    """Request body for creating video"""
    original_url: str = Field(..., description="Original video URL", min_length=1)
    highlight_url: str = Field(..., description="Highlight video URL", min_length=1)
    title: str = Field(..., description="Video title", min_length=1)


class BatchCreateVideoRequest(BaseModel):
    """Request body for batch creating videos"""
    videos: List[CreateVideoRequest] = Field(..., description="List of videos to create", min_items=1, max_items=100)


class VideoCreationResult(BaseModel):
    """Result of a single video creation"""
    success: bool = Field(..., description="Whether creation was successful")
    video_id: Optional[int] = Field(None, description="Created video ID if successful")
    error: Optional[str] = Field(None, description="Error message if failed")
    video_data: Optional[dict] = Field(None, description="Created video data if successful")


class BatchCreationResponse(BaseModel):
    """Response for batch video creation"""
    total: int = Field(..., description="Total number of videos in request")
    success_count: int = Field(..., description="Number of successfully created videos")
    failed_count: int = Field(..., description="Number of failed video creations")
    results: List[VideoCreationResult] = Field(..., description="Individual results for each video")


# ==================== Video Info Models ====================

class VideoInfo(BaseModel):
    """Video information model"""
    id: int
    original_url: str
    highlight_url: str
    title: str
    status: int

    class Config:
        from_attributes = True


class HighlightStats(BaseModel):
    """Highlight statistics model"""
    id: int
    video_id: int
    vmaf_mean: Optional[float] = None
    vmaf_min: Optional[float] = None
    vmaf_max: Optional[float] = None
    duration: Optional[float] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    class Config:
        from_attributes = True
