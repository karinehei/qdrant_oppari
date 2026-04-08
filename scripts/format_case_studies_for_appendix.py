#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Format Case Studies for Appendix Script

Converts outputs/experiments/case_studies.md into a LAB thesis appendix-friendly
Markdown file (LIITE_X_Case_esimerkit.md) with Finnish labels and consistent numbering.

Workflow order (always run in this sequence):
  1. python scripts/generate_case_studies.py
  2. python scripts/format_case_studies_for_appendix.py

Usage:
    python scripts/format_case_studies_for_appendix.py
    python scripts/format_case_studies_for_appendix.py --appendix-number 3
    python scripts/format_case_studies_for_appendix.py --include-snippets false
"""

from __future__ import annotations

import argparse
import html
import logging
import re
import sys
from pathlib import Path
from typing import Any

# Add project root to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Format case_studies.md into LAB thesis appendix Markdown"
    )
    parser.add_argument(
        "--input",
        default="outputs/experiments/case_studies.md",
        help="Input case_studies.md path (default: outputs/experiments/case_studies.md)",
    )
    parser.add_argument(
        "--output",
        default="outputs/experiments/LIITE_X_Case_esimerkit.md",
        help="Output appendix path (default: outputs/experiments/LIITE_X_Case_esimerkit.md)",
    )
    parser.add_argument(
        "--appendix-number",
        default="X",
        help="Appendix number, e.g. X or 3 (default: X)",
    )
    parser.add_argument(
        "--title",
        default="Kysymys–haku–vastaus -esimerkit (RAG-putki)",
        help="Appendix title (default: Kysymys–haku–vastaus -esimerkit (RAG-putki))",
    )
    parser.add_argument(
        "--max-snippet-chars",
        type=int,
        default=160,
        help="Max characters per snippet (default: 160)",
    )
    parser.add_argument(
        "--include-snippets",
        type=lambda x: str(x).lower() not in ("false", "0", "no", "off"),
        default=True,
        metavar="BOOL",
        help="Include snippet column (default: true)",
    )
    parser.add_argument(
        "--no-snippets",
        dest="include_snippets",
        action="store_false",
        help="Disable snippets (shorthand for --include-snippets false)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging",
    )
    return parser.parse_args()


def resolve_path(p: str, base: Path) -> Path:
    path = Path(p)
    if not path.is_absolute():
        path = base / path
    return path


def normalize_text(s: str, eval_level: str | None = None) -> str:
    """Apply text fixes: typos, HTML entities, inflection, doc-level wording.

    - hakkivat -> hakivat (typo)
    - &lt;, &gt;, &amp; etc. -> <, >, & (via html.unescape)
    - gold-kohtetta -> gold-kohdetta (inflection)
    - gold-dokumentit/chunkit -> gold-dokumentit when eval_level=doc
    """
    s = s.replace("hakkivat", "hakivat")
    s = html.unescape(s)
    s = s.replace("gold-kohtetta", "gold-kohdetta")
    if eval_level and str(eval_level).lower() == "doc":
        s = s.replace("gold-dokumentit/chunkit", "gold-dokumentit")
    return s


# English -> Finnish translation for interpretation bullets
_INTERP_TRANSLATIONS: list[tuple[str, str]] = [
    (r"^\-\s*\*\*Success:\*\*\s*All gold documents/chunks were retrieved in top-k\.$",
     "- **Onnistui:** Kaikki gold-dokumentit/chunkit löytyivät top-k:sta."),
    (r"^\-\s*\*\*Failure:\*\*\s*No gold items in top-k \(recall@k=0\)\.$",
     "- **Epäonnistui:** Yhtään gold-kohtetta ei löytynyt top-k:sta (recall@k=0)."),
    (r"^\-\s*Gold was ranked highly \(nDCG@k ≥ 0\.9\)\.$",
     "- Gold sijoittui korkealle (nDCG@k ≥ 0,9)."),
    (r"^\-\s*Gold appeared but ranking could be improved\.$",
     "- Gold löytyi, mutta järjestystä voisi parantaa."),
    (r"^\-\s*Gold did not appear in top-k or was ranked very low\.$",
     "- Gold ei löytynyt top-k:sta tai sijoittui hyvin alas."),
    (r"^\-\s*\*\*Latency outlier:\*\*\s*High latency may be due to cold start, reranker load, or hardware variance\.$",
     "- **Latenssi-poikkeama:** Latenssi voi liittyä esimerkiksi yksittäiseen hitaaseen hakuun tai ajonaikaiseen kuormitukseen; poikkeamat varmistetaan per-kysely-tasolla (per_query_metrics.csv)."),
    (r"^\-\s*\*\*Config disagreement:\*\*\s*Different configs produced different recall; worth comparing\.$",
     "- **Konfiguraatioero:** Eri konfiguraatiot tuottivat eri recall-arvot; vertailun arvoista."),
    (r"^\-\s*\*\*Config disagreement:\*\*\s*Another config retrieved the gold; focus config \(e\.g\. reranker\) pushed it out of top-k\.$",
     "- **Konfiguraatioero:** Toinen konfiguraatio haki goldin; fokus-konfiguraatio (esim. reranker) työnsi sen top-k:n ulkopuolelle."),
    (r"^\-\s*See comparison table for config-wise metrics\.$",
     "- Katso vertailutaulukko konfiguraatiokohtaisille mittareille."),
]


def _translate_interpretation(line: str) -> str:
    """Translate known English interpretation bullets to Finnish."""
    line_stripped = line.strip()
    for pattern, replacement in _INTERP_TRANSLATIONS:
        if re.match(pattern, line_stripped):
            return replacement
    # Partial with percentage - translate pattern (use Finnish decimal comma)
    m = re.match(r"^-\s*\*\*Partial:\*\*\s*(\d+%)\s+of gold items retrieved \(recall@k=([\d.]+)\)\.$", line_stripped)
    if m:
        dec = m.group(2).replace(".", ",")
        return f"- **Osittain:** {m.group(1)} gold-kohteista löytyi top-k:sta (recall@k={dec})."
    return line  # Keep as-is if no match


def _truncate_snippet(text: str, max_chars: int) -> str:
    """Truncate snippet, replace newlines with spaces."""
    if not text or not isinstance(text, str):
        return ""
    s = re.sub(r"\s+", " ", text).strip()
    return (s[:max_chars] + "…") if len(s) > max_chars else s


def _parse_case_studies(content: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Parse case_studies.md into metadata dict and list of case dicts.
    Returns (metadata, cases).
    """
    metadata: dict[str, Any] = {}
    cases: list[dict[str, Any]] = []

    # Extract generated timestamp
    gen_match = re.search(r"\*Generated:\s*([^*]+)\*", content)
    if gen_match:
        metadata["generated"] = gen_match.group(1).strip()

    # Extract run metadata bullets
    meta_section = re.search(
        r"## Run Metadata\s*\n(.*?)(?=\n## |\nThis appendix|\Z)",
        content,
        re.DOTALL,
    )
    if meta_section:
        for m in re.finditer(r"\*\*([^:*]+):\*\*\s*(.+)", meta_section.group(1)):
            metadata[m.group(1).strip()] = m.group(2).strip()

    # Split by case headers: ## Case N — query_id
    case_blocks = re.split(r"\n## Case \d+ — ", content)
    if len(case_blocks) <= 1:
        return metadata, cases

    # First block is header + metadata + intro; skip
    for block in case_blocks[1:]:
        if not block.strip():
            continue
        lines = block.strip().split("\n")
        query_id = lines[0].strip() if lines else "?"
        case: dict[str, Any] = {"query_id": query_id}

        text = "\n".join(lines[1:]) if len(lines) > 1 else ""

        # Question
        q_match = re.search(r"\*\*Question:\*\*\s*(.+?)(?=\n\*\*|\n###|\Z)", text, re.DOTALL)
        if q_match:
            case["question"] = q_match.group(1).strip()

        # Gold
        g_match = re.search(
            r"\*\*Gold\s*\([^)]+\):\*\*\s*(.+?)(?=\n\*\*|\n###|\Z)",
            text,
            re.DOTALL,
        )
        if g_match:
            case["gold"] = g_match.group(1).strip()

        # Focus config
        fc_match = re.search(r"\*\*Focus config:\*\*\s*(.+?)(?=\n\*\*|\n###|\Z)", text, re.DOTALL)
        if fc_match:
            case["focus_config"] = fc_match.group(1).strip()

        # Metrics
        m_match = re.search(
            r"\*\*Metrics \(focus config\):\*\*\s*(.+?)(?=\n\*\*|\n###|\Z)",
            text,
            re.DOTALL,
        )
        if m_match:
            case["metrics"] = m_match.group(1).strip()

        # Top hits table
        th_match = re.search(
            r"### Top hits.*?\n\n(\|.+\|[\s\S]*?)(?=\n### |\n---|\Z)",
            text,
        )
        if th_match:
            case["top_hits_raw"] = th_match.group(1).strip()

        # Comparison table
        comp_match = re.search(
            r"### Comparison.*?\n\n(\|.+\|[\s\S]*?)(?=\n### |\n---|\Z)",
            text,
        )
        if comp_match:
            case["comparison_raw"] = comp_match.group(1).strip()

        # Interpretation
        interp_match = re.search(
            r"### Interpretation\s*\n\n([\s\S]*?)(?=\n---|\n## |\Z)",
            text,
        )
        if interp_match:
            case["interpretation"] = interp_match.group(1).strip()
        else:
            case["interpretation"] = ""

        cases.append(case)

    return metadata, cases


