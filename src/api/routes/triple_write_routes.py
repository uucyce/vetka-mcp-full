"""
VETKA Triple Write Routes - FastAPI Version

@file triple_write_routes.py
@status ACTIVE
@phase Phase 39.6
@lastAudit 2026-01-05

Triple Write (Qdrant + Weaviate + ChangeLog) storage management API routes.
Migrated from src/server/routes/triple_write_routes.py (Flask Blueprint)

Endpoints:
- GET /api/triple-write/stats - Get Triple Write storage statistics
- GET /api/triple-write/check-coherence - Check data coherence across stores (FIX_95.9)
- POST /api/triple-write/cleanup - Clean up evaluation data from VetkaLeaf
- POST /api/triple-write/reindex - Re-index files using Triple Write

Changes from Flask version:
- Blueprint -> APIRouter
- request.get_json() -> Pydantic BaseModel
- return jsonify({}) -> return {}
- def -> async def
"""

import os
import mimetypes
import hashlib
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.scanners.mime_policy import validate_ingest_target


router = APIRouter(prefix="/api/triple-write", tags=["triple_write"])

# Get project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ============================================================
# PYDANTIC MODELS
# ============================================================

class ReindexRequest(BaseModel):
    """Request to reindex files."""
    path: Optional[str] = "src"
    limit: Optional[int] = 500
    multimodal: Optional[bool] = False


# ============================================================
# ROUTES
# ============================================================

@router.get("/stats")
async def triple_write_stats():
    """
    Get Triple Write storage statistics.

    Returns status of Qdrant, Weaviate, and ChangeLog stores.
    """
    try:
        from src.orchestration.triple_write_manager import get_triple_write_manager
        tw = get_triple_write_manager()
        stats = tw.get_stats()

        return {
            'success': True,
            'stats': stats,
            'healthy': all(s.get('status') == 'ready' for s in stats.values())
        }
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail={'error': str(e), 'traceback': traceback.format_exc()})


@router.get("/check-coherence")
async def check_coherence(depth: str = "basic"):
    """
    FIX_95.9: MARKER_COHERENCE_001 - Check data coherence across all stores.

    Compares counts and samples between Qdrant, Weaviate, and ChangeLog
    to detect inconsistencies. Based on Grok's cache coherence analysis.

    Args:
        depth: "basic" for counts only, "full" for sample comparison

    Returns:
        coherent: True if all stores are in sync
        stats: Per-store counts
        mismatches: List of detected inconsistencies
    """
    try:
        from src.orchestration.triple_write_manager import get_triple_write_manager
        tw = get_triple_write_manager()

        # Get counts from each store
        stats = tw.get_stats()

        mismatches = []

        # Compare Qdrant vs Weaviate counts
        qdrant_count = stats.get('qdrant', {}).get('count', 0)
        weaviate_count = stats.get('weaviate', {}).get('count', 0)
        changelog_count = stats.get('changelog', {}).get('count', 0)

        if abs(qdrant_count - weaviate_count) > 10:  # Allow small variance
            mismatches.append({
                'type': 'count_mismatch',
                'stores': ['qdrant', 'weaviate'],
                'qdrant': qdrant_count,
                'weaviate': weaviate_count,
                'diff': abs(qdrant_count - weaviate_count)
            })

        # Check changelog coverage
        min_count = min(qdrant_count, weaviate_count) if qdrant_count and weaviate_count else max(qdrant_count, weaviate_count)
        if min_count > 0 and changelog_count < min_count * 0.9:
            mismatches.append({
                'type': 'changelog_behind',
                'changelog': changelog_count,
                'expected': min_count,
                'coverage': f"{(changelog_count / max(1, min_count)) * 100:.1f}%"
            })

        # Deep check: sample comparison (if depth=full)
        sample_mismatches = []
        if depth == "full" and tw.qdrant_client and tw.weaviate_client:
            try:
                # Get 5 random samples from Qdrant
                from qdrant_client.models import ScrollRequest
                scroll_result = tw.qdrant_client.scroll(
                    collection_name='vetka_files',
                    limit=5,
                    with_payload=True,
                    with_vectors=False
                )
                samples = scroll_result[0] if scroll_result else []

                for point in samples:
                    file_path = point.payload.get('file_path', '')
                    if not file_path:
                        continue

                    # Check if exists in Weaviate
                    try:
                        import uuid
                        file_id = str(uuid.uuid5(uuid.NAMESPACE_URL, file_path))
                        w_obj = tw.weaviate_client.data_object.get_by_id(file_id, class_name='VetkaLeaf')
                        if not w_obj:
                            sample_mismatches.append({
                                'file_path': file_path,
                                'issue': 'missing_in_weaviate'
                            })
                    except Exception:
                        sample_mismatches.append({
                            'file_path': file_path,
                            'issue': 'weaviate_lookup_failed'
                        })

                if sample_mismatches:
                    mismatches.append({
                        'type': 'sample_mismatch',
                        'samples_checked': len(samples),
                        'issues': sample_mismatches[:5]  # Limit output
                    })
            except Exception as e:
                mismatches.append({
                    'type': 'sample_check_error',
                    'error': str(e)
                })

        return {
            'coherent': len(mismatches) == 0,
            'depth': depth,
            'stats': {
                'qdrant': qdrant_count,
                'weaviate': weaviate_count,
                'changelog': changelog_count
            },
            'mismatches': mismatches,
            'recommendation': 'Run /api/triple-write/reindex to fix' if mismatches else 'All stores coherent'
        }

    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail={'error': str(e), 'traceback': traceback.format_exc()})


