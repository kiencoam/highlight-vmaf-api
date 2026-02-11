# Highlight VMAF API Documentation

## Overview

RESTful API for video highlight evaluation using VMAF (Video Multimethod Assessment Fusion).

## API Endpoints

Base URL: `http://localhost:8000`

### 1. Create Video Job

**POST** `/api/v1/videos`

Create a new video evaluation job and push to processing queue.

**Request Body:**

```json
{
  "original_url": "https://example.com/original.mp4",
  "highlight_url": "https://example.com/highlight.mp4",
  "title": "My Video Title"
}
```

**Response (201 Created):**

```json
{
  "code": 201,
  "status": "success",
  "message": "Video created successfully",
  "data": {
    "id": 123,
    "original_url": "https://example.com/original.mp4",
    "highlight_url": "https://example.com/highlight.mp4",
    "title": "My Video Title",
    "status": 0
  }
}
```

**cURL Example:**

```bash
curl -X POST "http://localhost:8000/api/v1/videos" \
  -H "Content-Type: application/json" \
  -d '{
    "original_url": "https://example.com/original.mp4",
    "highlight_url": "https://example.com/highlight.mp4",
    "title": "My Video Title"
  }'
```

---

### 2. Batch Create Videos

**POST** `/api/v1/videos/batch`

Create multiple video evaluation jobs at once (bulk insert).

**Request Body:**

```json
{
  "videos": [
    {
      "original_url": "https://example.com/original1.mp4",
      "highlight_url": "https://example.com/highlight1.mp4",
      "title": "Video 1"
    },
    {
      "original_url": "https://example.com/original2.mp4",
      "highlight_url": "https://example.com/highlight2.mp4",
      "title": "Video 2"
    }
  ]
}
```

**Constraints:**

- Minimum: 1 video
- Maximum: 100 videos per request

**Response (201 Created):**

```json
{
  "code": 201,
  "status": "success",
  "message": "2 videos created, 0 failed",
  "data": {
    "total": 2,
    "success_count": 2,
    "failed_count": 0,
    "results": [
      {
        "success": true,
        "video_id": 123,
        "error": null,
        "video_data": {
          "id": 123,
          "original_url": "https://example.com/original1.mp4",
          "highlight_url": "https://example.com/highlight1.mp4",
          "title": "Video 1",
          "status": 0
        }
      },
      {
        "success": true,
        "video_id": 124,
        "error": null,
        "video_data": {
          "id": 124,
          "original_url": "https://example.com/original2.mp4",
          "highlight_url": "https://example.com/highlight2.mp4",
          "title": "Video 2",
          "status": 0
        }
      }
    ]
  }
}
```

**Partial Success Response:**

```json
{
  "code": 201,
  "status": "success",
  "message": "2 videos created, 1 failed",
  "data": {
    "total": 3,
    "success_count": 2,
    "failed_count": 1,
    "results": [
      {
        "success": true,
        "video_id": 123,
        "error": null,
        "video_data": { ... }
      },
      {
        "success": false,
        "video_id": null,
        "error": "Failed to insert video into database",
        "video_data": null
      },
      {
        "success": true,
        "video_id": 125,
        "error": null,
        "video_data": { ... }
      }
    ]
  }
}
```

**cURL Example:**

```bash
curl -X POST "http://localhost:8000/api/v1/videos/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "videos": [
      {
        "original_url": "https://example.com/original1.mp4",
        "highlight_url": "https://example.com/highlight1.mp4",
        "title": "Video 1"
      },
      {
        "original_url": "https://example.com/original2.mp4",
        "highlight_url": "https://example.com/highlight2.mp4",
        "title": "Video 2"
      }
    ]
  }'
```

---

### 3. Get Videos List

**GET** `/api/v1/videos`

Get paginated list of videos with search and sorting capabilities.

**Query Parameters:**

- `page` (int, optional): Page number (default: 1, min: 1)
- `size` (int, optional): Items per page (default: 10, min: 1, max: 100)
- `order_by` (string, optional): Sort column - id, title, status (default: id)
- `order_direction` (string, optional): asc or desc (default: desc)
- `status_filter` (int, optional): Filter by status code
- `query` (string, optional): Search in title (partial match)

**Response (200 OK):**

```json
{
  "code": 200,
  "status": "success",
  "message": "Videos retrieved successfully",
  "data": {
    "totalItems": 100,
    "totalPages": 10,
    "currentPage": 1,
    "items": [
      {
        "id": 123,
        "original_url": "https://example.com/original.mp4",
        "highlight_url": "https://example.com/highlight.mp4",
        "title": "My Video Title",
        "status": 0
      }
    ]
  }
}
```

**cURL Examples:**

Basic request:

```bash
curl "http://localhost:8000/api/v1/videos?page=1&size=10"
```

With search and filters:

```bash
curl "http://localhost:8000/api/v1/videos?page=1&size=20&query=highlight&status=0&order_by=title&order_direction=asc"
```

---

### 4. Get Video Highlights

**GET** `/api/v1/videos/{video_id}/highlights`

Get paginated list of highlight segments for a specific video.

**Path Parameters:**

- `video_id` (int, required): Video ID

**Query Parameters:**

- `page` (int, optional): Page number (default: 1, min: 1)
- `size` (int, optional): Items per page (default: 10, min: 1, max: 100)
- `order_by` (string, optional): Sort column (default: id)
- `order_direction` (string, optional): asc or desc (default: desc)

**Response (200 OK):**

```json
{
  "code": 200,
  "status": "success",
  "message": "Highlights retrieved successfully",
  "data": {
    "totalItems": 50,
    "totalPages": 5,
    "currentPage": 1,
    "items": [
      {
        "id": 1,
        "video_id": 123,
        "vmaf_mean": 95.5,
        "vmaf_min": 90.2,
        "vmaf_max": 98.7,
        "duration": 15.5,
        "start_time": 10.0,
        "end_time": 25.5
      }
    ]
  }
}
```

**cURL Examples:**

Basic request:

```bash
curl "http://localhost:8000/api/v1/videos/123/highlights"
```

With pagination and sorting:

```bash
curl "http://localhost:8000/api/v1/videos/123/highlights?page=2&size=20&order_by=vmaf_mean&order_direction=desc"
```

---

### 5. Health Check

**GET** `/health`

Check if the API is running.

**Response:**

```json
{
  "status": "healthy",
  "service": "highlight-vmaf-api"
}
```

---

## Response Format

All API responses follow this standard format:

```json
{
  "code": 200,
  "status": "success",
  "message": "Description of the result",
  "data": {
    // Response data here
  }
}
```

### Status Codes

- `200` - OK (successful GET)
- `201` - Created (successful POST)
- `400` - Bad Request (invalid input)
- `404` - Not Found
- `500` - Internal Server Error

### Status Values

- `success` - Operation completed successfully
- `failed` - Operation failed

### Pagination Format

For paginated endpoints, `data` contains:

```json
{
  "totalItems": 100,
  "totalPages": 10,
  "currentPage": 1,
  "items": [...]
}
```

## Interactive Documentation

Once the API is running, you can access:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## Error Handling

Error responses follow the same format:

```json
{
  "code": 400,
  "status": "failed",
  "message": "Error description",
  "data": null
}
```

## Notes

- The worker process (`main.py`) should be running separately to process jobs from the Redis queue
- Video status codes: 0 = Pending, 1 = Processing, 2 = Completed, 3 = Failed
- Maximum page size is limited to 100 items
- Search queries are case-insensitive and support partial matches