def _reformat_top_hits_table(
    raw: str,
    include_snippets: bool,
    max_snippet_chars: int,
    has_rerank: bool,
) -> str:
    """Reformat top hits table with Finnish headers and optional snippet truncation."""
    lines = raw.strip().split("\n")
    if len(lines) < 2:
        return raw

    header = lines[0]
    sep = lines[1]
    data_rows = lines[2:]

    # Parse header to detect columns
    cols = [c.strip() for c in header.strip("|").split("|")]
    col_map = {c.lower(): i for i, c in enumerate(cols)}

    # Finnish header mapping
    finnish_headers = {
        "rank": "Sijoitus",
        "doc_id": "Lähde (doc_id/source)",
        "source": "Lähde (doc_id/source)",
        "title": "Otsikko",
        "score": "Piste (score)",
        "rerank_score": "Rerank-piste",
        "snippet": "Katkelma",
    }

    out_cols: list[str] = []
    for c in cols:
        key = c.lower().replace(" ", "_")
        out_cols.append(finnish_headers.get(key, c))

    # Build new header - omit rerank if not present, omit snippet if disabled
    new_header_parts: list[str] = []
    new_indices: list[int] = []
    for i, c in enumerate(cols):
        key = c.lower().replace(" ", "_")
        if key == "rerank_score" and not has_rerank:
            continue
        if key == "snippet" and not include_snippets:
            continue
        new_header_parts.append(finnish_headers.get(key, c))
        new_indices.append(i)

    header_line = "| " + " | ".join(new_header_parts) + " |"
    sep_line = "| " + " | ".join("---" for _ in new_header_parts) + " |"

    out_rows = [header_line, sep_line]
    for row in data_rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        if len(cells) < len(cols):
            continue
        new_cells: list[str] = []
        for idx in new_indices:
            if idx >= len(cells):
                new_cells.append("")
                continue
            val = cells[idx]
            # Truncate snippet if present
            if cols[idx].lower() in ("snippet",) and include_snippets:
                val = _truncate_snippet(val, max_snippet_chars)
            new_cells.append(val.replace("|", "\\|"))
        out_rows.append("| " + " | ".join(new_cells) + " |")

    return "\n".join(out_rows)


