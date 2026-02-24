# -*- coding: utf-8 -*-
"""
Data Loading Module

Loads Finnish research documents from files for indexing in the RAG pipeline.
Supports PDF primarily; prepared for future .txt, .md, .html support.

This module is intended for research use and does not replace config.DOCS demo.
"""

from __future__ import annotations

import csv
import logging
import re
from pathlib import Path
from typing import Any, Callable

__all__ = ["load_documents_from_raw_dir", "DocumentDict"]

# Configure module logger
logger = logging.getLogger(__name__)

# Type alias for document dict (compatible with document_processing.build_corpus)
DocumentDict = dict[str, Any]


def _clean_text(text: str) -> str:
    """
    Light text cleaning: normalize whitespace and remove duplicate empty lines.

    Does not perform aggressive cleaning (e.g. no stemming, no stopword removal).
    """
    if not text or not isinstance(text, str):
        return ""
    # Normalize whitespace: collapse runs of spaces/tabs to single space
    text = re.sub(r"[ \t]+", " ", text)
    # Normalize line endings to \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Remove duplicate empty lines (max one blank line between content)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip leading/trailing whitespace per line and overall
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def _extract_metadata_from_filename(filepath: Path) -> tuple[str, str | None]:
    """
    Extract title and author from filename (e.g. Antikainen_Jari.pdf -> title, author).

    Returns:
        (title, author) - title is human-readable filename; author parsed if Lastname_Firstname.
    """
    stem = filepath.stem  # e.g. "Antikainen_Jari" or "Holopainen_Petri"
    title = stem.replace("_", " ")  # Human-readable fallback
    author: str | None = None

    # Pattern: Lastname_Firstname (Finnish convention)
    parts = stem.split("_")
    if len(parts) >= 2:
        lastname, firstname = parts[0], parts[1]
        author = f"{firstname} {lastname}"

    return title, author


def _infer_source_type(filepath: Path, raw_dir: Path) -> str:
    """
    Infer source_type from path relative to raw_dir.

    - 'theseus' if path contains 'theseus'
    - 'official_doc' if path contains 'docs'
    - 'raw' as fallback
    """
    try:
        rel = filepath.resolve().relative_to(raw_dir.resolve())
        path_lower = str(rel).lower()
        if "theseus" in path_lower:
            return "theseus"
        if "docs" in path_lower:
            return "official_doc"
    except ValueError:
        pass
    return "raw"


