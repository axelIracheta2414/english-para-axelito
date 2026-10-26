"""Vistas de la interfaz (Dash). Solo construye componentes: no contiene lógica pedagógica.

Regla de oro: Dash solo ejecuta un callback si TODOS sus Input/State existen en el layout actual.
Como cada vista muestra controles distintos, todos usan IDs por patrón (que admiten listas vacías):

    {"type": "act",  "name": ...}   botones de acción (navegación, comprobar, continuar…)
    {"type": "tok",  "i": n}        palabras del banco (ejercicio de ordenar)
    {"type": "opt",  "i": n}        opciones del ejercicio de opción múltiple
    {"type": "mopt", "i": n}        opciones en inglés del emparejamiento
    {"type": "mrow", "i": n}        fila en español del emparejamiento (tocar para vaciarla)
    {"type": "ans",  "k": "text"}   campo de texto (rellenar / traducir)
"""
from __future__ import annotations

from typing import Any, Dict

from dash import dcc, html

from core import exercise_factory as ef
from core import session
from core import theory
from core.content_loader import Module
from core.srs import ProgressStore


# ---------- piezas reutilizables ----------
def btn(label, name, kind="primary", **kw):
    return html.Button(label, id={"type": "act", "name": name}, n_clicks=0,
                       className=f"btn btn-{kind}", **kw)


def dots(total: int, active: int):
    return html.Div(
        [html.Span(className="dot " + ("done" if i < active else "active" if i == active else ""))
         for i in range(total)],
        className="dots",
    )


def card(children, accent: str | None = None, cls: str = ""):
    style = {"--accent": accent} if accent else {}
    return html.Div(children, className=f"card {cls}", style=style)


def actionbar(*children):
    """Barra de acciones fija abajo: el pulgar siempre alcanza el botón principal."""
    return html.Div(list(children), className="actionbar")


# ---------- HOME ----------
def home_view(modules: Dict[str, Module], store: ProgressStore) -> html.Div:
    due = len(store.due_keys())
    review = card([
        html.Div([
            html.H3("Repaso espaciado"),
            html.P(f"{due} pregunta(s) para repasar hoy." if due
                   else "Nada pendiente hoy. Completa una lección para generar repasos.",
                   className="muted"),
        ]),
        btn("Repasar ahora", "review", "accent", disabled=not due),
    ], cls="review-card")

    cards = []
    for m in modules.values():
        st = store.module_stats(m.module_id)
        cards.append(card([
            html.Div(m.icon, className="module-icon"),
            html.H3(m.title),
            html.P(m.concept, className="muted clamp"),
            html.Div(f"Dominadas: {st['mastered']} · Vistas: {st['seen']}", className="chip"),
            btn("Estudiar", f"open:{m.module_id}"),
        ], accent=m.color, cls="module-card"))
    return html.Div([
        html.H2("Elige una lección"),
        review,
        html.Div(cards, className="grid"),
    ])


# ---------- TEORÍA ----------
def theory_view(state: Dict[str, Any], modules: Dict[str, Module]) -> html.Div:
    m = modules[state["module_id"]]
    steps = theory.theory_steps(m)
    step_i = min(state.get("step", 0), len(steps) - 1)
    s = steps[step_i]

    if s["kind"] == "concept":
        body = [html.P(s["text"], className="analogy")]
        if not any(x["kind"] == "pdf" for x in steps):
            body.append(html.P("Aún no hay extractos de PDF indexados "
                               "(ejecuta scripts/build_pdf_index.py).", className="muted small"))
    elif s["kind"] == "pdf":
        body = [html.Div([
            html.Div(f"{e['source']} · pág. {e['page']} · «{e['topic']}»", className="chip"),
            html.Pre(e["text"], className="excerpt"),
        ]) for e in s["excerpts"]]
    else:
        body = [
            html.Div([html.Span("ES", className="tag"), html.Span(s["es"])], className="line"),
            html.Div([html.Span("EN", className="tag tag-en"), html.Strong(s["en"])], className="line"),
            html.Div([html.Span("Por qué", className="tag tag-why"), html.Span(s["explanation"])],
                     className="why"),
        ]

    last = step_i == len(steps) - 1
    return html.Div([
        html.Div([btn("←", "home", "ghost", title="Inicio"),
                  html.H2(f"{m.icon} {m.title}", className="topbar-title")], className="topbar"),
        dots(len(steps), step_i),
        card([html.H3(s["title"]), *body], accent=m.color),
        actionbar(
            btn("← Atrás", "prev", "ghost", disabled=step_i == 0),
            btn("Ir al cuestionario →", "start-quiz", "accent") if last else btn("Siguiente →", "next"),
        ),
    ])


# ---------- QUIZ ----------
def _cloze_text(ex: dict, middle):
    return html.Div([html.Span(ex["before"] + " "), middle,
                     html.Span((ex["punct"] + " " + ex["after"]).strip())], className="cloze")


def _answer_area(ex: dict, state: dict, locked: bool):
    t = ex["type"]
    if t == "order":
        bank, sel = ex["bank"], state.get("selected", [])
        built = html.Div(
            [html.Span(bank[i], className="token built") for i in sel] or
            [html.Span("Toca las palabras en orden…", className="muted")],
            className="built-line",
        )
        tokens = html.Div([
            html.Button(tok, id={"type": "tok", "i": i}, n_clicks=0,
                        className="token", disabled=locked or i in sel)
            for i, tok in enumerate(bank)
        ], className="bank")
        tools = html.Div([btn("↶ Deshacer", "undo", "ghost", disabled=locked or not sel),
                          btn("Limpiar", "clear", "ghost", disabled=locked or not sel)], className="tools")
        return [built, tokens, tools]

    if t == "fill":
        return [_cloze_text(ex, dcc.Input(
            id={"type": "ans", "k": "text"}, type="text", className="gap", autoComplete="off",
            disabled=locked, debounce=False, placeholder="…", size="12"))]

    if t == "mcq":
        choice = state.get("choice")
        return [
            _cloze_text(ex, html.Span(
                ex["options"][choice] if choice is not None else "_____", className="blank")),
            html.Div([
                html.Button(o, id={"type": "opt", "i": i}, n_clicks=0, disabled=locked,
                            className="opt" + (" selected" if i == choice else ""))
                for i, o in enumerate(ex["options"])
            ], className="opts"),
        ]

    if t == "translate":
        return [html.P(f"Escríbela en inglés ({ex['n_words']} palabras).", className="muted small"),
                dcc.Textarea(id={"type": "ans", "k": "text"}, className="textarea", disabled=locked,
                             placeholder="Write the sentence in English…")]

    if t == "match":
        n = len(ex["pairs"])
        matches = state.get("matches") or [None] * n
        matches = matches + [None] * (n - len(matches))
        current = next((i for i, v in enumerate(matches) if v is None), None)
        used = {v for v in matches if v is not None}
        rows = [html.Button([
            html.Span(p["es"], className="match-es"),
            html.Span(ex["options"][matches[i]] if matches[i] is not None else "Toca una opción abajo",
                      className="match-slot" + (" filled" if matches[i] is not None else "")
                      + (" current" if i == current else "")),
        ], id={"type": "mrow", "i": i}, n_clicks=0, disabled=locked or matches[i] is None,
            className="match-row") for i, p in enumerate(ex["pairs"])]
        options = html.Div([
            html.Button(o, id={"type": "mopt", "i": j}, n_clicks=0,
                        disabled=locked or j in used, className="opt")
            for j, o in enumerate(ex["options"])
        ], className="opts")
        return [html.P("Toca una opción para llenar la siguiente fila. Toca una fila para vaciarla.",
                       className="muted small"), html.Div(rows, className="match-rows"), options]
    return []


def _prompt(ex: dict):
    return "Une cada frase con su traducción" if ex["type"] == "match" else ex["prompt_es"]


def quiz_view(state: Dict[str, Any], modules: Dict[str, Module]) -> html.Div:
    ex = session.current(state)
    fb = state.get("feedback")
    locked = fb is not None
    m = modules.get(ex["module_id"])
    total = len(state["queue"])

    feedback = None
    if fb:
        title = "✓ ¡Correcto!" if fb["ok"] else "✗ Todavía no"
        extra = ([html.P(f"Respuesta modelo: {fb['model']}", className="model")]
                 if not fb["ok"] or ex["type"] == "match" else [])
        if fb["requeued"]:
            extra.append(html.P("Esta pregunta volverá a aparecer en unos minutos (repaso espaciado).",
                                className="muted small"))
        feedback = html.Div([html.H4(title), *extra, html.P(ex["explanation"], className="why-text")],
                            className="feedback " + ("ok" if fb["ok"] else "bad"))

    action = btn("Continuar →", "continue", "accent") if locked else btn("Comprobar", "submit")
    return html.Div([
        html.Div([btn("←", "home", "ghost", title="Salir"),
                  html.Div(f"{m.icon} {m.title}" if m and not state.get("review") else "🔁 Repaso espaciado",
                           className="chip grow"),
                  html.Div(f"{min(state['pos'] + 1, total)}/{total}", className="chip")], className="topbar"),
        html.Div(html.Div(className="bar-fill", style={"width": f"{100 * state['pos'] / total:.0f}%"}),
                 className="bar"),
        card([
            html.Div(ef.TYPE_LABELS[ex["type"]], className="chip type-chip"),
            html.H3(_prompt(ex), className="prompt"),
            *_answer_area(ex, state, locked),
            feedback,
        ], accent=m.color if m else None),
        actionbar(action),
    ])


# ---------- RESUMEN ----------
def summary_view(state: Dict[str, Any], modules: Dict[str, Module]) -> html.Div:
    s = session.summarize(state)
    rows = [html.Div([html.Span(ef.TYPE_LABELS[t]), html.Strong(f"{ok}/{n}")], className="row")
            for t, (ok, n) in s["by_type"].items()]
    msg = ("¡Excelente dominio!" if s["pct"] >= 85 else
           "Buen avance; las falladas volverán en tus repasos." if s["pct"] >= 60 else
           "Normal al empezar: repasa la teoría y vuelve a intentar.")
    module_id = state.get("module_id")
    actions = [btn("Inicio", "home", "ghost")]
    if module_id:
        actions += [btn("Teoría", f"open:{module_id}", "ghost"), btn("Otra ronda", "restart", "accent")]
    return html.Div([
        card([
            html.H2("Resultado"),
            html.Div(f"{s['pct']}%", className="score"),
            html.P(f"{s['correct_first']} de {s['total']} a la primera · "
                   f"{s['recovered']} recuperadas en reintentos. {msg}"),
            html.Div(rows, className="rows"),
        ]),
        actionbar(*actions),
    ])


# ---------- ENRUTADOR ----------
def render(state: Dict[str, Any], modules: Dict[str, Module], store: ProgressStore):
    view = state.get("view", "home")
    if view == "theory":
        return theory_view(state, modules)
    if view == "quiz":
        return quiz_view(state, modules)
    if view == "summary":
        return summary_view(state, modules)
    return home_view(modules, store)


def build_layout() -> html.Div:
    return html.Div([
        dcc.Store(id="state", storage_type="session", data=session.new_state()),
        html.Header([html.H1("English Lab"), html.Span("A2 → B1", className="muted")], className="brand"),
        html.Main(id="view"),
    ], className="app")