# Section: Liitteen lukeminen ja gold-annotointi (thesis-appendix friendly)
_LUKEMINEN_SECTION = """
## Liitteen lukeminen ja gold-annotointi

- **Gold** tarkoittaa tässä liitteessä kysymyksen kannalta relevantteja dokumentteja (doc-tason arviointi). Gold-lähteet on annotoitu etukäteen; ne toimivat vertailupohjana hakutulosten arvioinnissa.
- **Relevanssi** on binäärinen (relevantti / ei relevantti), ellei toisin mainita.
- **eval_level=doc** tarkoittaa, että arviointi tehdään dokumenttitasolla: sama dokumentti voi tuottaa useita top-k-rivejä, koska hausta palautuu eri katkelmat (chunks) samasta dokumentista.
- **Toistuva doc_id** top-k-taulukossa ei siis tarkoita useita erillisiä dokumentteja vaan eri katkelmia samasta lähteestä.
- **recall@k** kuvaa sitä, kuinka suuri osa gold-dokumenteista löytyi top-k-tuloksista (0–1).
- **nDCG@k** mittaa hakutulosten järjestystä: mitä korkeammalle gold sijoittuu, sitä parempi nDCG.
- **latenssi_ms** on mitattu kokeen toteutuksen mukaisesti ja kattaa vähintään haun; tarkka mittauskohta on dokumentoitu run_metadata.json-tiedostoon.
- **Katkelmat** on rajattu lyhyiksi (truncated) tekijänoikeussyistä; ne eivät korvaa alkuperäistä lähdettä.
""".strip()

