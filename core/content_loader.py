"""Procesamiento de los módulos JSON -> modelos de dominio (sin dependencias de UI)."""
from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import config


@dataclass
class Scenario:
    index: int
    prompt_es: str
    tokens: List[str]             # banco de palabras (incluye distractores)
    expected: List[str]           # oración correcta, en orden
    explanation: str

    @property
    def sentence(self) -> str:
        return " ".join(self.expected)

    @property
    def distractors(self) -> List[str]:
        """Tokens del banco que NO forman parte de la oración correcta (comparación multiconjunto)."""
        pool = list(self.expected)
        extras = []
        for tok in self.tokens:
            if tok in pool:
                pool.remove(tok)
            else:
                extras.append(tok)
        return extras


@dataclass
class Module:
    module_id: str
    title: str
    concept: str
    scenarios: List[Scenario] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    @property
    def icon(self) -> str:
        return self.meta.get("icon", "📘")

    @property
    def color(self) -> str:
        return self.meta.get("color", "#6c8cff")


def _txt(value: str) -> str:
    return html.unescape(value).strip()


def load_module(path: Path) -> Module:
    data = json.loads(path.read_text(encoding="utf-8"))
    scenarios = [
        Scenario(
            index=i,
            prompt_es=_txt(s["prompt"]),
            tokens=[_txt(t) for t in s["tokens"]],
            expected=[_txt(t) for t in s["expectedSequence"]],
            explanation=_txt(s["explanation"]),
        )
        for i, s in enumerate(data["interactiveScenarios"])
    ]
    module_id = data["moduleId"]
    return Module(
        module_id=module_id,
        title=_txt(data["moduleTitle"]),
        concept=_txt(data["concept"]),
        scenarios=scenarios,
        meta=config.MODULE_META.get(module_id, {}),
    )


def load_all_modules() -> Dict[str, Module]:
    modules: Dict[str, Module] = {}
    for name in config.MODULE_FILES:
        path = config.CONTENT_DIR / name
        if path.exists():
            m = load_module(path)
            modules[m.module_id] = m
    return modules
