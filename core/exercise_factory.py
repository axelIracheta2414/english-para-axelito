"""Fábrica de ejercicios: transforma cada escenario JSON en 5 formatos de práctica.

Formatos:
  order     -> construir la oración con el banco de palabras (incluye distractores del JSON)
  fill      -> rellenar el hueco (palabra gramatical clave) escribiendo
  mcq       -> opción múltiple para el hueco (distractores = errores típicos del JSON)
  translate -> traducción inversa (español -> inglés) escrita
  match     -> emparejar 4 frases en español con su versión en inglés

Los ejercicios son diccionarios serializables y con clave determinista
(módulo|escenario|tipo): así la repetición espaciada puede reconstruirlos entre sesiones.
"""
from __future__ import annotations

import random
import re
import zlib
from typing import Any, Dict, List, Optional, Tuple

from core.content_loader import Module, Scenario

TYPES = ["mcq", "fill", "order", "translate"]
TYPE_LABELS = {
    "order": "Construye la oración",
    "fill": "Rellena el hueco",
    "mcq": "Opción múltiple",
    "translate": "Traducción inversa",
    "match": "Emparejar",
}
_TRAILING_PUNCT = re.compile(r"([.,;:!?]+)$")


# ---------- normalización ----------
def strip_punct(token: str) -> str:
    return _TRAILING_PUNCT.sub("", token)


def norm_token(token: str) -> str:
    return strip_punct(token).lower().strip()


def norm_sentence(text: str) -> str:
    """Minúsculas, sin puntuación ni apóstrofos (CI/CD == CICD, yesterday's == yesterdays)."""
    text = text.lower().replace("’", "'")
    text = re.sub(r"[^a-z0-9\- ]", "", text.replace("'", ""))
    return re.sub(r"\s+", " ", text).strip()


def _rng(key: str) -> random.Random:
    return random.Random(zlib.crc32(key.encode("utf-8")))


# ---------- selección de huecos ----------
def _focus_indices(sc: Scenario, focus_words: List[str]) -> List[int]:
    focus = {w.lower() for w in focus_words}
    return [i for i, t in enumerate(sc.expected) if norm_token(t) in focus]


