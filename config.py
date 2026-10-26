"""Configuración central: rutas, fuentes PDF y metadatos pedagógicos por módulo."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONTENT_DIR = BASE_DIR            # Los JSON viven en la raíz del proyecto
DATA_DIR = BASE_DIR / "data"      # Caché de PDFs y progreso del alumno
PDF_CACHE_DIR = DATA_DIR / "pdf_cache"
PROGRESS_FILE = DATA_DIR / "progress.json"

MODULE_FILES = [
    "module1-perfect.json",
    "module2-narrative.json",
    "module3-connectors.json",
    "module4-modals.json",
]

PDF_SOURCES = {
    "murphy": {
        "file": "English Grammar in Use [Cambridge] - Raymond Murphy - 2nd Edition.pdf",
        "label": "English Grammar in Use (Murphy)",
    },
    "pet": {
        "file": "preliminary-english.pdf",
        "label": "Preliminary English",
    },
    "pet2": {
        "file": "Cambridge Preliminary English Test 2 [Book].pdf",
        "label": "Cambridge PET 2",
    },
}

# Metadatos por módulo:
#  - icon / color: presentación
#  - focus_words: palabras gramaticales que se "ocultan" en huecos y opción múltiple
#  - pdf_queries: encabezados a buscar en los PDFs (extractos literales, sin reescribir)
MODULE_META = {
    "module1-perfect": {
        "icon": "⏳",
        "color": "#6c8cff",
        "focus_words": ["has", "have", "since", "for", "yet", "already", "just", "ago", "did"],
        "pdf_queries": [
            {"source": "murphy", "terms": ["present perfect and past"]},
            {"source": "murphy", "terms": ["for and since"]},
            {"source": "murphy", "terms": ["still, yet and already"]},
        ],
    },
    "module2-narrative": {
        "icon": "⚡",
        "color": "#f7b955",
        "focus_words": ["was", "were", "when", "while", "had"],
        "pdf_queries": [
            {"source": "murphy", "terms": ["past continuous (i was doing)"]},
            {"source": "murphy", "terms": ["past continuous and simple", "past continuous and past simple"]},
        ],
    },
    "module3-connectors": {
        "icon": "🔗",
        "color": "#4fd1a5",
        "focus_words": ["although", "however", "therefore", "despite", "because", "because of",
                        "in spite of", "while", "whereas", "so", "but", "even though", "moreover"],
        "pdf_queries": [
            {"source": "murphy", "terms": ["although / though / even though", "although"]},
        ],
    },
    "module4-modals": {
        "icon": "🛡️",
        "color": "#ff7a90",
        "focus_words": ["must", "mustn't", "have to", "has to", "don't have to", "should", "ought to",
                        "shouldn't", "can", "could", "would", "if", "whether"],
        "pdf_queries": [
            {"source": "murphy", "terms": ["must and have to"]},
            {"source": "murphy", "terms": ["must mustn't needn't"]},
            {"source": "murphy", "terms": ["should (1)"]},
            {"source": "murphy", "terms": ["questions (2)"]},
        ],
    },
}

# Parámetros de la sesión de estudio
THEORY_EXAMPLES = 3          # escenarios usados como ejemplos resueltos (no entran al quiz)
QUIZ_SCENARIOS = 8           # ejercicios individuales por lección
QUIZ_MATCHING = 2            # rondas de emparejamiento por lección
MAX_RETRIES = 2              # veces que se reinserta una pregunta fallada dentro de la sesión
RETRY_GAP = 3                # cuántas preguntas después reaparece una fallada
LEITNER_DAYS = [0, 1, 3, 7, 14, 30]   # intervalos (días) por caja para la repetición espaciada
