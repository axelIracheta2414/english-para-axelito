"""Teoría de cada lección: analogía (JSON) + extractos literales de los PDFs + ejemplos resueltos (JSON)."""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, List

import config
from core.content_loader import Module
from core.pdf_reader import PdfTextIndex


@lru_cache(maxsize=None)
def _index(source_key: str) -> PdfTextIndex:
    src = config.PDF_SOURCES[source_key]
    return PdfTextIndex(config.CONTENT_DIR / src["file"], config.PDF_CACHE_DIR / f"{source_key}.json")


def pdf_excerpts(module: Module, per_query: int = 1) -> List[Dict]:
    """Extractos literales del libro relacionados con el módulo. Lista vacía si el índice no existe."""
    excerpts, seen_pages = [], set()
    for q in module.meta.get("pdf_queries", []):
        index = _index(q["source"])
        if not index.is_ready:
            continue
        for hit in index.search_by_heading(q["terms"], limit=per_query):
            ref = (q["source"], hit["page"])
            if ref in seen_pages:
                continue
            seen_pages.add(ref)
            excerpts.append({
                "source": config.PDF_SOURCES[q["source"]]["label"],
                "page": hit["page"],
                "topic": ", ".join(q["terms"]),
                "text": hit["text"],
            })
    return excerpts


def theory_steps(module: Module) -> List[Dict]:
    """Pasos de teoría. Cada ejemplo va INMEDIATAMENTE después de la explicación que ilustra."""
    steps: List[Dict] = [{"kind": "concept", "title": "La idea clave", "text": module.concept}]
    excerpts = pdf_excerpts(module)
    if excerpts:
        steps.append({"kind": "pdf", "title": "Lo que dice el libro", "excerpts": excerpts})
    for i in range(min(config.THEORY_EXAMPLES, len(module.scenarios))):
        sc = module.scenarios[i]
        steps.append({
            "kind": "example", "title": f"Ejemplo {i + 1}",
            "es": sc.prompt_es, "en": sc.sentence, "explanation": sc.explanation,
        })
    return steps