# Note under Hakutulokset (top-k)
_DOC_ID_NOTE = "Huom: doc-tason arvioinnissa sama doc_id voi esiintyä useana rivinä (eri katkelmat samasta dokumentista)."

# Dedupe-slower note (when C3 latency > C2)
_DEDUPE_SLOWER_NOTE = "- Tässä yksittäisessä tapauksessa deduplikointi ei pienentänyt latenssia, mikä viittaa siihen, että latenssiin vaikuttavat myös ajonaikaiset tekijät (kuorma, outlierit) eikä pelkästään rerankattavien kandidaattien määrä."

# Yhteenveto section (generic patterns)
_YHTEENVETO_SECTION = """
## Yhteenveto liitteen havainnoista

- Näissä esimerkeissä baseline (C0) ja MMR (C1) hakkivat goldin usein, kun taas rerank-konfiguraatiot (C2, C3) eivät aina löytäneet sitä.
- Rerank paransi järjestystä (nDCG) kun gold oli top-k:ssa, mutta joissakin tapauksissa rerank työnsi goldin ulos top-k:sta.
- Konfiguraatioeroja esiintyi: C1 haki goldin joissakin tapauksissa, joissa C2 epäonnistui.
- Latenssi vaihteli voimakkaasti konfiguraatioittain; rerank-konfiguraatiot olivat tyypillisesti hitaimpia.
- Deduplikointi (C3) pienensi latenssia useissa tapauksissa verrattuna C2:een, mutta ei aina.
- Osittaiset tulokset (recall@k &lt; 1) esiintyivät tapauksissa, joissa gold-dokumentteja oli useita.
- Katkelmat on rajattu lyhyiksi; alkuperäiset lähteet tulee tarkistaa erikseen.
""".strip()


def _parse_comparison_latencies(comp_raw: str) -> tuple[float | None, float | None]:
    """Extract C2 and C3 latency_ms from comparison table. Returns (c2_ms, c3_ms)."""
    c2_ms: float | None = None
    c3_ms: float | None = None
    lines = comp_raw.strip().split("\n")
    if len(lines) < 3:
        return c2_ms, c3_ms
    # Find latency column index (last column typically)
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    sep = lines[1]
    try:
        lat_idx = next(i for i, h in enumerate(header) if "latency" in h.lower() or "latenssi" in h.lower())
    except StopIteration:
        lat_idx = -1
    for row in lines[2:]:
        cells = [c.strip() for c in row.strip("|").split("|")]
        if len(cells) <= max(lat_idx, 0):
            continue
        config = cells[0] if cells else ""
        try:
            val = float(cells[lat_idx])
        except (ValueError, IndexError):
            continue
        if "C2" in config and "C3" not in config:
            c2_ms = val
        elif "C3" in config:
            c3_ms = val
    return c2_ms, c3_ms


