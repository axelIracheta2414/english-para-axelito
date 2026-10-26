"""Punto de entrada: python app.py  ->  http://127.0.0.1:8050"""
import os

from dash import Dash

from core.content_loader import load_all_modules
from core.srs import ProgressStore
from ui.callbacks import register_callbacks
from ui.layout import build_layout

modules = load_all_modules()
store = ProgressStore()

app = Dash(
    __name__, suppress_callback_exceptions=True, title="English Lab",
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1, viewport-fit=cover"},
        {"name": "theme-color", "content": "#0d1020"},
        {"name": "mobile-web-app-capable", "content": "yes"},
    ],
)
app.layout = build_layout()
register_callbacks(app, modules, store)

if __name__ == "__main__":
    # HOST=0.0.0.0 expone la app en la red local (para abrirla desde el móvil)
    app.run(debug=False, host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8050")))
