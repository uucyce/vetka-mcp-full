"""
VETKA OCR & Vision Processor v2.1.

Primary: Qwen2.5-VL (OCR + image understanding)
Fallback: Tesseract (fast, no Ollama)

Phase 18 v2.1: Bugfixes
- Error handling for Ollama calls
- 30s timeout on Vision
- File-hash caching (1h TTL)
- Documented confidence calculation
- PDF page-by-page processing (memory safe)
- Removed Ollama from Tesseract fallback
- Protected reset endpoint (is_processing flag)
- Rate limiting (10 req/min)
- Structured logging

@status: active
@phase: 96
@depends: subprocess, PIL, pytesseract, requests, logging, threading
@used_by: src.ocr, src.api.routes, file indexing pipeline
"""

import subprocess
import re
import os
import time
import base64
import json
import hashlib
import logging
import threading
import uuid
from pathlib import Path
from typing import Optional, Dict, List, Any
from collections import defaultdict
from datetime import datetime

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Configure logger
logger = logging.getLogger('vetka.ocr')
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[%(name)s] %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class OCRCache:
    """Simple file-based OCR cache with TTL."""

    def __init__(self, cache_dir: str = ".ocr_cache", ttl_seconds: int = 3600):
        self.cache_dir = cache_dir
        self.ttl = ttl_seconds
        os.makedirs(cache_dir, exist_ok=True)

    def _get_file_hash(self, file_path: str) -> str:
        """MD5 hash of file content."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    def _cache_path(self, file_hash: str) -> str:
        return os.path.join(self.cache_dir, f"{file_hash}.json")

    def get(self, file_path: str) -> Optional[Dict]:
        """Get cached result if exists and not expired."""
        file_hash = self._get_file_hash(file_path)
        if not file_hash:
            return None

        cache_file = self._cache_path(file_hash)

        if os.path.exists(cache_file):
            # Check cache age
            if time.time() - os.path.getmtime(cache_file) < self.ttl:
                try:
                    with open(cache_file, 'r') as f:
                        result = json.load(f)
                        result['cached'] = True
                        return result
                except Exception:
                    pass
        return None

    def set(self, file_path: str, result: Dict) -> None:
        """Cache result."""
        file_hash = self._get_file_hash(file_path)
        if not file_hash:
            return

        cache_file = self._cache_path(file_hash)

        try:
            # Remove 'cached' flag before storing
            to_store = {k: v for k, v in result.items() if k != 'cached'}
            with open(cache_file, 'w') as f:
                json.dump(to_store, f)
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")

    def clear(self) -> int:
        """Clear all cache files. Returns count of deleted files."""
        count = 0
        try:
            for f in os.listdir(self.cache_dir):
                if f.endswith('.json'):
                    os.unlink(os.path.join(self.cache_dir, f))
                    count += 1
        except Exception:
            pass
        return count


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, max_calls: int = 10, period: int = 60):
        self.max_calls = max_calls
        self.period = period
        self.calls: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, key: str = 'global') -> bool:
        """Check if request is allowed."""
        with self._lock:
            now = time.time()

            # Remove old calls
            self.calls[key] = [t for t in self.calls[key] if now - t < self.period]

            if len(self.calls[key]) >= self.max_calls:
                return False

            self.calls[key].append(now)
            return True

    def get_wait_time(self, key: str = 'global') -> float:
        """Get seconds until next request is allowed."""
        with self._lock:
            if not self.calls[key]:
                return 0

            now = time.time()
            oldest = min(self.calls[key])
            wait = self.period - (now - oldest)
            return max(0, wait)


class OCRProcessor:
    """
    Vision-first OCR processor for VETKA.

    Strategy:
    1. Qwen2.5-VL (primary) - best quality, understands images
    2. Tesseract (fallback) - fast, no Ollama structuring

    Features (v2.1):
    - Caching with 1h TTL
    - Rate limiting (10 req/min)
    - 30s timeout on Vision calls
    - Thread-safe processing flag

    Supported formats:
    - Images: PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP
    - Documents: PDF (scanned or text-based)
    """

    SUPPORTED_IMAGES = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
    SUPPORTED_DOCS = {'.pdf'}

    # Timeouts
    VISION_TIMEOUT = 30  # seconds
    TESSERACT_TIMEOUT = 10  # seconds

    # Tesseract config
    TESSERACT_CONFIG = '--oem 3 --psm 3'

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.tesseract_ok = self._check_tesseract()
        self.ollama_ok = self._check_ollama()
        self.vision_model = self._find_vision_model()
        self.text_model = self._find_text_model()

        # v2.1: New components
        self.cache = OCRCache()
        self.rate_limiter = RateLimiter(max_calls=10, period=60)
        self._processing_lock = threading.Lock()
        self._is_processing = False

        logger.info(f"Tesseract: {'OK' if self.tesseract_ok else 'NOT AVAILABLE'}")
        logger.info(f"Ollama: {'OK' if self.ollama_ok else 'NOT AVAILABLE'}")
        logger.info(f"Vision model: {self.vision_model or 'NOT FOUND'}")
        logger.info(f"Text model: {self.text_model or 'NOT FOUND'}")

        if self.vision_model:
            logger.info(f"Strategy: Vision-first (Qwen) + Tesseract fallback")
        elif self.tesseract_ok:
            logger.info(f"Strategy: Tesseract only (install qwen2.5vl for better quality)")
        else:
            logger.warning(f"No OCR available!")

    @property
    def is_processing(self) -> bool:
        """Thread-safe check if currently processing."""
        with self._processing_lock:
            return self._is_processing

    def _set_processing(self, value: bool):
        """Thread-safe set processing flag."""
        with self._processing_lock:
            self._is_processing = value

    def _check_tesseract(self) -> bool:
        """Check if Tesseract is installed."""
        if not TESSERACT_AVAILABLE:
            return False
        try:
            subprocess.run(['tesseract', '--version'],
                          capture_output=True, check=True, timeout=5)
            return True
        except Exception:
            return False

    def _check_ollama(self) -> bool:
        """Check if Ollama is running."""
        if not REQUESTS_AVAILABLE:
            return False
        try:
            r = requests.get(f'{self.ollama_url}/api/tags', timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def _find_vision_model(self) -> Optional[str]:
        """Find best available vision model."""
        if not self.ollama_ok:
            return None
        try:
            r = requests.get(f'{self.ollama_url}/api/tags', timeout=2)
            models = [m['name'] for m in r.json().get('models', [])]

            # Priority: qwen2.5vl > llama3.2-vision > llava > moondream
            priority = ['qwen2.5vl', 'qwen2-vl', 'llama3.2-vision', 'llava', 'bakllava', 'moondream']
            for candidate in priority:
                for m in models:
                    if candidate in m.lower():
                        return m
            return None
        except Exception:
            return None

    def _find_text_model(self) -> Optional[str]:
        """Find text model (for future use, not used in fallback anymore)."""
        if not self.ollama_ok:
            return None
        try:
            r = requests.get(f'{self.ollama_url}/api/tags', timeout=2)
            models = [m['name'] for m in r.json().get('models', [])]

            for candidate in ['llama3.2:1b', 'llama3.2:3b', 'llama3.2', 'qwen2', 'mistral']:
                for m in models:
                    if candidate in m.lower() and 'vision' not in m.lower() and 'vl' not in m.lower():
                        return m
            for m in models:
                if 'vision' not in m.lower() and 'vl' not in m.lower():
                    return m
            return None
        except Exception:
            return None

    def process_image(self, image_path: str, use_vision: bool = True, skip_cache: bool = False) -> Dict[str, Any]:
        """
        Process image with best available method.

        Args:
            image_path: Path to image file
            use_vision: Try Qwen2.5-VL first (default True)
            skip_cache: Skip cache lookup (default False)

        Returns:
            {
                'text': str,              # Extracted/structured text
                'raw_text': str,          # Raw OCR text
                'confidence': float,      # 0.0-1.0 (see _calculate_confidence docstring)
                'source': str,            # 'qwen-vision' | 'tesseract'
                'processing_time_ms': int,
                'has_tables': bool,
                'description': str,       # Image description (vision only)
                'vision_model': str,      # Model used (vision only)
                'cached': bool            # Whether result was from cache
            }
        """
        request_id = uuid.uuid4().hex[:8]
        start_time = time.time()

        logger.info(f"[{request_id}] START file={os.path.basename(image_path)}")

        path = Path(image_path)
        if not path.exists():
            logger.error(f"[{request_id}] File not found: {image_path}")
            return self._empty_result(error=f'File not found: {image_path}')

        # Check rate limit
        if not self.rate_limiter.is_allowed():
            wait_time = self.rate_limiter.get_wait_time()
            logger.warning(f"[{request_id}] Rate limited, wait {wait_time:.1f}s")
            return self._empty_result(error=f'Rate limit exceeded. Try again in {wait_time:.0f}s')

        # Check cache first
        if not skip_cache:
            cached = self.cache.get(image_path)
            if cached:
                elapsed = int((time.time() - start_time) * 1000)
                logger.info(f"[{request_id}] CACHE HIT ({elapsed}ms)")
                cached['processing_time_ms'] = elapsed
                return cached

        # Set processing flag
        self._set_processing(True)

        try:
            # Strategy 1: Qwen2.5-VL (primary)
            if use_vision and self.vision_model:
                logger.info(f"[{request_id}] Trying Vision ({self.vision_model})...")
                result = self._process_with_vision(image_path, request_id)

                if result and result.get('confidence', 0) > 0.5:
                    result['processing_time_ms'] = int((time.time() - start_time) * 1000)
                    self.cache.set(image_path, result)
                    logger.info(
                        f"[{request_id}] SUCCESS source={result['source']} "
                        f"conf={result['confidence']:.2f} time={result['processing_time_ms']}ms"
                    )
                    return result

                logger.info(f"[{request_id}] Vision low confidence, trying Tesseract...")

            # Strategy 2: Tesseract (fallback) - NO Ollama structuring!
            if self.tesseract_ok:
                logger.info(f"[{request_id}] Using Tesseract fallback...")
                result = self._process_with_tesseract(image_path, request_id)
                result['processing_time_ms'] = int((time.time() - start_time) * 1000)
                self.cache.set(image_path, result)
                logger.info(
                    f"[{request_id}] FALLBACK SUCCESS "
                    f"conf={result['confidence']:.2f} time={result['processing_time_ms']}ms"
                )
                return result

            logger.error(f"[{request_id}] No OCR method available")
            return self._empty_result(error='No OCR method available')

        finally:
            self._set_processing(False)

    def _process_with_vision(self, image_path: str, request_id: str = "") -> Optional[Dict[str, Any]]:
        """
        Process image with Qwen2.5-VL vision model.

        Has 30s timeout and full error handling.
        Returns None on failure (triggers Tesseract fallback).
        """
        try:
            # Read and encode image
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # Vision prompt - extract text AND describe
            prompt = """Analyze this image:

