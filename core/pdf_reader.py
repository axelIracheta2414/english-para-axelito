"""Lectura de PDFs: extracción de texto (nativo u OCR), caché en disco y búsqueda de extractos.

Principio pedagógico: la app NUNCA reescribe ni inventa reglas. Solo muestra extractos
literales de los PDFs (con fuente y número de página) junto a los datos del JSON.

Los PDFs de Murphy y PET 2 son escaneos (imágenes sin texto), por eso existe un paso de OCR
offline (scripts/build_pdf_index.py). En ejecución la app solo lee la caché.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pymupdf  # PyMuPDF

MIN_NATIVE_CHARS = 40  # por debajo de esto se considera página escaneada


class PdfTextIndex:
    """Texto por página de un PDF, con caché JSON."""

    def __init__(self, pdf_path: Path, cache_path: Path):
        self.pdf_path = Path(pdf_path)
        self.cache_path = Path(cache_path)
        self.pages: Dict[int, str] = {}
        self._load_cache()

    # ---------- caché ----------
    def _load_cache(self) -> None:
        if self.cache_path.exists():
            raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
            self.pages = {int(k): v for k, v in raw.items()}

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self.pages, ensure_ascii=False), encoding="utf-8")

    @property
    def is_ready(self) -> bool:
        return bool(self.pages) and any(len(t) > MIN_NATIVE_CHARS for t in self.pages.values())

    # ---------- construcción del índice ----------
    def build(self, ocr: Optional[Callable[[bytes], str]] = None,
              progress: Optional[Callable[[int, int], None]] = None,
              save_every: int = 20) -> None:
        """Extrae el texto de todas las páginas. Reanudable: omite las ya procesadas.

        `ocr` recibe bytes PNG y devuelve texto; solo se invoca en páginas sin texto nativo.
        """
        doc = pymupdf.open(self.pdf_path)
        total = len(doc)
        for i in range(total):
            if i in self.pages and (len(self.pages[i]) > MIN_NATIVE_CHARS or ocr is None):
                continue
            text = doc[i].get_text().strip()
            if len(text) < MIN_NATIVE_CHARS and ocr is not None:
                png = doc[i].get_pixmap(matrix=pymupdf.Matrix(2, 2)).tobytes("png")
                text = ocr(png)
            self.pages[i] = text
            if progress:
                progress(i + 1, total)
            if (i + 1) % save_every == 0:
                self._save_cache()
        self._save_cache()

    # ---------- búsqueda ----------
    def search_by_heading(self, terms: List[str], limit: int = 2, heading_chars: int = 220,
                          max_chars: int = 1100) -> List[dict]:
        """Devuelve páginas cuyo TÍTULO contiene alguno de los `terms`.

        Solo se mira el inicio de la página (con espacios normalizados) para no confundir una unidad
        con otra que solo menciona el término. Se descartan ejercicios, apéndices, índice y guías
        de estudio, y se prefieren las páginas de explicación ("UNIT n ...").
        """
        noise = ("exercises", "appendix", "study guide", "additional exercises", "key to", "index")
        results = []
        for page_no, text in self.pages.items():
            head = " ".join(text[:heading_chars].split()).lower()
            if any(n in head[:60] for n in noise):
                continue
            hits = sum(1 for t in terms if t.lower() in head)
            if not hits:
                continue
            body = _clean(text)
            lowered = body.lower()
            exercise_penalty = lowered.count("exercise") + lowered.count("complete the sentences")
            unit_bonus = 8 if re.search(r"\bunit\b", head[:40]) else 0
            score = hits * 10 + unit_bonus - exercise_penalty * 3 + min(len(body), 1500) / 300
            results.append((score, page_no, body))
        results.sort(reverse=True)
        return [
            {"page": p + 1, "text": _truncate(body, max_chars)}
            for _, p, body in results[:limit]
        ]


def _clean(text: str) -> str:
    text = text.replace("\r", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    last = max(cut.rfind(". "), cut.rfind("\n"))
    return (cut[:last] if last > max_chars * 0.5 else cut).rstrip() + " …"


def make_rapidocr() -> Callable[[bytes], str]:
    """Crea una función OCR basada en RapidOCR (dependencia opcional)."""
    from rapidocr_onnxruntime import RapidOCR

    engine = RapidOCR()

    def run(png_bytes: bytes) -> str:
        result, _ = engine(png_bytes)
        if not result:
            return ""
        # result: [[box, text, score], ...] -> orden de lectura aproximado (fila, columna)
        def key(item):
            x0, y0 = item[0][0]
            return (round(y0 / 14), x0)
        return "\n".join(item[1] for item in sorted(result, key=key))

    return run
