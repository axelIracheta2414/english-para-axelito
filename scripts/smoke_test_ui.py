"""Prueba de humo: simula clics enviando los mismos POST que el navegador a /_dash-update-component.

Uso:  python scripts/smoke_test_ui.py
Recorre: home -> teoría -> cuestionario (todos los formatos) -> resumen, y falla si algún botón no responde.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as app_module
from core import session
from core.srs import ProgressStore

app_module.store.path = Path(tempfile.mkdtemp()) / "progress.json"  # no ensuciar el progreso real
client = app_module.app.server.test_client()


def pid(d):  # id por patrón tal como lo serializa Dash (claves ordenadas, sin espacios)
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def click(state, kind, text=None, **ident):
    """Envía un clic sobre {type: kind, **ident}. Devuelve el nuevo estado (o el mismo si no_update)."""
    target = {"type": kind, **ident}
    groups = {"act": [], "tok": [], "opt": [], "mopt": [], "mrow": []}
    ex_ids = {  # controles existentes en la vista; el clic objetivo siempre va incluido
        "act": ["home", "review", "next", "prev", "start-quiz", "restart", "submit", "continue", "undo", "clear"],
    }
    for name in ex_ids["act"]:
        groups["act"].append({"id": {"type": "act", "name": name}, "property": "n_clicks",
                              "value": 1 if target == {"type": "act", "name": name} else 0})
    for k in ("tok", "opt", "mopt", "mrow"):
        for i in range(30):
            groups[k].append({"id": {"type": k, "i": i}, "property": "n_clicks",
                              "value": 1 if target == {"type": k, "i": i} else 0})
    if kind == "act" and ident["name"].startswith("open:"):
        groups["act"].append({"id": target, "property": "n_clicks", "value": 1})
    changed = pid(target) + ".n_clicks"
    payload = {
        "output": "state.data",
        "outputs": {"id": "state", "property": "data"},
        "inputs": [groups["act"], groups["tok"], groups["opt"], groups["mopt"], groups["mrow"]],
        "state": [{"id": "state", "property": "data", "value": state},
                  [{"id": {"type": "ans", "k": "text"}, "property": "value", "value": text}]],
        "changedPropIds": [changed],
    }
    r = client.post("/_dash-update-component", json=payload)
    assert r.status_code == 204 or r.status_code == 200, f"HTTP {r.status_code}: {r.data[:300]}"
    if r.status_code == 204 or not r.data:
        return state
    body = r.get_json()
    return body["response"]["state"]["data"] if body.get("response") else state


def render(state):
    payload = {"output": "view.children", "outputs": {"id": "view", "property": "children"},
               "inputs": [{"id": "state", "property": "data", "value": state}], "changedPropIds": ["state.data"]}
    r = client.post("/_dash-update-component", json=payload)
    assert r.status_code == 200, f"render HTTP {r.status_code}: {r.data[:300]}"


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        sys.exit(1)


state = session.new_state()
render(state)
state = click(state, "act", name="open:module1-perfect")
check(state["view"] == "theory", "Estudiar abre la teoría")
state = click(state, "act", name="next")
check(state["step"] == 1, "Siguiente avanza")
state = click(state, "act", name="prev")
check(state["step"] == 0, "Atrás retrocede")
render(state)
state = click(state, "act", name="start-quiz")
check(state["view"] == "quiz", "Ir al cuestionario abre el quiz")

seen = set()
guard = 0
while state["view"] == "quiz" and guard < 40:
    guard += 1
    render(state)
    ex = session.current(state)
    t = ex["type"]
    seen.add(t)
    if t == "order":
        state = click(state, "tok", i=0)
        state = click(state, "act", name="undo")
        check(state["selected"] == [], f"[{t}] Deshacer")
        for tok_i in range(len(ex["answer"])):  # orden correcto: buscar cada palabra en el banco
            used = set(state["selected"])
            want = ex["answer"][len(state["selected"])]
            idx = next(i for i, w in enumerate(ex["bank"]) if w == want and i not in used)
            state = click(state, "tok", i=idx)
        check(len(state["selected"]) == len(ex["answer"]), f"[{t}] tocar palabras")
        state = click(state, "act", name="submit")
    elif t == "mcq":
        idx = ex["options"].index(ex["answer"])
        state = click(state, "opt", i=idx)
        state = click(state, "act", name="submit")
    elif t in ("fill", "translate"):
        state = click(state, "act", name="submit", text=ex["answer"])
    elif t == "match":
        for p in ex["pairs"]:
            state = click(state, "mopt", i=ex["options"].index(p["en"]))
        state = click(state, "act", name="submit")
    check(state["feedback"] is not None and state["feedback"]["ok"], f"[{t}] Comprobar -> correcto")
    render(state)
    state = click(state, "act", name="continue")

check(state["view"] == "summary", f"Cuestionario termina en resumen (formatos vistos: {sorted(seen)})")
render(state)
state = click(state, "act", name="home")
check(state["view"] == "home", "Inicio vuelve a home")
print("\nTODO OK")