def _read_pdf(filepath: Path) -> str | None:
    """
    Extract text from PDF using pypdf. Combines all pages into one string.

    Returns:
        Extracted text or None on failure.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.warning("pypdf not installed. Install with: pip install pypdf")
        return None

    try:
        reader = PdfReader(str(filepath))
        parts: list[str] = []
        for page in reader.pages:
            raw = page.extract_text()
            if raw:
                parts.append(raw)
        return "\n".join(parts) if parts else None
    except Exception as e:
        logger.warning("Failed to read PDF %s: %s", filepath, e)
        return None


def _read_txt(filepath: Path) -> str | None:
    """
    Read plain text file. Light support for future use.
    """
    try:
        return filepath.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.warning("Failed to read TXT %s: %s", filepath, e)
        return None


def _read_md(filepath: Path) -> str | None:
    """
    Read Markdown file. Stub for future use - treats as plain text.
    """
    return _read_txt(filepath)


def _read_html(filepath: Path) -> str | None:
    """
    Read HTML file. Stub for future use - extracts raw text (no tag stripping yet).
    """
    # Minimal: read as text; future: use BeautifulSoup to strip tags
    return _read_txt(filepath)


def _load_metadata_csv(csv_path: Path) -> dict[str, dict[str, Any]]:
    """
    Load metadata CSV into a dict keyed by filepath or doc_id.

    Expected columns (flexible): filepath, doc_id, title, author, year, url, source_type
    """
    if not csv_path.exists():
        logger.warning("Metadata CSV not found: %s", csv_path)
        return {}

    rows_by_key: dict[str, dict[str, Any]] = {}
    try:
        with open(csv_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Prefer filepath, then doc_id, then first column as key
                key = row.get("filepath") or row.get("doc_id") or list(row.values())[0]
                if key:
                    rows_by_key[str(key).strip()] = dict(row)
    except Exception as e:
        logger.warning("Failed to parse metadata CSV %s: %s", csv_path, e)
    return rows_by_key


def _enrich_from_csv(
    doc: DocumentDict, metadata_map: dict[str, dict[str, Any]], filepath: Path
) -> None:
    """
    Enrich document with CSV metadata. Matches by filepath or doc id.
    """
    if not metadata_map:
        return

    # Try full path, relative path, filename, stem
    candidates = [
        str(filepath),
        str(filepath.name),
        filepath.stem,
        doc.get("id", ""),
    ]
    for c in candidates:
        if c in metadata_map:
            meta = metadata_map[c]
            for field in ("title", "author", "year", "url", "source_type"):
                val = meta.get(field)
                if val is not None and str(val).strip():
                    doc[field] = str(val).strip()
            break


def load_documents_from_raw_dir(
    raw_dir: str,
    metadata_csv_path: str | None = None,
) -> list[DocumentDict]:
    """
    Load documents from a raw directory (recursively) and return a unified document list.

    Supports:
    - PDF (primary)
    - .txt, .md, .html (light support / stubs)

    Each document is a dict with: id, title, text, source, source_type, language,
    author, year, url, filepath. Compatible with document_processing.build_corpus().

    Args:
        raw_dir: Path to data/raw (or subdir). Traversed recursively.
        metadata_csv_path: Optional path to CSV with columns: filepath/doc_id,
            title, author, year, url, source_type. Enriches documents when provided.

    Returns:
        List of document dicts ready for indexing.

    Example:
        >>> docs = load_documents_from_raw_dir("data/raw")
        >>> len(docs)
        5
        >>> docs[0]["id"]  # relative path from raw_dir, e.g. "Holopainen_Petri"
        'Holopainen_Petri'
    """
    base = Path(raw_dir)
    if not base.exists():
        logger.error("Raw directory does not exist: %s", raw_dir)
        return []

    metadata_map = (
        _load_metadata_csv(Path(metadata_csv_path)) if metadata_csv_path else {}
    )

    documents: list[DocumentDict] = []
    seen_ids: set[str] = set()

    # File extension -> reader
    readers: dict[str, Callable[[Path], str | None]] = {
        ".pdf": _read_pdf,
        ".txt": _read_txt,
        ".md": _read_md,
        ".html": _read_html,
        ".htm": _read_html,
    }

    for filepath in sorted(base.rglob("*")):
        if not filepath.is_file():
            continue

        ext = filepath.suffix.lower()
        if ext not in readers:
            continue

        reader_fn = readers[ext]
        raw_text = reader_fn(filepath)
        if raw_text is None:
            continue

        text = _clean_text(raw_text)
        if not text.strip():
            logger.debug("Skipping empty or whitespace-only file: %s", filepath)
            continue

        title_fallback, author_fallback = _extract_metadata_from_filename(filepath)
        source_type = _infer_source_type(filepath, base)

        # id: unique, stable; use path relative to raw_dir
        try:
            rel = filepath.resolve().relative_to(base.resolve())
        except ValueError:
            rel = filepath
        doc_id = str(rel).replace("\\", "/").replace(filepath.suffix, "")

        # Avoid duplicate ids
        if doc_id in seen_ids:
            doc_id = f"{doc_id}_{filepath.stat().st_mtime}"
        seen_ids.add(doc_id)

        doc: DocumentDict = {
            "id": doc_id,
            "title": title_fallback,
            "text": text,
            "source": doc_id,
            "source_type": source_type,
            "language": "fi",
            "author": author_fallback,
            "year": None,
            "url": None,
            "filepath": str(filepath.resolve()),
        }

        _enrich_from_csv(doc, metadata_map, filepath)

        # Ensure build_corpus compatibility: id, title, text required
        documents.append(doc)

    logger.info("Loaded %d documents from %s", len(documents), raw_dir)
    return documents


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    raw_path = Path(__file__).parent / "data" / "raw"
    docs = load_documents_from_raw_dir(str(raw_path))

    print(f"\nLöytyi {len(docs)} dokumenttia.")
    if docs:
        for i, d in enumerate(docs[:2]):
            meta = {k: v for k, v in d.items() if k != "text"}
            text_preview = (d["text"][:80] + "...") if len(d.get("text", "")) > 80 else d.get("text", "")
            print(f"\n--- Esimerkki {i + 1} ---")
            print(f"  Metadata: {meta}")
            print(f"  Teksti (lyhyt): {text_preview}")