@router.post("/cleanup")
async def triple_write_cleanup():
    """
    Clean up wrong evaluation data from VetkaLeaf.

    Removes orphaned or incorrect evaluation entries.
    """
    try:
        from src.orchestration.triple_write_manager import get_triple_write_manager
        tw = get_triple_write_manager()
        deleted = tw.clear_weaviate_eval_data()

        return {
            'success': True,
            'deleted': deleted,
            'message': f'Removed {deleted} evaluation objects from VetkaLeaf'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reindex")
async def triple_write_reindex(req: ReindexRequest):
    """
    Re-index files using Triple Write.

    Walks directory and indexes text files to Qdrant, Weaviate, and ChangeLog.
    """
    try:
        from src.orchestration.triple_write_manager import get_triple_write_manager

        tw = get_triple_write_manager()

        # Walk directory and index files
        indexed = 0
        errors = 0
        skipped = 0

        target_dir = os.path.join(PROJECT_ROOT, req.path)

        TEXT_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.md', '.txt', '.json',
                          '.yaml', '.yml', '.html', '.css', '.sh', '.sql', '.go', '.rs'}
        OCR_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff'}
        MEDIA_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg',
                            '.mp4', '.mov', '.mkv', '.avi', '.webm'}

        for root, dirs, files in os.walk(target_dir):
            # Skip hidden and common ignore
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in
                      ['node_modules', '__pycache__', 'venv', '.git', 'dist', 'build']]

            for fname in files:
                if indexed >= req.limit:
                    break

                if fname.startswith('.'):
                    skipped += 1
                    continue

                # Extension gate
                ext = os.path.splitext(fname)[1].lower()
                size_bytes = os.path.getsize(fpath)
                policy_allowed, policy = validate_ingest_target(fpath, size_bytes)
                if not policy_allowed:
                    skipped += 1
                    continue

                allowed = ext in TEXT_EXTENSIONS or (req.multimodal and (ext in OCR_EXTENSIONS or ext in MEDIA_EXTENSIONS))
                if not allowed:
                    skipped += 1
                    continue

                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, PROJECT_ROOT)

                try:
                    media_chunks = []
                    # Read content (text / OCR / media summary)
                    if ext in TEXT_EXTENSIONS:
                        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                    elif ext in OCR_EXTENSIONS:
                        try:
                            from src.ocr.ocr_processor import get_ocr_processor
                            ocr = get_ocr_processor()
                            ocr_result = ocr.process_pdf(fpath) if ext == '.pdf' else ocr.process_image(fpath)
                            content = (ocr_result.get('text') or '').strip()
                            if not content:
                                content = f"[OCR empty] file={rel_path}"
                        except Exception as ocr_err:
                            content = f"[OCR error] file={rel_path} error={str(ocr_err)[:160]}"
                    else:
                        mime_type, _ = mimetypes.guess_type(fpath)
                        mime_type = mime_type or 'application/octet-stream'
                        size_bytes = os.path.getsize(fpath)
                        try:
                            from src.voice.stt_engine import WhisperSTT
                            stt = WhisperSTT(model_name="base")
                            tr = stt.transcribe(fpath)
                            t_text = (tr.get("text") or "").strip()
                            segments = tr.get("segments", []) or []
                            if t_text:
                                content = t_text
                                for seg in segments[:128]:
                                    media_chunks.append({
                                        "start_sec": float(seg.get("start", 0.0) or 0.0),
                                        "end_sec": float(seg.get("end", 0.0) or 0.0),
                                        "text": str(seg.get("text", "") or ""),
                                        "confidence": float(tr.get("confidence", 0.0) or 0.0),
                                    })
                            else:
                                raise ValueError("empty transcript")
                        except Exception:
                            with open(fpath, 'rb') as fb:
                                digest = hashlib.sha256(fb.read()).hexdigest()
                            content = (
                                f"[Media file summary]\n"
                                f"path={rel_path}\n"
                                f"mime={mime_type}\n"
                                f"size_bytes={size_bytes}\n"
                                f"sha256={digest}"
                            )

                    # Skip very large or empty files
                    if len(content) < 10 or len(content) > 100000:
                        skipped += 1
                        continue

                    # Get file stats
                    stat = os.stat(fpath)
                    metadata = {
                        'size': stat.st_size,
                        'mtime': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'extension': ext,
                        'mime_type': policy.get('mime_type') or mimetypes.guess_type(fpath)[0] or 'application/octet-stream',
                        'modality': policy.get('category'),
                        'ingest_mode': 'multimodal' if req.multimodal else 'text_only',
                        'media_chunks': media_chunks[:32],
                        'extraction_version': 'phase153_mm_v1',
                    }

                    # Get embedding
                    embedding = tw.get_embedding(content[:2000])

                    # Triple Write!
                    results = tw.write_file(
                        file_path=rel_path,
                        content=content,
                        embedding=embedding,
                        metadata=metadata
                    )

                    if any(results.values()):
                        indexed += 1
                    else:
                        errors += 1

                except Exception as e:
                    errors += 1
                    print(f"  [Reindex] Error {rel_path}: {e}")

            if indexed >= req.limit:
                break

        return {
            'success': True,
            'indexed': indexed,
            'errors': errors,
            'skipped': skipped,
            'path': req.path,
            'limit': req.limit
        }

    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail={'error': str(e), 'traceback': traceback.format_exc()})
