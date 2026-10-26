"""Repetición espaciada persistente (cajas de Leitner) guardada en data/progress.json."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List

import config


class ProgressStore:
    def __init__(self, path: Path = config.PROGRESS_FILE):
        self.path = Path(path)
        self.items: Dict[str, dict] = {}
        if self.path.exists():
            self.items = json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.items, indent=1), encoding="utf-8")

    def record(self, key: str, correct: bool, today: date | None = None) -> None:
        """Acierto: sube de caja (intervalo más largo). Fallo: vuelve a la caja 0 (repasar hoy)."""
        today = today or date.today()
        item = self.items.setdefault(key, {"box": 0, "seen": 0, "fails": 0})
        item["seen"] += 1
        if correct:
            item["box"] = min(item["box"] + 1, len(config.LEITNER_DAYS) - 1)
        else:
            item["box"] = 0
            item["fails"] += 1
        item["due"] = (today + timedelta(days=config.LEITNER_DAYS[item["box"]])).isoformat()
        self._save()

    def due_keys(self, today: date | None = None, module_id: str | None = None) -> List[str]:
        """Claves vencidas, las más atrasadas / con más fallos primero."""
        today = (today or date.today()).isoformat()
        due = [
            (v["due"], -v["fails"], k) for k, v in self.items.items()
            if v.get("due", today) <= today and (module_id is None or k.startswith(module_id + "|"))
        ]
        return [k for _, _, k in sorted(due)]

    def module_stats(self, module_id: str) -> dict:
        mine = [v for k, v in self.items.items() if k.startswith(module_id + "|")]
        mastered = sum(1 for v in mine if v["box"] >= 3)
        return {"seen": len(mine), "mastered": mastered}
