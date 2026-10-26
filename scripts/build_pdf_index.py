"""Construye el índice de texto de los PDFs (OCR en escaneos). Se ejecuta una sola vez.

Uso:
    python scripts/build_pdf_index.py            # murphy + pet (rápido)
    python scripts/build_pdf_index.py murphy     # un PDF concreto
    python scripts/build_pdf_index.py pet2       # PET 2 (escaneado, tarda más)
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from core.pdf_reader import PdfTextIndex, make_rapidocr


def main(keys):
    ocr = make_rapidocr()
    for key in keys:
        src = config.PDF_SOURCES[key]
        index = PdfTextIndex(config.CONTENT_DIR / src["file"], config.PDF_CACHE_DIR / f"{key}.json")
        start = time.time()

        def progress(done, total):
            if done % 10 == 0 or done == total:
                print(f"[{key}] {done}/{total} páginas ({time.time() - start:.0f}s)", flush=True)

        index.build(ocr=ocr, progress=progress)
        print(f"[{key}] listo -> {index.cache_path}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or ["pet", "murphy"])