1. **OCR**: Extract ALL visible text exactly as it appears
2. **Format**: Structure as clean markdown (tables → markdown tables)
3. **Describe**: What type of image is this? (screenshot, document, diagram, photo, etc.)

Output format:
## Text
[extracted text in markdown]

## Type
[1 sentence description of what this image shows]"""

            response = requests.post(
                f'{self.ollama_url}/api/generate',
                json={
                    'model': self.vision_model,
                    'prompt': prompt,
                    'images': [image_data],
                    'stream': False,
                    'options': {
                        'temperature': 0.1,
                        'num_predict': 4096
                    }
                },
                timeout=self.VISION_TIMEOUT
            )

            if response.status_code != 200:
                logger.warning(f"[{request_id}] Vision API error: {response.status_code}")
                return None

            result_text = response.json().get('response', '')

            if not result_text.strip():
                logger.warning(f"[{request_id}] Vision returned empty response")
                return None

            # Parse response
            text = result_text
            description = ''

            # Try to extract sections
            if '## Type' in result_text:
                parts = result_text.split('## Type')
                text = parts[0].replace('## Text', '').strip()
                description = parts[1].strip() if len(parts) > 1 else ''
            elif '## text' in result_text.lower():
                parts = re.split(r'##\s*type', result_text, flags=re.IGNORECASE)
                text = re.sub(r'##\s*text', '', parts[0], flags=re.IGNORECASE).strip()
                description = parts[1].strip() if len(parts) > 1 else ''

            # Detect tables in output
            has_tables = bool(re.search(r'\|.*\|.*\n\|[-:| ]+\|', text))

            # Calculate confidence
            confidence = self._calculate_confidence(text, description, 'qwen-vision', has_tables)

            return {
                'text': text.strip(),
                'raw_text': text.strip(),
                'confidence': confidence,
                'source': 'qwen-vision',
                'has_tables': has_tables,
                'description': description.strip(),
                'vision_model': self.vision_model
            }

        except requests.exceptions.Timeout:
            logger.warning(f"[{request_id}] Vision timeout after {self.VISION_TIMEOUT}s")
            return None
        except requests.exceptions.ConnectionError:
            logger.warning(f"[{request_id}] Vision connection error - Ollama may be down")
            return None
        except Exception as e:
            logger.warning(f"[{request_id}] Vision error: {e}")
            return None

    def _process_with_tesseract(self, image_path: str, request_id: str = "") -> Dict[str, Any]:
        """
        Process image with Tesseract only.

        v2.1: Removed Ollama structuring for faster fallback.
        If Vision (6s) failed, user wants FAST fallback, not another 3s wait.
        """
        try:
            image = Image.open(image_path)

            # Convert to RGB if needed
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                if image.mode in ('RGBA', 'LA'):
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')

            # OCR with Tesseract
            raw_text = pytesseract.image_to_string(image, config=self.TESSERACT_CONFIG)

            # Get Tesseract confidence
            try:
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                confidences = [int(c) for c in data['conf'] if str(c).lstrip('-').isdigit() and int(c) > 0]
                tesseract_conf = sum(confidences) / len(confidences) / 100 if confidences else 0.5
            except Exception:
                tesseract_conf = 0.5

            # Calculate final confidence
            confidence = self._calculate_confidence(raw_text, '', 'tesseract', False, tesseract_conf)

            return {
                'text': raw_text.strip(),
                'raw_text': raw_text.strip(),
                'confidence': confidence,
                'source': 'tesseract',
                'has_tables': False,  # Tesseract doesn't detect tables
                'description': '',
                'vision_model': None
            }

        except Exception as e:
            logger.error(f"[{request_id}] Tesseract error: {e}")
            return self._empty_result(error=str(e), source='tesseract-error')

    def _calculate_confidence(
        self,
        text: str,
        description: str,
        source: str,
        has_tables: bool = False,
        tesseract_conf: float = 0.5
    ) -> float:
        """
        Calculate OCR confidence score.

        For Vision (Qwen):
          - Base: 0.70 (model is generally reliable)
          - +0.10 if text length > 50 chars
          - +0.05 if text length > 200 chars
          - +0.10 if description > 10 chars
          - +0.05 if structured formatting detected (|, #, -, *)
          - Max: 0.99

        For Tesseract:
          - Use Tesseract's native word confidence (0-1 scale)
          - Apply text length bonus:
            - +0.10 if > 50 chars
            - +0.05 if > 200 chars
          - Max: 0.95 (lower than vision since no understanding)

        Returns:
            float: Confidence score 0.0-1.0
        """
        if not text:
            return 0.0

        if source == 'qwen-vision':
            score = 0.70  # Base score for vision

            # Text length bonus
            if len(text) > 50:
                score += 0.10
            if len(text) > 200:
                score += 0.05

            # Description bonus
            if description and len(description) > 10:
                score += 0.10

            # Structure bonus
            if any(c in text for c in ['|', '#', '-', '*']):
                score += 0.05

            # Tables bonus
            if has_tables:
                score += 0.05

            return min(0.99, round(score, 2))

        elif source == 'tesseract':
            # Start with Tesseract's own confidence
            score = tesseract_conf

            # Text length bonus
            if len(text) > 50:
                score += 0.10
            if len(text) > 200:
                score += 0.05

            return min(0.95, round(score, 2))

        return 0.50  # Unknown source

    def _empty_result(self, error: str = '', source: str = 'none') -> Dict[str, Any]:
        """Return empty result with error."""
        return {
            'text': '',
            'raw_text': '',
            'confidence': 0,
            'source': source,
            'has_tables': False,
            'description': '',
            'vision_model': None,
            'processing_time_ms': 0,
            'error': error
        }

    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process PDF - try direct extraction first, then OCR page by page.

        v2.1: Page-by-page processing to avoid memory issues.
        """
        request_id = uuid.uuid4().hex[:8]
        start_time = time.time()

        logger.info(f"[{request_id}] PDF START file={os.path.basename(pdf_path)}")

        path = Path(pdf_path)
        if not path.exists():
            return self._empty_result(error=f'File not found: {pdf_path}')

        # Check rate limit
        if not self.rate_limiter.is_allowed():
            wait_time = self.rate_limiter.get_wait_time()
            return self._empty_result(error=f'Rate limit exceeded. Try again in {wait_time:.0f}s')

        # Check cache
        cached = self.cache.get(pdf_path)
        if cached:
            elapsed = int((time.time() - start_time) * 1000)
            logger.info(f"[{request_id}] PDF CACHE HIT ({elapsed}ms)")
            cached['processing_time_ms'] = elapsed
            return cached

        self._set_processing(True)

        try:
            # Try direct text extraction first (for text-based PDFs)
            direct_result = self._extract_pdf_direct(pdf_path, request_id)

            if direct_result and direct_result.get('confidence', 0) >= 0.9:
                direct_result['processing_time_ms'] = int((time.time() - start_time) * 1000)
                self.cache.set(pdf_path, direct_result)
                logger.info(f"[{request_id}] PDF direct extraction success")
                return direct_result

            # Fall back to OCR (for scanned PDFs) - page by page
            ocr_result = self._extract_pdf_ocr(pdf_path, request_id)
            ocr_result['processing_time_ms'] = int((time.time() - start_time) * 1000)
            self.cache.set(pdf_path, ocr_result)
            return ocr_result

        finally:
            self._set_processing(False)

    def _extract_pdf_direct(self, pdf_path: str, request_id: str = "") -> Optional[Dict[str, Any]]:
        """Direct text extraction from PDF using PyMuPDF."""
        try:
            import fitz
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            logger.info(f"[{request_id}] PDF direct: {total_pages} pages")

            all_text = []
            for i in range(total_pages):
                page = doc.load_page(i)
                text = page.get_text().strip()
                if text:
                    all_text.append(f"## Page {i + 1}\n\n{text}")
                # Free memory
                del page

            doc.close()

            if not all_text:
                return None

            combined = '\n\n---\n\n'.join(all_text)

            # Check if meaningful text
            if len(combined.split()) < 10:
                return None

            return {
                'text': combined,
                'raw_text': combined,
                'confidence': 1.0,
                'source': 'pdf-direct',
                'pages': len(all_text),
                'has_tables': False,
                'description': f'PDF document with {len(all_text)} pages',
                'vision_model': None
            }

        except Exception as e:
            logger.warning(f"[{request_id}] PDF direct extraction failed: {e}")
            return None

    def _extract_pdf_ocr(self, pdf_path: str, request_id: str = "") -> Dict[str, Any]:
        """
        OCR-based PDF extraction for scanned documents.

        v2.1: Process page by page to avoid memory issues.
        """
        try:
            import fitz
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
        except Exception as e:
            return self._empty_result(error=f'PDF open failed: {e}', source='pdf-error')

        logger.info(f"[{request_id}] PDF OCR: {total_pages} pages")

        all_text = []
        confidences = []
        descriptions = []
        has_tables = False

        import tempfile

        for i in range(total_pages):
            try:
                # Load single page
                page = doc.load_page(i)

                # Convert to image (2x scale for better OCR)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

                # Save to temp file
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    pix.save(tmp.name)
                    temp_path = tmp.name

                # Process this page (skip cache for individual pages)
                result = self.process_image(temp_path, skip_cache=True)

                # Clean up
                os.unlink(temp_path)
                del pix
                del page

                if result.get('text'):
                    all_text.append(f"## Page {i + 1}\n\n{result['text']}")
                if result.get('confidence'):
                    confidences.append(result['confidence'])
                if result.get('description'):
                    descriptions.append(result['description'])
                if result.get('has_tables'):
                    has_tables = True

                logger.info(f"[{request_id}] PDF page {i + 1}/{total_pages} done")

            except Exception as e:
                logger.warning(f"[{request_id}] PDF page {i + 1} error: {e}")
                continue

        doc.close()

        avg_conf = sum(confidences) / len(confidences) if confidences else 0

        return {
            'text': '\n\n---\n\n'.join(all_text),
            'raw_text': '\n\n'.join(all_text),
            'confidence': round(avg_conf, 2),
            'source': 'pdf-ocr',
            'pages': total_pages,
            'has_tables': has_tables,
            'description': descriptions[0] if descriptions else '',
            'vision_model': self.vision_model
        }

    def get_status(self) -> Dict[str, Any]:
        """Return processor status."""
        strategy = 'none'
        if self.vision_model:
            strategy = 'qwen-vision'
        elif self.tesseract_ok:
            strategy = 'tesseract'

        return {
            'ready': self.vision_model is not None or self.tesseract_ok,
            'tesseract': self.tesseract_ok,
            'ollama': self.ollama_ok,
            'vision_model': self.vision_model,
            'text_model': self.text_model,
            'strategy': strategy,
            'is_processing': self.is_processing,
            'supported_formats': list(self.SUPPORTED_IMAGES | self.SUPPORTED_DOCS),
            'timeouts': {
                'vision': self.VISION_TIMEOUT,
                'tesseract': self.TESSERACT_TIMEOUT
            },
            'rate_limit': {
                'max_calls': self.rate_limiter.max_calls,
                'period': self.rate_limiter.period
            }
        }

    def clear_cache(self) -> int:
        """Clear OCR cache. Returns count of deleted entries."""
        count = self.cache.clear()
        logger.info(f"Cache cleared: {count} entries")
        return count


# Singleton
_processor = None
_processor_lock = threading.Lock()


def get_ocr_processor() -> OCRProcessor:
    """Get or create singleton OCRProcessor instance."""
    global _processor
    with _processor_lock:
        if _processor is None:
            _processor = OCRProcessor()
        return _processor


def reset_ocr_processor() -> Dict[str, Any]:
    """
    Reset singleton (useful after installing new models).

    Returns:
        {'success': bool, 'message': str, 'error': str (optional)}
    """
    global _processor
    with _processor_lock:
        if _processor is not None and _processor.is_processing:
            return {
                'success': False,
                'error': 'OCR is currently processing. Try again later.'
            }

        _processor = None

    # Create new instance
    new_processor = get_ocr_processor()

    return {
        'success': True,
        'message': 'OCR processor reset',
        'vision_model': new_processor.vision_model,
        'strategy': new_processor.get_status()['strategy']
    }
