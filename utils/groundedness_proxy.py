# -*- coding: utf-8 -*-
"""
Groundedness Proxy Module

Provides simple validation to check if LLM responses properly cite sources.
This is a lightweight proxy metric for groundedness - more sophisticated
methods would use NLI models or fact-checking systems.

Functions:
    groundedness_proxy: Check if answer contains source section and mentions allowed sources
"""
from __future__ import annotations
from typing import List, Dict

__all__ = ["groundedness_proxy"]

def groundedness_proxy(answer_text: str, allowed_sources: List[str]) -> Dict[str, bool]:
    """
    Check if LLM answer contains source citations.
    
    This is a simple proxy metric that checks:
    1. Whether the answer contains a "Lähteet" (Sources) section
    2. Whether any allowed source is mentioned in the answer
    
    Args:
        answer_text: The LLM-generated answer text
        allowed_sources: List of source identifiers that should be cited
    
    Returns:
        Dictionary with:
            - has_sources_section: True if "lähteet" found in answer (case-insensitive)
            - mentions_allowed_source: True if any allowed source is mentioned
    
    Example:
        >>> result = groundedness_proxy(
        ...     "Answer text. Lähteet: [lähde: doc1]",
        ...     ["doc1", "doc2"]
        ... )
        >>> result["has_sources_section"]
        True
        >>> result["mentions_allowed_source"]
        True
    
    Note:
        This is a simple heuristic. For production, consider using NLI models
        or more sophisticated fact-checking systems.
    """
    lower = answer_text.lower()
    has_section = "lähteet" in lower
    mentions_any = any(src.lower() in lower for src in allowed_sources if src)
    return {"has_sources_section": has_section, "mentions_allowed_source": mentions_any}