def run_format(args: argparse.Namespace) -> bool:
    """Format case_studies.md into appendix. Returns True if successful."""
    base = PROJECT_ROOT
    in_path = resolve_path(args.input, base)
    out_path = resolve_path(args.output, base)

    if not in_path.exists():
        logger.error("Input file not found: %s", in_path)
        return False

    content = in_path.read_text(encoding="utf-8")
    metadata, cases = _parse_case_studies(content)

    if not cases:
        logger.error("No cases found in input")
        return False

    X = args.appendix_number
    title = args.title

    lines: list[str] = []
    lines.append(f"# Liite {X}. {title}")
    lines.append("")
    lines.append(
        "Tässä liitteessä esitetään valitut esimerkkitapaukset RAG-putken hakutuloksista. "
        "Jokaisessa tapauksessa näytetään kysymys, haetut lähteet (top-k), mittarit (recall@k, nDCG@k, latenssi) "
        "ja lyhyt tulkinta. Taulukot esittävät sijoituksen, lähteen (doc_id), otsikon, pisteen ja mahdollisesti "
        "rerank-pisteen sekä lyhyen katkelman."
    )
    lines.append("")
    lines.append(_LUKEMINEN_SECTION)
    lines.append("")
    lines.append("## Ajo- ja kokoelmatiedot")
    lines.append("")
    if metadata.get("generated"):
        lines.append(f"- **Ajoajankohta:** {metadata['generated']}")
    if metadata.get("collection_name"):
        lines.append(f"- **Kokoelma:** {metadata['collection_name']}")
    if metadata.get("top_k") is not None:
        lines.append(f"- **top_k:** {metadata['top_k']}")
    if metadata.get("initial_limit") is not None:
        lines.append(f"- **initial_limit:** {metadata['initial_limit']}")
    if metadata.get("score_threshold") is not None:
        lines.append(f"- **score_threshold:** {metadata['score_threshold']}")
    if metadata.get("eval_level"):
        lines.append(f"- **eval_level:** {metadata['eval_level']}")
    if metadata.get("seed") is not None:
        lines.append(f"- **seed:** {metadata['seed']}")
    if metadata.get("rerank_models_loaded"):
        lines.append(f"- **Rerank-malli(t):** {metadata['rerank_models_loaded']}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, case in enumerate(cases, 1):
        lines.append(f"## {X}.{i} {case.get('query_id', '?')}")
        lines.append("")
        lines.append(f"**Kysymys:** {case.get('question', '(ei kysymystä)')}")
        lines.append("")
        lines.append(f"**Gold (relevantit lähteet):** {case.get('gold', '')}")
        lines.append("")
        lines.append(f"**Konfiguraatio:** {case.get('focus_config', '')}")
        lines.append("")
        metrics = (case.get("metrics", "") or "").replace("latency_ms=", "latenssi_ms=")
        lines.append(f"**Mittarit (recall@k, nDCG@k, latenssi):** {metrics}")
        lines.append("")

        # Top hits table
        raw_hits = case.get("top_hits_raw", "")
        has_rerank = "rerank_score" in raw_hits.lower() or "rerank" in raw_hits.lower()
        formatted_hits = _reformat_top_hits_table(
            raw_hits,
            args.include_snippets,
            args.max_snippet_chars,
            has_rerank,
        )
        lines.append("### Hakutulokset (top-k)")
        lines.append("")
        lines.append(_DOC_ID_NOTE)
        lines.append("")
        lines.append(formatted_hits)
        lines.append("")

        # Comparison table (translate headers to Finnish)
        comp_raw = case.get("comparison_raw", "")
        if comp_raw:
            lines.append("### Vertailu (kaikki konfiguraatiot)")
            lines.append("")
            comp_fi = comp_raw.replace("| config_name |", "| Konfiguraatio |").replace(
                "| latency_ms |", "| latenssi_ms |"
            )
            lines.append(comp_fi)
            lines.append("")

        # Interpretation (translate to Finnish)
        lines.append("### Tulkinta")
        lines.append("")
        interp = case.get("interpretation", "").strip()
        if interp:
            for line in interp.split("\n"):
                line = line.strip()
                if line and line.startswith("-"):
                    lines.append(_translate_interpretation(line))
        else:
            lines.append(
                "- (Täydennä: onnistuiko haku? löytyikö gold top-k:sta? oliko järjestys järkevä?)"
            )
        # Add dedupe-slower note when C3 latency > C2
        comp_raw = case.get("comparison_raw", "")
        if comp_raw:
            c2_ms, c3_ms = _parse_comparison_latencies(comp_raw)
            if c2_ms is not None and c3_ms is not None and c3_ms > c2_ms:
                lines.append(_DEDUPE_SLOWER_NOTE)
        lines.append("")
        lines.append("---")
        lines.append("")

    # Yhteenveto section
    lines.append(_YHTEENVETO_SECTION)
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_str = normalize_text("\n".join(lines), metadata.get("eval_level"))
    out_path.write_text(out_str, encoding="utf-8")

    print(f"\nInput:  {in_path}")
    print(f"Output: {out_path}")
    print(f"Cases processed: {len(cases)}")

    return True


def main() -> None:
    args = parse_args()
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s",
    )
    ok = run_format(args)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    # Self-check: normalize_text
    assert normalize_text("hakkivat") == "hakivat"
    assert normalize_text("recall@k &lt; 1") == "recall@k < 1"
    assert normalize_text("gold-kohtetta") == "gold-kohdetta"
    assert normalize_text("gold-dokumentit/chunkit", "doc") == "gold-dokumentit"
    assert normalize_text("gold-dokumentit/chunkit", None) == "gold-dokumentit/chunkit"
    main()