def _pick_blank(sc: Scenario, focus_words: List[str], rng: random.Random, avoid: Optional[int] = None) -> int:
    candidates = _focus_indices(sc, focus_words)
    if not candidates:  # sin palabra clave: usar un distractor-gemelo o el centro de la oración
        candidates = [len(sc.expected) // 2]
    preferred = [c for c in candidates if c != avoid] or candidates
    return rng.choice(preferred)


def _blank_sentence(sc: Scenario, idx: int) -> Tuple[str, str, str]:
    """Devuelve (antes, puntuación_final_del_hueco, después)."""
    tok = sc.expected[idx]
    punct = _TRAILING_PUNCT.search(tok)
    return " ".join(sc.expected[:idx]), punct.group(1) if punct else "", " ".join(sc.expected[idx + 1:])


def _mcq_options(sc: Scenario, answer: str, focus_words: List[str], rng: random.Random) -> List[str]:
    ans = norm_token(answer)
    seen = {ans}
    focus_set = {w.lower() for w in focus_words}
    extras = [strip_punct(t) for t in sc.distractors]
    ordered = (
        [t for t in extras if t.lower() in focus_set]            # errores típicos del JSON que son palabras clave
        + [w for w in rng.sample(focus_words, len(focus_words))]  # resto de palabras clave del módulo
        + extras
    )
    options = [strip_punct(answer)]
    for cand in ordered:
        key = cand.lower()
        if key not in seen:
            seen.add(key)
            options.append(cand)
        if len(options) == 4:
            break
    rng.shuffle(options)
    return options


# ---------- construcción ----------
def build_exercise(module: Module, scenario_idx: int, ex_type: str) -> Dict[str, Any]:
    sc = module.scenarios[scenario_idx]
    key = f"{module.module_id}|{scenario_idx}|{ex_type}"
    rng = _rng(key)
    focus = module.meta.get("focus_words", [])
    base = {
        "key": key, "type": ex_type, "module_id": module.module_id,
        "scenario": scenario_idx, "prompt_es": sc.prompt_es,
        "explanation": sc.explanation, "sentence": sc.sentence,
    }

    if ex_type == "order":
        bank = list(sc.tokens)
        rng.shuffle(bank)
        return {**base, "bank": bank, "answer": list(sc.expected)}

    if ex_type == "translate":
        return {**base, "answer": sc.sentence, "n_words": len(sc.expected)}

    # fill y mcq comparten lógica de hueco; se evita repetir el mismo hueco entre ambos
    mcq_idx = _pick_blank(sc, focus, _rng(f"{module.module_id}|{scenario_idx}|mcq"))
    if ex_type == "mcq":
        idx = mcq_idx
    else:
        idx = _pick_blank(sc, focus, rng, avoid=mcq_idx)
    before, punct, after = _blank_sentence(sc, idx)
    answer = strip_punct(sc.expected[idx])
    out = {**base, "before": before, "after": after, "punct": punct, "answer": answer}
    if ex_type == "mcq":
        out["options"] = _mcq_options(sc, answer, focus, rng)
    return out


def build_match(module: Module, scenario_idxs: List[int]) -> Dict[str, Any]:
    key = f"{module.module_id}|match|{'-'.join(map(str, scenario_idxs))}"
    rng = _rng(key)
    pairs = [{"es": module.scenarios[i].prompt_es, "en": module.scenarios[i].sentence} for i in scenario_idxs]
    options = [p["en"] for p in pairs]
    rng.shuffle(options)
    return {
        "key": key, "type": "match", "module_id": module.module_id,
        "pairs": pairs, "options": options,
        "explanation": "\n".join(
            f"• {module.scenarios[i].sentence}: {module.scenarios[i].explanation}" for i in scenario_idxs
        ),
    }


def from_key(modules: Dict[str, Module], key: str) -> Dict[str, Any]:
    """Reconstruye un ejercicio a partir de su clave (usado por la repetición espaciada)."""
    module_id, middle, last = key.split("|")
    module = modules[module_id]
    if middle == "match":
        return build_match(module, [int(x) for x in last.split("-")])
    return build_exercise(module, int(middle), last)


def build_lesson(module: Module, n_scenarios: int, n_match: int, skip_first: int,
                 rng: Optional[random.Random] = None) -> List[Dict[str, Any]]:
    """Arma el cuestionario: variedad de formatos + rondas de emparejamiento al final."""
    rng = rng or random.Random()
    pool = list(range(skip_first, len(module.scenarios))) or list(range(len(module.scenarios)))
    chosen = rng.sample(pool, min(n_scenarios, len(pool)))
    exercises = [build_exercise(module, idx, TYPES[i % len(TYPES)]) for i, idx in enumerate(chosen)]
    rng.shuffle(exercises)
    rest = [i for i in pool if i not in chosen] or pool
    for _ in range(n_match):
        group = rng.sample(rest, min(4, len(rest)))
        exercises.append(build_match(module, group))
    return exercises


# ---------- corrección ----------
def check_answer(ex: Dict[str, Any], answer: Any) -> Tuple[bool, str]:
    """Devuelve (¿correcto?, respuesta modelo para mostrar)."""
    t = ex["type"]
    if t == "order":
        ok = [norm_token(a) for a in (answer or [])] == [norm_token(a) for a in ex["answer"]]
        return ok, " ".join(ex["answer"])
    if t == "translate":
        return norm_sentence(answer or "") == norm_sentence(ex["answer"]), ex["answer"]
    if t in ("fill", "mcq"):
        return norm_token(answer or "") == norm_token(ex["answer"]), ex["answer"]
    if t == "match":
        chosen = answer or []
        ok = len(chosen) == len(ex["pairs"]) and all(
            c == p["en"] for c, p in zip(chosen, ex["pairs"])
        )
        return ok, "\n".join(f'{p["es"]} → {p["en"]}' for p in ex["pairs"])
    raise ValueError(f"Tipo de ejercicio desconocido: {t}")
