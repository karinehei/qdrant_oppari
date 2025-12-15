# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict

__all__ = ["groundedness_proxy"]

def groundedness_proxy(answer_text: str, allowed_sources: List[str]) -> Dict[str, bool]:
    lower = answer_text.lower()
    has_section = "lähteet" in lower
    mentions_any = any(src.lower() in lower for src in allowed_sources if src)
    return {"has_sources_section": has_section, "mentions_allowed_source": mentions_any}
