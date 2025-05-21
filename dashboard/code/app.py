from factory import create_app
from dash_app import create_dash_app

app = create_app()
dash_app = create_dash_app(app)