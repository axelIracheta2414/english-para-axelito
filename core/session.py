"""Máquina de estados de la sesión de estudio (pura, serializable en dcc.Store).

Vistas: home -> theory -> quiz -> summary   (y 'review' reutiliza quiz/summary)
Repetición espaciada dentro de la sesión: una pregunta fallada se reinserta
RETRY_GAP posiciones más adelante, hasta MAX_RETRIES veces.
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

import config
from core import exercise_factory as ef
from core.content_loader import Module
from core.srs import ProgressStore


def new_state() -> Dict[str, Any]:
    return {"view": "home"}


def start_theory(module_id: str) -> Dict[str, Any]:
    return {"view": "theory", "module_id": module_id, "step": 0}


def _quiz_state(module_id: Optional[str], queue: List[dict], review: bool) -> Dict[str, Any]:
    return {
        "view": "quiz", "module_id": module_id, "review": review,
        "queue": queue, "pos": 0, "retries": {}, "attempts": [],
        "selected": [], "choice": None, "matches": [], "feedback": None,
    }


def start_quiz(module: Module) -> Dict[str, Any]:
    queue = ef.build_lesson(module, config.QUIZ_SCENARIOS, config.QUIZ_MATCHING, config.THEORY_EXAMPLES)
    return _quiz_state(module.module_id, queue, review=False)


def start_review(modules: Dict[str, Module], store: ProgressStore, limit: int = 12) -> Optional[Dict[str, Any]]:
    keys = store.due_keys()[:limit]
    if not keys:
        return None
    return _quiz_state(None, [ef.from_key(modules, k) for k in keys], review=True)


def current(state: Dict[str, Any]) -> Optional[dict]:
    q, pos = state["queue"], state["pos"]
    return q[pos] if pos < len(q) else None


def submit(state: Dict[str, Any], answer: Any, store: ProgressStore) -> Dict[str, Any]:
    """Corrige, registra en la repetición espaciada y reencola si falló."""
    state = copy.deepcopy(state)
    ex = current(state)
    ok, model_answer = ef.check_answer(ex, answer)
    key = ex["key"]
    first_attempt = key not in state["retries"] and not any(a["key"] == key for a in state["attempts"])
    state["attempts"].append({"key": key, "correct": ok, "first": first_attempt, "type": ex["type"]})
    store.record(key, ok)

    requeued = False
    if not ok:
        n = state["retries"].get(key, 0)
        if n < config.MAX_RETRIES:
            state["retries"][key] = n + 1
            insert_at = min(state["pos"] + 1 + config.RETRY_GAP, len(state["queue"]))
            state["queue"].insert(insert_at, copy.deepcopy(ex))
            requeued = True
    state["feedback"] = {"ok": ok, "model": model_answer, "requeued": requeued}
    return state


def advance(state: Dict[str, Any]) -> Dict[str, Any]:
    state = copy.deepcopy(state)
    state["pos"] += 1
    state["selected"] = []
    state["choice"] = None
    state["matches"] = []
    state["feedback"] = None
    if state["pos"] >= len(state["queue"]):
        state["view"] = "summary"
    return state


def summarize(state: Dict[str, Any]) -> Dict[str, Any]:
    firsts = [a for a in state["attempts"] if a["first"]]
    correct_first = sum(1 for a in firsts if a["correct"])
    by_type: Dict[str, List[int]] = {}
    for a in firsts:
        t = by_type.setdefault(a["type"], [0, 0])
        t[0] += a["correct"]
        t[1] += 1
    return {
        "total": len(firsts), "correct_first": correct_first,
        "pct": round(100 * correct_first / len(firsts)) if firsts else 0,
        "by_type": by_type,
        "recovered": sum(1 for a in state["attempts"] if not a["first"] and a["correct"]),
    }
