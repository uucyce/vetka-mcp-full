"""
VETKA OCR Routes - FastAPI Version

@file ocr_routes.py
@status ACTIVE
@phase Phase 39.6
@lastAudit 2026-01-05

OCR processing API routes.
Migrated from src/server/routes/ocr_routes.py (Flask Blueprint)

Endpoints:
- GET /api/ocr/status - Get OCR processor status
- POST /api/ocr/reset - Reset OCR processor
- POST /api/ocr/cache/clear - Clear OCR cache
- POST /api/ocr/process - Process image/PDF with OCR

Changes from Flask version:
- Blueprint -> APIRouter
- request.get_json() -> Pydantic BaseModel
- request.headers/remote_addr -> Request
- return jsonify({}) -> return {}
- def -> async def
"""

import os
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional


router = APIRouter(prefix="/api/ocr", tags=["ocr"])


# Rate limiter for OCR API (10 requests per minute per IP)
from src.ocr.ocr_processor import RateLimiter as OCRRateLimiter
_ocr_api_rate_limiter = OCRRateLimiter(max_calls=10, period=60)


# ============================================================
# PYDANTIC MODELS
# ============================================================

class OCRProcessRequest(BaseModel):
    """Request to process file with OCR."""
    path: str


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _check_ocr_rate_limit(request: Request) -> Optional[dict]:
    """
    Check rate limit per client IP and return error dict if exceeded.
    """
    # Get client IP (support for proxies via X-Forwarded-For)
    client_ip = request.headers.get('X-Forwarded-For', request.client.host if request.client else 'unknown')
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()

    if not _ocr_api_rate_limiter.is_allowed(key=client_ip):
        wait_time = _ocr_api_rate_limiter.get_wait_time(key=client_ip)
        return {
            'success': False,
            'error': f'Rate limit exceeded. Try again in {int(wait_time)}s',
            'retry_after': int(wait_time),
            'client_ip': client_ip
        }
    return None


# ============================================================
# ROUTES
# ============================================================

@router.get("/status")
async def ocr_status():
    """
    Get OCR processor status.

    Status endpoint is not rate-limited (informational only).
    """
    try:
        from src.ocr.ocr_processor import get_ocr_processor
        ocr = get_ocr_processor()
        return {
            'success': True,
            **ocr.get_status()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def ocr_reset(request: Request):
    """
    Reset OCR processor to pick up new models.

    Rate limited: 10 requests per minute.
    """
    # Check rate limit
    rate_limit_error = _check_ocr_rate_limit(request)
    if rate_limit_error:
        raise HTTPException(status_code=429, detail=rate_limit_error)

    try:
        from src.ocr.ocr_processor import reset_ocr_processor
        result = reset_ocr_processor()

        if not result.get('success'):
            # OCR is currently processing - return 409 Conflict
            raise HTTPException(status_code=409, detail=result)

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear")
async def ocr_cache_clear(request: Request):
    """
    Clear OCR cache.

    Rate limited: 10 requests per minute.
    """
    # Check rate limit
    rate_limit_error = _check_ocr_rate_limit(request)
    if rate_limit_error:
        raise HTTPException(status_code=429, detail=rate_limit_error)

    try:
        from src.ocr.ocr_processor import get_ocr_processor
        ocr = get_ocr_processor()
        count = ocr.clear_cache()
        return {
            'success': True,
            'cleared': count,
            'message': f'Cleared {count} cached OCR results'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process")
async def ocr_process(req: OCRProcessRequest, request: Request):
    """
    Process a single image or PDF with OCR.

    Rate limited: 10 requests per minute.
    """
    # Check rate limit at API level
    rate_limit_error = _check_ocr_rate_limit(request)
    if rate_limit_error:
        raise HTTPException(status_code=429, detail=rate_limit_error)

    try:
        from src.ocr.ocr_processor import get_ocr_processor

        if not req.path:
            raise HTTPException(status_code=400, detail="path is required")

        if not os.path.exists(req.path):
            raise HTTPException(status_code=404, detail=f"File not found: {req.path}")

        ocr = get_ocr_processor()
        ext = os.path.splitext(req.path)[1].lower()

        if ext == '.pdf':
            result = ocr.process_pdf(req.path)
        else:
            result = ocr.process_image(req.path)

        # Check for rate limit error from processor
        if result.get('error') and 'Rate limit' in result.get('error', ''):
            raise HTTPException(status_code=429, detail=result)

        return {
            'success': not result.get('error'),
            'path': req.path,
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail={'error': str(e), 'traceback': traceback.format_exc()})
