"""
VETKA Embedding Pipeline - generates embeddings and saves to Qdrant.

@status: active
@phase: 98
@depends: ollama, qdrant_client, src.utils.embedding_service, src.ocr.ocr_processor,
          src.orchestration.triple_write_manager, src.agents.hope_enhancer
@used_by: src.scanners.qdrant_updater, src.api.routes.tree_routes

FIX_98.3: Added HOPE (Hierarchical Optimized Processing) integration.
New use_hope option enables matryoshka-style multi-level embedding context.

Uses Ollama embeddinggemma:300m model for vector generation.
Features:
- Parallel processing with ThreadPoolExecutor (4-5x speedup)
- Smart scan: skip unchanged files based on modified_time
- OCR integration for images/PDFs
- TripleWrite integration for coherent storage (Qdrant + Weaviate + Changelog)
"""

import time
import hashlib
import uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("⚠️  ollama not installed. Install with: pip install ollama")


@dataclass
class EmbeddingResult:
    """Result of embedding a single document."""
    doc_id: str
    path: str
    name: str
    embedding: List[float]
    metadata: Dict[str, Any]
    success: bool
    error: Optional[str] = None


class EmbeddingPipeline:
    """
    Pipeline to generate embeddings and save to Qdrant.

    Uses existing Ollama embeddinggemma:300m model.
    Saves to existing Qdrant vetka_elisya collection.
    """

    EMBEDDING_MODEL = "embeddinggemma:300m"
    EMBEDDING_DIM = 768  # embeddinggemma output dimension
    BATCH_SIZE = 10
    MAX_CONTENT_LENGTH = 8000  # Characters to embed
    MAX_WORKERS = 8  # Concurrent workers for parallel embedding

    def __init__(
        self,
        qdrant_client=None,
        collection_name: str = "vetka_elisya",
        max_workers: int = 8,
        use_hope: bool = False  # FIX_98.3: Enable HOPE matryoshka context
    ):
        """
        Args:
            qdrant_client: Qdrant client instance (from MemoryManager.qdrant)
            collection_name: Qdrant collection to save embeddings
            max_workers: Number of concurrent workers for parallel embedding (default: 8)
            use_hope: Enable HOPE (Hierarchical Optimized Processing) for embedding context
        """
        self.qdrant = qdrant_client
        self.collection_name = collection_name
        self.processed_count = 0
        self.error_count = 0
        self.total_time = 0
        self.max_workers = max_workers
        self.use_hope = use_hope  # FIX_98.3
        self._lock = threading.Lock()  # For thread-safe counter updates
        self._hope_enhancer = None  # Lazy-loaded

    def get_existing_files(self) -> Dict[str, float]:
        """
        Get existing files from Qdrant with their modified_time.
        Returns dict: {path: modified_time}
        """
        existing = {}
        if not self.qdrant:
            return existing

        try:
            result = self.qdrant.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=False
            )
            points = result[0] if result else []

            for point in points:
                payload = point.payload or {}
                path = payload.get('path', '')
                modified = payload.get('modified_time', 0)
                if path:
                    existing[path] = modified

            print(f"[SmartScan] Found {len(existing)} existing files in Qdrant")
        except Exception as e:
            print(f"[SmartScan] Could not load existing files: {e}")

        return existing

    def filter_new_or_modified(
        self,
        files: List[Dict[str, Any]],
        existing: Dict[str, float]
    ) -> tuple:
        """
        Filter files to only include new or modified ones.
        Returns (files_to_process, skipped_count)
        """
        to_process = []
        skipped = 0

        for file_data in files:
            path = file_data.get('path', '')
            modified = file_data.get('modified_time', 0)

            if path in existing:
                # File exists - check if modified
                if abs(existing[path] - modified) < 1:  # Within 1 second tolerance
                    skipped += 1
                    continue  # Skip - unchanged

            to_process.append(file_data)

        print(f"[SmartScan] {len(to_process)} new/modified, {skipped} unchanged (skipped)")
        return to_process, skipped

    def process_files(
        self,
        files: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        smart_scan: bool = True,
        parallel: bool = True
    ) -> List[EmbeddingResult]:
        """
        Process list of scanned files: generate embeddings and save to Qdrant.

        Now supports parallel processing with ThreadPoolExecutor for 4-5x speedup.

        Args:
            files: List of file dicts from LocalScanner
            progress_callback: Optional callback(current, total, filename)
            smart_scan: If True, skip files already in Qdrant with same modified_time
            parallel: If True, use concurrent workers for 4-5x faster processing

        Returns:
            List of EmbeddingResult objects
        """
        if not OLLAMA_AVAILABLE:
            raise RuntimeError("Ollama not available. Install with: pip install ollama")

        # Smart scan: filter out unchanged files
        self.skipped_count = 0
        if smart_scan:
            existing = self.get_existing_files()
            files, self.skipped_count = self.filter_new_or_modified(files, existing)

        results = []
        total = len(files)

        if total == 0:
            print("[SmartScan] No new files to process!")
            return results

        if parallel:
            results = self._process_files_parallel(files, progress_callback, total)
        else:
            results = self._process_files_sequential(files, progress_callback, total)

        return results

    def _process_files_sequential(
        self,
        files: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, int, str], None]],
        total: int
    ) -> List[EmbeddingResult]:
        """Original sequential processing (slower)."""
        results = []
        for idx, file_data in enumerate(files):
            try:
                start_time = time.time()
                result = self._process_single(file_data)
                results.append(result)

                if result.success:
                    with self._lock:
                        self.processed_count += 1
                else:
                    with self._lock:
                        self.error_count += 1

                self.total_time += time.time() - start_time

                if progress_callback:
                    progress_callback(idx + 1, total, file_data.get('name', 'unknown'))

            except Exception as e:
                with self._lock:
                    self.error_count += 1
                results.append(EmbeddingResult(
                    doc_id=self._generate_id(file_data),
                    path=file_data.get('path', ''),
                    name=file_data.get('name', ''),
                    embedding=[],
                    metadata={},
                    success=False,
                    error=str(e)
                ))

        return results

    def _process_files_parallel(
        self,
        files: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, int, str], None]],
        total: int
    ) -> List[EmbeddingResult]:
        """Parallel processing with ThreadPoolExecutor (4-5x faster)."""
        results = []
        processed_count = [0]  # Use list to track in callback

        def worker_process(idx: int, file_data: Dict[str, Any]) -> tuple:
            """Worker thread: process one file and return (idx, result)."""
            try:
                start_time = time.time()
                result = self._process_single(file_data)

                if result.success:
                    with self._lock:
                        self.processed_count += 1
                else:
                    with self._lock:
                        self.error_count += 1

                self.total_time += time.time() - start_time
                return (idx, result)

            except Exception as e:
                with self._lock:
                    self.error_count += 1
                return (idx, EmbeddingResult(
                    doc_id=self._generate_id(file_data),
                    path=file_data.get('path', ''),
                    name=file_data.get('name', ''),
                    embedding=[],
                    metadata={},
                    success=False,
                    error=str(e)
                ))

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(worker_process, idx, file_data): (idx, file_data)
                for idx, file_data in enumerate(files)
            }

            # Collect results as they complete (maintains order)
            result_dict = {}
            for future in as_completed(futures):
                idx, result = future.result()
                result_dict[idx] = result

                # Progress callback
                processed_count[0] += 1
                if progress_callback:
                    progress_callback(
                        processed_count[0],
                        total,
                        files[idx].get('name', 'unknown')
                    )

            # Rebuild results in original order
            for i in range(total):
                results.append(result_dict[i])

        return results

    def _process_single(self, file_data: Dict[str, Any]) -> EmbeddingResult:
        """Process a single file: generate embedding and save to Qdrant."""

        doc_id = self._generate_id(file_data)
        path = file_data.get('path', '')
        name = file_data.get('name', '')
        content = file_data.get('content', '')
        extension = file_data.get('extension', '').lower()

        # === OCR FOR IMAGES/PDFs ===
        ocr_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp', '.pdf'}
        ocr_metadata = {}

        if extension in ocr_extensions:
            try:
                from src.ocr.ocr_processor import get_ocr_processor
                ocr = get_ocr_processor()

                if extension == '.pdf':
                    ocr_result = ocr.process_pdf(path)
                else:
                    ocr_result = ocr.process_image(path)

                if ocr_result.get('text') and not ocr_result.get('error'):
                    # Use OCR text instead of empty/binary content
                    content = ocr_result['text']
                    ocr_metadata = {
                        'ocr_source': ocr_result.get('source', 'unknown'),
                        'ocr_confidence': ocr_result.get('confidence', 0),
                        'ocr_pages': ocr_result.get('pages', 1),
                        'has_tables': len(ocr_result.get('tables', [])) > 0,
                        'has_formulas': len(ocr_result.get('formulas', [])) > 0,
                        # Vision model extras
                        'image_description': ocr_result.get('description', ''),
                        'processing_time_ms': ocr_result.get('processing_time_ms', 0),
                        'vision_model': ocr_result.get('vision_model', '')
                    }
                    print(f"[OCR] {name}: {len(content)} chars, source={ocr_metadata['ocr_source']}, {ocr_metadata['processing_time_ms']}ms")
                elif ocr_result.get('error'):
                    print(f"[OCR] {name}: error - {ocr_result['error']}")
            except Exception as ocr_error:
                print(f"[OCR] {name}: exception - {ocr_error}")
        # === END OCR ===

        # Truncate content for embedding
        embed_text = self._prepare_text(name, content)

        # Generate embedding via Ollama
        embedding = self._get_embedding(embed_text)

        if not embedding:
            return EmbeddingResult(
                doc_id=doc_id,
                path=path,
                name=name,
                embedding=[],
                metadata={},
                success=False,
                error="Failed to generate embedding"
            )

        # Prepare metadata for Qdrant
        metadata = {
            'type': 'scanned_file',
            'source': 'local_scanner',
            'path': path,
            'name': name,
            'extension': file_data.get('extension', ''),
            'size_bytes': file_data.get('size_bytes', 0),
            'created_time': file_data.get('created_time', 0),  # Original file creation date
            'modified_time': file_data.get('modified_time', 0),
            'content_hash': file_data.get('content_hash', ''),
            'parent_folder': file_data.get('parent_folder', ''),
            'depth': file_data.get('depth', 0),
            'content': content[:500],  # Store preview only
            'timestamp': time.time()
        }

        # Save to Qdrant (legacy - vetka_elisya collection)
        success = self._save_to_qdrant(doc_id, embedding, metadata)

        # === TRIPLE WRITE INTEGRATION ===
        # Also write to Weaviate + vetka_files + ChangeLog for unified storage
        try:
            from src.orchestration.triple_write_manager import get_triple_write_manager
            tw = get_triple_write_manager()

            # Combine base metadata with OCR metadata
            tw_metadata = {
                'size': file_data.get('size_bytes', 0),
                'mtime': file_data.get('modified_time', 0),
                'extension': file_data.get('extension', ''),
                'depth': file_data.get('depth', 0),
                **ocr_metadata  # Include OCR metadata if present
            }

            tw_results = tw.write_file(
                file_path=path,
                content=content,
                embedding=embedding,
                metadata=tw_metadata
            )
            # Log Triple Write results (non-blocking)
            tw_success = sum(tw_results.values())
            if tw_success < 3:
                print(f"[TripleWrite] {name}: W={tw_results['weaviate']} Q={tw_results['qdrant']} C={tw_results['changelog']}")
        except Exception as tw_error:
            # Triple Write errors should not break the main scan
            print(f"[TripleWrite] Error for {name}: {tw_error}")
        # === END TRIPLE WRITE ===

        return EmbeddingResult(
            doc_id=doc_id,
            path=path,
            name=name,
            embedding=embedding,
            metadata=metadata,
            success=success,
            error=None if success else "Failed to save to Qdrant"
        )

    def _prepare_text(self, name: str, content: str) -> str:
        """
        Prepare text for embedding (title + content).

        FIX_98.3: Optionally uses HOPE for matryoshka-style context.
        HOPE provides multi-level context (LOW/MID/HIGH) for richer embeddings.
        """
        # FIX_98.3: Use HOPE if enabled
        if self.use_hope and len(content) > 500:
            try:
                hope_context = self._get_hope_context(content)
                if hope_context:
                    # Use summary (LOW layer) for embedding - more semantic
                    summary = hope_context.get('summary', '')
                    if summary and len(summary) > 100:
                        text = f"File: {name}\n\n{summary}"
                        # Add detailed hint if space permits
                        detailed = hope_context.get('detailed', '')
                        if detailed and len(text) + len(detailed) < self.MAX_CONTENT_LENGTH:
                            text += f"\n\n{detailed[:500]}"
                        return text
            except Exception as e:
                # Fallback to raw content on HOPE failure
                pass

        # Default: combine name and content
        text = f"File: {name}\n\n{content}"

        # Truncate if too long
        if len(text) > self.MAX_CONTENT_LENGTH:
            text = text[:self.MAX_CONTENT_LENGTH] + "..."

        return text

    def _get_hope_context(self, content: str) -> Optional[Dict[str, str]]:
        """
        Get HOPE embedding context for content.

        FIX_98.3: Uses HOPEEnhancer.get_embedding_context() for matryoshka layers.
        """
        try:
            if self._hope_enhancer is None:
                from src.agents.hope_enhancer import HOPEEnhancer
                self._hope_enhancer = HOPEEnhancer(use_api_fallback=False)

            return self._hope_enhancer.get_embedding_context(content)
        except ImportError:
            return None
        except Exception:
            return None

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Delegate to unified EmbeddingService (Phase 36.1)"""
        from src.utils.embedding_service import get_embedding
        return get_embedding(text)

    def _save_to_qdrant(self, doc_id: str, embedding: List[float], metadata: Dict) -> bool:
        """Save embedding to Qdrant."""
        if not self.qdrant:
            print("[Embedding] No Qdrant client available")
            return False

        try:
            from qdrant_client.models import PointStruct

            # Use UUID5 for collision-free point IDs (Phase 19 fix)
            # UUID5 is deterministic: same doc_id always produces same ID
            point_id = uuid.uuid5(uuid.NAMESPACE_DNS, doc_id).int & 0x7FFFFFFFFFFFFFFF

            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=metadata
            )

            # Phase 92: Non-blocking upsert (Kimi K2 fix)
            # wait=False allows FastAPI to respond while Qdrant writes to disk
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=[point],
                wait=False  # Non-blocking - UI won't freeze
            )

            return True

        except Exception as e:
            print(f"[Embedding] Qdrant save error: {e}")
            return False

    def _generate_id(self, file_data: Dict[str, Any]) -> str:
        """Generate unique ID for a file."""
        path = file_data.get('path', '')
        content_hash = file_data.get('content_hash', '')
        return hashlib.md5(f"{path}:{content_hash}".encode()).hexdigest()

    def get_stats(self) -> Dict[str, Any]:
        """Return pipeline statistics."""
        avg_time = self.total_time / max(self.processed_count, 1)
        return {
            'processed_count': self.processed_count,
            'skipped_count': getattr(self, 'skipped_count', 0),
            'error_count': self.error_count,
            'total_time_sec': round(self.total_time, 2),
            'avg_time_per_file_sec': round(avg_time, 3),
            'collection': self.collection_name,
            'model': self.EMBEDDING_MODEL
        }


def run_embedding_pipeline(
    files: List[Dict[str, Any]],
    qdrant_client=None,
    collection_name: str = "vetka_elisya",
    progress_callback: Optional[Callable] = None,
    use_hope: bool = False  # FIX_98.3: Enable HOPE matryoshka context
) -> Dict[str, Any]:
    """
    Convenience function to run the embedding pipeline.

    Args:
        files: List of file dicts from LocalScanner
        qdrant_client: Qdrant client instance
        collection_name: Target collection
        progress_callback: Optional progress callback
        use_hope: Enable HOPE for matryoshka-style embedding context (FIX_98.3)

    Returns:
        Dict with stats and results summary
    """
    pipeline = EmbeddingPipeline(
        qdrant_client=qdrant_client,
        collection_name=collection_name,
        use_hope=use_hope  # FIX_98.3
    )

    results = pipeline.process_files(files, progress_callback)
    stats = pipeline.get_stats()

    success_count = sum(1 for r in results if r.success)

    return {
        'stats': stats,
        'success_count': success_count,
        'total_files': len(files),
        'success_rate': round(success_count / max(len(files), 1) * 100, 1)
    }
