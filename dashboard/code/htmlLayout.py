import os
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from flask_wtf.csrf import generate_csrf
from dotenv import load_dotenv
load_dotenv()

def baseLayout():
  return html.Div([
    html.Meta(name='csrf-token', content=generate_csrf()),
    dcc.Store(id='csrf-store', data=generate_csrf()),
    dbc.NavbarSimple(
      children=[
        dbc.NavItem(
          dbc.NavLink(
            "Home",
            href=f"{os.getenv('EXTERNAL_BASE_URL')}/home"
          )
        ),
        dbc.DropdownMenu(
          children=[
            dbc.DropdownMenuItem(
              "Help",
              id='help-button',
            ),
            dbc.DropdownMenuItem(
              "Logout",
              href="/logout",
              external_link=True
            ),
          ],
          nav=True,
          in_navbar=True,
          label="More",
        ),
      ],
      brand=[
        html.Img(
          src="/assets/DARe_logo_cropped_2.png",
          style={"width": "50px", "margin-right": "3%", "margin-bottom": "1%"}),
        "DARe DATA STORE"
      ],
      brand_style={
        "color": "#f9f9f9",
        "font-size": "2em",
        "margin-left": "1.1%"
      },
      fluid=True,
      # sticky='top',
      class_name="navbanner"
    ),
    dash.page_container,
    # html.Div(className='footer')
  ])