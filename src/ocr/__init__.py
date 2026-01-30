"""
VETKA OCR Module - Mac-first OCR using Tesseract + Ollama.

Phase 18: OCR Integration providing OCRProcessor for image and PDF text extraction
with Qwen2.5-VL vision model as primary and Tesseract as fallback.

@status: active
@phase: 96
@depends: src.ocr.ocr_processor
@used_by: src.api.routes, file processing pipelines
"""

from .ocr_processor import OCRProcessor, get_ocr_processor

__all__ = ['OCRProcessor', 'get_ocr_processor']
