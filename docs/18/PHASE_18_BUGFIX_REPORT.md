# Phase 18 Bugfix Report

**Date:** 2025-12-28
**Version:** v2.0 → v2.1 → v2.1.1 (hotfix)
**Source:** Claude Haiku analysis (browser agent)

---

## Hotfix v2.1.1

**Issue:** Rate limiting was implemented inside `OCRProcessor.process_image()` but not at the Flask API level. Testing `/api/ocr/process` with 15 requests showed all 200 OK.

**Fix:** Added `_ocr_api_rate_limiter` at Flask level in `main.py`:
- Global `RateLimiter` instance (10 req/min)
- `_check_ocr_rate_limit()` helper function
- Applied to `/api/ocr/process`, `/api/ocr/reset`, `/api/ocr/cache/clear`
- `/api/ocr/status` is NOT rate-limited (informational only)

**Note:** Logging is server-side only (stdout), not sent to browser console. This is expected Flask behavior.

---

## Hotfix v2.1.2

**Issue:** Rate limiting used global key - all users shared one limit. Also, testers didn't wait 60s between tests, so limit appeared "stuck".

**Fix:** Per-IP rate limiting:
- Uses `X-Forwarded-For` header (proxy support) or `request.remote_addr`
- Each IP gets its own 10 req/min limit
- Returns `client_ip` in 429 response for debugging

**How RateLimiter works:**
```
Time 0s:  IP-A makes 10 requests → all OK
Time 0s:  IP-A makes 11th request → 429 (wait ~60s)
Time 0s:  IP-B makes 10 requests → all OK (separate limit)
Time 60s: IP-A's old requests expire → can make 10 more
```

**Test result:**
```
IP 192.168.1.1: OK OK OK 429 429
IP 192.168.1.2: OK OK OK 429 429  (separate limit!)
[wait 2.5s]
IP 192.168.1.1: OK OK OK  (reset works!)
```

---

## Bugs Fixed

| Bug | Issue | Fix |
|-----|-------|-----|
| BUG 1 | No error handling for Ollama calls | Added try-catch with ConnectionError, Timeout handling |
| BUG 2 | No timeout (6s blocks forever) | Added VISION_TIMEOUT=30s constant |
| BUG 3 | No caching (same image 10x = 60s wasted) | Added OCRCache class with file-hash and 1h TTL |
| BUG 4 | Confidence score undocumented | Added full docstring in `_calculate_confidence()` |
| BUG 5 | Memory leak on large PDFs | Changed to page-by-page processing with `del page` |
| BUG 6 | Tesseract+Ollama combo slow (4s) | Removed Ollama from fallback, pure Tesseract (0.2s) |
| BUG 7 | Reset endpoint unprotected | Added `is_processing` flag, returns 409 Conflict if busy |
| BUG 8 | No rate limiting | Added RateLimiter class (10 req/min) |
| BUG 9 | Logging insufficient | Added structured logging with request IDs |

---

## New Components

### OCRCache

```python
class OCRCache:
    """File-based cache with MD5 hash and TTL."""

    def __init__(self, cache_dir=".ocr_cache", ttl_seconds=3600):
        ...

    def get(self, file_path: str) -> Optional[Dict]
    def set(self, file_path: str, result: Dict) -> None
    def clear(self) -> int
```

### RateLimiter

```python
class RateLimiter:
    """In-memory rate limiter."""

    def __init__(self, max_calls=10, period=60):
        ...

    def is_allowed(self, key: str = 'global') -> bool
    def get_wait_time(self, key: str = 'global') -> float
```

---

## New API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ocr/cache/clear` | POST | Clear OCR cache |

### Reset Endpoint Changes

```python
# Before (v2.0):
POST /api/ocr/reset → 200 OK always

# After (v2.1):
POST /api/ocr/reset → 200 OK if idle
POST /api/ocr/reset → 409 Conflict if processing
```

---

## Performance After Fix

| Scenario | Before | After |
|----------|--------|-------|
| First image | 6s | 6s |
| Same image (cached) | 6s | <1ms |
| Ollama down | 500 error | Tesseract 0.2s |
| 15 requests | All processed | 10 OK, 5 rate-limited |

### Cache Test Results

```
First call (no cache)...
  Time: 5.58s
  Source: qwen-vision
  Cached: False

Second call (cached)...
  Time: 0.0003s
  Cached: True

Speed improvement: 17,176x faster!
```

### Fallback Test Results

```
Strategy: tesseract (Ollama down)
Source: tesseract
Confidence: 0.69
Time: 0.20s
```

---

## Confidence Score Documentation

### For Vision (Qwen)

| Factor | Score |
|--------|-------|
| Base | 0.70 |
| Text > 50 chars | +0.10 |
| Text > 200 chars | +0.05 |
| Description > 10 chars | +0.10 |
| Formatting (|, #, -, *) | +0.05 |
| Tables detected | +0.05 |
| **Maximum** | 0.99 |

### For Tesseract

| Factor | Score |
|--------|-------|
| Base (Tesseract confidence) | 0.0-1.0 |
| Text > 50 chars | +0.10 |
| Text > 200 chars | +0.05 |
| **Maximum** | 0.95 |

---

## Files Changed

| File | Changes |
|------|---------|
| `src/ocr/ocr_processor.py` | Rewritten v2.1 (830 lines) |
| `main.py` | +15 lines (cache clear endpoint, reset protection) |

---

## Logging Format

```
[vetka.ocr] [a6ded865] START file=screenshot.png
[vetka.ocr] [a6ded865] Trying Vision (qwen2.5vl:3b)...
[vetka.ocr] [a6ded865] SUCCESS source=qwen-vision conf=0.95 time=5580ms

# Or on cache hit:
[vetka.ocr] [d7a1d6a9] START file=screenshot.png
[vetka.ocr] [d7a1d6a9] CACHE HIT (0ms)

# Or on fallback:
[vetka.ocr] [b5b50d1c] Vision low confidence, trying Tesseract...
[vetka.ocr] [b5b50d1c] FALLBACK SUCCESS conf=0.69 time=201ms
```

---

## Summary

All 9 bugs from Haiku analysis fixed. OCRProcessor v2.1 is production-ready with:
- Robust error handling
- Smart caching (17,000x speedup on cache hit)
- Fast Tesseract fallback (0.2s vs 4s before)
- Rate limiting (10 req/min)
- Protected reset endpoint
- Structured logging with request IDs
