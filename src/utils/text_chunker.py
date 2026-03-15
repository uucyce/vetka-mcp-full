"""MARKER_181.10: Text chunker for embedding-safe text splitting.

Splits text into overlapping chunks that fit within embedding model context windows.
Used by EmbeddingService.get_embedding_chunked() for full-document embeddings.

Strategy: paragraphs → sentences → words (hierarchical splitting).
Overlap between chunks preserves cross-boundary context.

@status: active
@phase: 181.10
@depends: none
@used_by: src/utils/embedding_service.py, src/scanners/qdrant_updater.py
"""

import re
from typing import List


def chunk_text(
    text: str,
    max_chars: int = 3000,
    overlap: int = 500,
) -> List[str]:
    """Split text into overlapping chunks that fit within embedding model limits.

    Args:
        text: Full text to chunk.
        max_chars: Maximum characters per chunk (~2048 tokens for embeddinggemma:300m).
        overlap: Character overlap between consecutive chunks for context continuity.

    Returns:
        List of text chunks. Single-element list if text fits in one chunk.
    """
    if not text or not text.strip():
        return []

    text = text.strip()

    # Fast path: text fits in one chunk
    if len(text) <= max_chars:
        return [text]

    # Split into paragraphs first (preserves semantic units)
    paragraphs = re.split(r'\n\s*\n', text)
    # Fallback: if no paragraph breaks, split by single newlines
    if len(paragraphs) == 1:
        paragraphs = text.split('\n')

    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If single paragraph exceeds max_chars, split it by sentences
        if len(para) > max_chars:
            # Flush current buffer first
            if current.strip():
                chunks.append(current.strip())
                current = ""
            # Split large paragraph into sentence-level chunks
            sentence_chunks = _split_by_sentences(para, max_chars, overlap)
            chunks.extend(sentence_chunks)
            continue

        # Would adding this paragraph exceed the limit?
        candidate = (current + "\n\n" + para).strip() if current else para
        if len(candidate) <= max_chars:
            current = candidate
        else:
            # Flush current chunk
            if current.strip():
                chunks.append(current.strip())
            # Start new chunk with overlap from end of previous
            if overlap > 0 and chunks:
                tail = chunks[-1][-overlap:]
                current = tail + "\n\n" + para
                # If overlap + new para exceeds limit, just use the para
                if len(current) > max_chars:
                    current = para
            else:
                current = para

    # Flush remaining
    if current.strip():
        chunks.append(current.strip())

    return chunks if chunks else [text[:max_chars]]


def _split_by_sentences(text: str, max_chars: int, overlap: int) -> List[str]:
    """Split text by sentence boundaries when paragraphs are too long."""
    # Split on sentence endings (. ! ? followed by space or end)
    sentences = re.split(r'(?<=[.!?])\s+', text)

    if not sentences:
        return _split_by_words(text, max_chars, overlap)

    chunks: List[str] = []
    current = ""

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue

        # Single sentence exceeds limit — split by words
        if len(sent) > max_chars:
            if current.strip():
                chunks.append(current.strip())
                current = ""
            word_chunks = _split_by_words(sent, max_chars, overlap)
            chunks.extend(word_chunks)
            continue

        candidate = (current + " " + sent).strip() if current else sent
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current.strip():
                chunks.append(current.strip())
            if overlap > 0 and chunks:
                tail = chunks[-1][-overlap:]
                current = tail + " " + sent
                if len(current) > max_chars:
                    current = sent
            else:
                current = sent

    if current.strip():
        chunks.append(current.strip())

    return chunks


def _split_by_words(text: str, max_chars: int, overlap: int) -> List[str]:
    """Last resort: split by words when sentences are too long."""
    words = text.split()
    if not words:
        return [text[:max_chars]] if text else []

    chunks: List[str] = []
    current_words: List[str] = []
    current_len = 0

    for word in words:
        new_len = current_len + len(word) + (1 if current_words else 0)
        if new_len <= max_chars:
            current_words.append(word)
            current_len = new_len
        else:
            if current_words:
                chunks.append(" ".join(current_words))
            # Overlap: keep last N chars worth of words
            if overlap > 0 and chunks:
                tail_text = chunks[-1][-overlap:]
                tail_words = tail_text.split()
                current_words = tail_words + [word]
                current_len = sum(len(w) for w in current_words) + len(current_words) - 1
                if current_len > max_chars:
                    current_words = [word]
                    current_len = len(word)
            else:
                current_words = [word]
                current_len = len(word)

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks
