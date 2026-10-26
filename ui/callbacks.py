"""Callbacks de Dash: traducen eventos de UI en transiciones de la máquina de estados.

Un único callback con Inputs por patrón (ALL). Los patrones aceptan listas vacías, así que el
callback se dispara sin importar qué controles tenga la vista actual.
"""
from __future__ import annotations

from dash import ALL, Input, Output, State, callback_context, no_update

from core import session
from ui import layout


def register_callbacks(app, modules, store):
    @app.callback(Output("view", "children"), Input("state", "data"))
    def render_view(state):
        return layout.render(state or session.new_state(), modules, store)

    @app.callback(
        Output("state", "data"),
        Input({"type": "act", "name": ALL}, "n_clicks"),
        Input({"type": "tok", "i": ALL}, "n_clicks"),
        Input({"type": "opt", "i": ALL}, "n_clicks"),
        Input({"type": "mopt", "i": ALL}, "n_clicks"),
        Input({"type": "mrow", "i": ALL}, "n_clicks"),
        State("state", "data"),
        State({"type": "ans", "k": ALL}, "value"),
        prevent_initial_call=True,
    )
    def transition(_act, _tok, _opt, _mopt, _mrow, state, texts):
        ctx = callback_context
        # Al re-renderizar, los botones nuevos llegan con n_clicks=0: no son clics reales.
        if not ctx.triggered or not ctx.triggered[0]["value"]:
            return no_update
        trig = ctx.triggered_id
        state = state or session.new_state()
        kind, name = trig["type"], trig.get("name")

        # ---- navegación ----
        if kind == "act":
            if name == "home":
                return session.new_state()
            if name.startswith("open:"):
                return session.start_theory(name.split(":", 1)[1])
            if name == "review":
                return session.start_review(modules, store) or no_update
            if name == "next":
                return {**state, "step": state.get("step", 0) + 1}
            if name == "prev":
                return {**state, "step": max(0, state.get("step", 0) - 1)}
            if name in ("start-quiz", "restart"):
                return session.start_quiz(modules[state["module_id"]])

        # ---- quiz ----
        if state.get("view") != "quiz":
            return no_update
        if kind == "act" and name == "continue":
            return session.advance(state)
        if state.get("feedback"):
            return no_update  # ya respondida: ignorar toques

        ex = session.current(state)
        if kind == "tok":
            if trig["i"] in state["selected"]:
                return no_update
            return {**state, "selected": state["selected"] + [trig["i"]]}
        if kind == "opt":
            return {**state, "choice": trig["i"]}
        if kind in ("mopt", "mrow"):
            n = len(ex["pairs"])
            matches = list(state.get("matches") or [None] * n)
            matches += [None] * (n - len(matches))
            if kind == "mopt":
                if trig["i"] in matches or None not in matches:
                    return no_update
                matches[matches.index(None)] = trig["i"]
            else:
                matches[trig["i"]] = None
            return {**state, "matches": matches}

        if kind == "act":
            if name == "undo":
                return {**state, "selected": state["selected"][:-1]}
            if name == "clear":
                return {**state, "selected": []}
            if name == "submit":
                t = ex["type"]
                if t == "order":
                    if not state["selected"]:
                        return no_update
                    answer = [ex["bank"][i] for i in state["selected"]]
                elif t == "mcq":
                    if state.get("choice") is None:
                        return no_update
                    answer = ex["options"][state["choice"]]
                elif t == "match":
                    matches = state.get("matches") or []
                    if len(matches) < len(ex["pairs"]) or any(v is None for v in matches):
                        return no_update
                    answer = [ex["options"][j] for j in matches]
                else:  # fill / translate
                    answer = (texts[0] if texts else "") or ""
                    if not answer.strip():
                        return no_update
                return session.submit(state, answer, store)
        return no_update
