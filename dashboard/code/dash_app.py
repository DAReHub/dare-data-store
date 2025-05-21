import os
from flask_login import current_user
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
from dotenv import load_dotenv

import htmlLayout
from callbacks import register_callbacks

load_dotenv()

def serve_layout():
    if not current_user.is_authenticated:
        return html.Div([dcc.Location(id='redirect', pathname='/login')])
    return htmlLayout.baseLayout()


def create_dash_app(server):
    dash_app = dash.Dash(
        __name__,
        server=server,
        suppress_callback_exceptions=True,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}],
        url_base_pathname='/',
        use_pages=True
    )

    if str(os.getenv("DEBUG")) == "true":
        dash_app.enable_dev_tools(
            dev_tools_ui=True, dev_tools_serve_dev_bundles=True
        )

    dash_app.layout = serve_layout
    register_callbacks(dash_app)

    return dash_app
