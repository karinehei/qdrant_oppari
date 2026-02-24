# -*- coding: utf-8 -*-
"""
Document Processing Module

Handles document chunking and corpus construction from raw documents.
Supports both demo pipeline (simple chunking) and research use (PDF cleaning,
paragraph-based chunking with overlap and metadata).

Backward compatible: chunk() and build_corpus() remain unchanged for demo.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from config import DOCS

__all__ = [
    "chunk",
    "build_corpus",
    "normalize_whitespace",
    "fix_hyphenation",
    "remove_obvious_page_artifacts",
    "clean_pdf_text",
    "chunk_document",
    "build_corpus_research",
]

logger = logging.getLogger(__name__)

# Minimum chunk size to avoid tiny fragments (heuristiikka: alle 100 merkkiä on usein kohinaa)
MIN_CHUNK_CHARS = 100


# ---------------------------------------------------------------------------
# Text cleaning (PDF-specific, safe heuristics)
# ---------------------------------------------------------------------------


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace: collapse runs of spaces/tabs, unify line endings,
    remove excessive blank lines.

    Does NOT remove content or change word boundaries.
    """
    if not text or not isinstance(text, str):
        return ""
    text = re.sub(r"[ \t]+", " ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def fix_hyphenation(text: str) -> str:
    """
    Fix common PDF hyphenation: "word-\\ncontinuation" -> "wordcontinuation".

    Only joins when continuation starts with lowercase (Finnish: tavutus jatkuu
    pienellä kirjaimella, esim. "teko-\\näly" -> "tekoäly"). Avoids joining
    title-like breaks (e.g. "Osa-\\nOtsikko").
    """
    if not text or not isinstance(text, str):
        return ""
    # Pattern: hyphen + optional spaces + newline + optional spaces + lowercase/digit
    # Risk: "Osa-\\n1" would become "Osa1" - acceptable for list items
    return re.sub(r"-\s*\n\s*([a-zäöå0-9])", r"\1", text)


def remove_obvious_page_artifacts(text: str) -> str:
    """
    Remove obvious page-artifact lines: standalone page numbers, "- N -" patterns.

    Heuristic: only remove lines that look like page numbers (e.g. "12", "- 12 -",
    "12 / 45"). Does NOT remove short content lines or numbers in context.
    Risk: could remove "1" or "2" if they appear alone - rare in thesis body.
    """
    if not text or not isinstance(text, str):
        return ""
    lines = text.split("\n")
    result: List[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            result.append(line)
            continue
        # Standalone page number: only digits, optionally with spaces/dashes
        if re.match(r"^-?\s*\d+\s*$", line):
            continue  # "12", "- 12 ", "12"
        if re.match(r"^-?\s*\d+\s*/\s*\d+\s*$", line):
            continue  # "12 / 45"
        if re.match(r"^-\s*\d+\s*-$", line):
            continue  # "- 12 -"
        # Very short lines (< 10 chars) that are mostly digits/punctuation
        # (heuristiikka: header/footer-tyyppiset)
        if len(line) < 10 and re.match(r"^[\d\s\-\./]+$", line):
            continue
        result.append(line)
    return "\n".join(result)


def clean_pdf_text(text: str) -> str:
    """
    Full PDF text cleaning pipeline for Finnish research documents.

    Applies:
    1. normalize_whitespace
    2. fix_hyphenation
    3. remove_obvious_page_artifacts

    Does NOT:
    - Remove or change semantic content
    - Do stemming, lemmatization, or stopword removal
    - Strip headers/footers aggressively (only obvious page numbers)
    """
    if not text or not isinstance(text, str):
        return ""
    text = normalize_whitespace(text)
    text = fix_hyphenation(text)
    text = remove_obvious_page_artifacts(text)
    return normalize_whitespace(text)  # final pass after artifact removal


# ---------------------------------------------------------------------------
# Chunking (original, backward compatible)
# ---------------------------------------------------------------------------


def chunk(text: str, max_len: int = 256) -> List[str]:
    """
    Split text into chunks based on sentence boundaries.

    This function performs simple sentence-based chunking, splitting text at
    periods and grouping sentences into chunks that don't exceed max_len.

    Args:
        text: Input text to be chunked
        max_len: Maximum character length for each chunk (default: 256)

    Returns:
        List of text chunks, each not exceeding max_len characters

    Example:
        >>> chunk("First sentence. Second sentence. Third sentence.", max_len=30)
        ['First sentence. Second sentence.', 'Third sentence.']
    """
    s = [p.strip() for p in text.replace("\n", " ").split(".") if p.strip()]
    chunks, buf = [], ""
    for sent in s:
        if len(buf) + len(sent) + 1 <= max_len:
            buf = f"{buf} {sent}".strip()
        else:
            if buf:
                chunks.append(buf)
            buf = sent
    if buf:
        chunks.append(buf)
    return chunks


def build_corpus(docs: List[Dict]) -> List[Dict]:
    """
    Build a corpus from documents by chunking and adding metadata.

    Takes a list of documents, chunks each document's text, and creates
    corpus entries with unique identifiers and source tracking.

    Compatible with indexing.index() and demo pipeline.

    Args:
        docs: List of document dictionaries with keys:
            - id: Unique document identifier
            - title: Document title
            - text: Document content to be chunked

    Returns:
        List of corpus entries, each containing:
            - uid: Unique identifier in format "{doc_id}#{chunk_index}"
            - title: Original document title
            - text: Chunk text
            - source: Original document ID

    Example:
        >>> docs = [{"id": "doc1", "title": "Test", "text": "Sentence one. Sentence two."}]
        >>> corpus = build_corpus(docs)
        >>> len(corpus) > 0
        True
    """
    corpus = []
    for d in docs:
        for i, ch in enumerate(chunk(d["text"])):
            corpus.append({
                "uid": f"{d['id']}#{i}",
                "title": d["title"],
                "text": ch,
                "source": d["id"]
            })
    return corpus


# ---------------------------------------------------------------------------
# Research chunking (paragraph-based, overlap, metadata)
# ---------------------------------------------------------------------------


def _split_into_paragraphs(text: str) -> List[str]:
    """Split text by blank lines (double newline or more)."""
    if not text.strip():
        return []
    blocks = re.split(r"\n\s*\n", text)
    return [b.strip() for b in blocks if b.strip()]


def _split_into_sentences(text: str) -> List[str]:
    """Simple sentence split on period + space. Preserves sentence boundaries."""
    if not text.strip():
        return []
    parts = [p.strip() for p in re.split(r"[.!?]\s+", text) if p.strip()]
    if not parts:
        return [text.strip()] if text.strip() else []
    # Re-attach sentence-ending punctuation
    result: List[str] = []
    for i, p in enumerate(parts):
        if i < len(parts) - 1:
            result.append(p + ".")
        else:
            if text.rstrip().endswith((".", "!", "?")):
                result.append(p + text.rstrip()[-1])
            else:
                result.append(p)
    return result


def _chunk_by_char_window(
    text: str, max_len: int, overlap: int, prefer_boundary: str = "sentence"
) -> List[tuple[str, int, int]]:
    """
    Split text into chunks with overlap. Prefers sentence boundaries.
    Returns list of (chunk_text, char_start, char_end).
    """
    if not text.strip():
        return []
    if prefer_boundary == "sentence":
        units = _split_into_sentences(text)
    else:
        units = [text] if text.strip() else []

    chunks: List[tuple[str, int, int]] = []
    buf: List[str] = []
    buf_len = 0
    step_back = 0  # chars to overlap from previous chunk

    for unit in units:
        sep = 1 if buf else 0
        if buf_len + sep + len(unit) <= max_len:
            buf.append(unit)
            buf_len += sep + len(unit)
        else:
            if buf:
                chunk_text = " ".join(buf)
                # Find overlap point: last 'overlap' chars should start next chunk
                if overlap > 0 and len(chunk_text) > overlap:
                    overlap_start = chunk_text.rfind(" ", len(chunk_text) - overlap, len(chunk_text))
                    if overlap_start < 0:
                        overlap_start = max(0, len(chunk_text) - overlap)
                    step_back = len(chunk_text) - overlap_start
                else:
                    step_back = 0
                chunks.append((chunk_text, 0, len(chunk_text)))  # positions relative to block
                # Start next chunk with overlap
                if step_back > 0 and len(chunk_text) >= step_back:
                    overlap_text = chunk_text[-step_back:]
                    buf = [overlap_text] if overlap_text.strip() else []
                    buf_len = len(overlap_text)
                else:
                    buf = []
                    buf_len = 0
                # Add current unit if it fits
                if len(unit) <= max_len:
                    buf.append(unit)
                    buf_len += (1 if buf else 0) + len(unit)
                else:
                    for i in range(0, len(unit), max(1, max_len - overlap)):
                        seg = unit[i:i + max_len]
                        if seg.strip():
                            chunks.append((seg, 0, len(seg)))
            else:
                if len(unit) > max_len:
                    for i in range(0, len(unit), max(1, max_len - overlap)):
                        seg = unit[i:i + max_len]
                        if seg.strip():
                            chunks.append((seg, 0, len(seg)))
                else:
                    buf = [unit]
                    buf_len = len(unit)

    if buf:
        chunk_text = " ".join(buf)
        chunks.append((chunk_text, 0, len(chunk_text)))

    return chunks


def chunk_document(
    document: Dict[str, Any],
    max_len_chars: int = 800,
    overlap_chars: int = 120,
    strategy: str = "paragraph",
) -> List[Dict[str, Any]]:
    """
    Chunk a document for research use with overlap and metadata.

    Strategies:
    - paragraph: Split by blank lines first; combine short paragraphs, split long ones.
    - sentence: Fallback to sentence-based chunking (like original chunk()).

    Args:
        document: Dict with id, title, text; optionally source_type, language, year.
        max_len_chars: Maximum chunk size in characters.
        overlap_chars: Overlap between consecutive chunks.
        strategy: "paragraph" or "sentence".

    Returns:
        List of chunk dicts with: chunk_id, doc_id, chunk_index, char_start, char_end,
        title, text, source, source_type, language, year.
    """
    doc_id = document.get("id", "unknown")
    title = document.get("title", "")
    text = document.get("text", "")
    source = document.get("source", doc_id)
    source_type = document.get("source_type", "raw")
    language = document.get("language", "fi")
    year = document.get("year")

    text = clean_pdf_text(text)
    if not text.strip():
        return []

    chunks_out: List[Dict[str, Any]] = []

    if strategy == "paragraph":
        paragraphs = _split_into_paragraphs(text)
        combined: List[str] = []
        combined_len = 0

        for para in paragraphs:
            para_len = len(para) + (1 if combined else 0)
            if combined_len + para_len <= max_len_chars and combined:
                combined.append(para)
                combined_len += para_len
            elif combined_len + para_len <= max_len_chars:
                combined = [para]
                combined_len = len(para)
            else:
                if combined:
                    block = "\n\n".join(combined)
                    sub_chunks = _chunk_by_char_window(
                        block, max_len_chars, overlap_chars, prefer_boundary="sentence"
                    )
                    for sub_text, sub_start, sub_end in sub_chunks:
                        if len(sub_text.strip()) >= MIN_CHUNK_CHARS:
                            chunks_out.append({
                                "chunk_text": sub_text,
                                "char_start": sub_start,
                                "char_end": sub_end,
                            })
                if len(para) > max_len_chars:
                    sub_chunks = _chunk_by_char_window(
                        para, max_len_chars, overlap_chars, prefer_boundary="sentence"
                    )
                    for sub_text, sub_start, sub_end in sub_chunks:
                        if len(sub_text.strip()) >= MIN_CHUNK_CHARS:
                            chunks_out.append({
                                "chunk_text": sub_text,
                                "char_start": sub_start,
                                "char_end": sub_end,
                            })
                    combined = []
                    combined_len = 0
                else:
                    combined = [para]
                    combined_len = len(para)

        if combined:
            block = "\n\n".join(combined)
            if len(block.strip()) >= MIN_CHUNK_CHARS:
                sub_chunks = _chunk_by_char_window(
                    block, max_len_chars, overlap_chars, prefer_boundary="sentence"
                )
                for sub_text, sub_start, sub_end in sub_chunks:
                    if len(sub_text.strip()) >= MIN_CHUNK_CHARS:
                        chunks_out.append({
                            "chunk_text": sub_text,
                            "char_start": sub_start,
                            "char_end": sub_end,
                        })

    else:
        sub_chunks = _chunk_by_char_window(
            text, max_len_chars, overlap_chars, prefer_boundary="sentence"
        )
        for sub_text, sub_start, sub_end in sub_chunks:
            if len(sub_text.strip()) >= MIN_CHUNK_CHARS:
                chunks_out.append({
                    "chunk_text": sub_text,
                    "char_start": sub_start,
                    "char_end": sub_end,
                })

    result: List[Dict[str, Any]] = []
    for i, c in enumerate(chunks_out):
        chunk_text = c["chunk_text"]
        result.append({
            "chunk_id": f"{doc_id}#{i}",
            "uid": f"{doc_id}#{i}",
            "doc_id": doc_id,
            "chunk_index": i,
            "char_start": c["char_start"],
            "char_end": c["char_end"],
            "title": title,
            "text": chunk_text,
            "source": source,
            "source_type": source_type,
            "language": language,
            "year": year,
        })
    return result


def build_corpus_research(
    docs: List[Dict[str, Any]],
    max_len_chars: int = 800,
    overlap_chars: int = 120,
    strategy: str = "paragraph",
) -> List[Dict[str, Any]]:
    """
    Build corpus from documents using research chunking (clean_pdf_text + chunk_document).

    Returns chunks compatible with indexing.index() (uid, title, text, source).
    """
    corpus: List[Dict[str, Any]] = []
    for d in docs:
        for c in chunk_document(d, max_len_chars, overlap_chars, strategy):
            corpus.append({
                "uid": c["uid"],
                "title": c["title"],
                "text": c["text"],
                "source": c["source"],
            })
    return corpus


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    sample = """
    Tekoäly on tieteenala, joka käsittelee älykkyyttä. Tämä on
    toinen kappale. Siinä on useita lauseita. Kappale on melko pitkä.

    Kolmas kappale on lyhyt.

    Neljäs kappale sisältää tavutusjäänteitä: teko-
    äly ja kone-
    oppiminen yhdistyvät.

    - 12 -

    Viides kappale jatkuu normaalisti.
    """

    cleaned = clean_pdf_text(sample)
    print("=== clean_pdf_text (sample) ===")
    print("Hyphenation fixed:", "tekoäly" in cleaned and "teko-\näly" not in cleaned)
    print("Page artifact removed:", "- 12 -" not in cleaned)

    doc = {
        "id": "test_doc",
        "title": "Testidokumentti",
        "text": cleaned,
        "source": "test_doc",
        "source_type": "raw",
        "language": "fi",
        "year": None,
    }

    chunks = chunk_document(doc, max_len_chars=200, overlap_chars=30, strategy="paragraph")
    print(f"\n=== chunk_document ===")
    print(f"Chunks: {len(chunks)}")
    for i, c in enumerate(chunks[:2]):
        print(f"\n--- Chunk {i+1} ---")
        print(f"  chunk_id: {c['chunk_id']}")
        print(f"  char_start: {c['char_start']}, char_end: {c['char_end']}")
        print(f"  text (preview): {c['text'][:100]}...")
