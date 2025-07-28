import dash
from dash import dcc, html
import dash_bootstrap_components as dbc

dash.register_page(__name__)

layout = html.Div([
  dcc.Location(id='url', refresh=True),
  dbc.Container([
    dbc.Row([
      dbc.Col([
        html.Div([
          dbc.Row([
            dbc.Col([
              html.H1("Filter Data Catalogue"),
            ], width=6),
            dbc.Col([
              html.Div([
                dbc.ButtonGroup([
                  dbc.Button(
                    'Apply filters',
                    id='datadict-apply-filters',
                    n_clicks=0,
                    className='me-1',
                    outline=True,
                    color='primary',
                    size='lg',
                  ),
                  dbc.Button(
                    'Remove filters',
                    id='datadict-remove-filters',
                    n_clicks=0,
                    className='me-1',
                    outline=True,
                    color='primary',
                    size='lg',
                  ),
                ]),
              ], style={'text-align': 'right'})
            ], width=6),
          ], justify='between'),
          html.Hr(),
          html.Br(),
          dbc.Row([
            dbc.Col([
              html.H5("Search name"),
              dbc.Input(
                id="filter-datadict-name",
                type='text',
                size="lg"
              ),
            ], xs=12, sm=12, md=4, lg=4, xl=4),
            dbc.Col([
              html.H5("Search UUID"),
              dbc.Input(
                id="filter-datadict-uuid",
                type='text',
                size="lg"
              ),
            ], xs=12, sm=12, md=4, lg=4, xl=4),
            dbc.Col([
              html.H5("Model domain"),
              dcc.Dropdown(
                id="filter-datadict-model_domain",
                placeholder="all",
                multi=True,
                value=[]
              ),
            ], xs=12, sm=12, md=4, lg=4, xl=4),
          ]),
          html.Br(),
          dbc.Row([
            dbc.Col([
              html.H5("Filename extension"),
              dcc.Dropdown(
                id="filter-datadict-filename_extensions",
                placeholder="all",
                multi=True,
                value=[]
              ),
            ], xs=12, sm=12, md=4, lg=4, xl=4),
            dbc.Col([
              html.H5("Model relation"),
              dcc.Dropdown(
                id="filter-datadict-relation",
                placeholder="all",
                multi=True,
                value=[]
              ),
            ], xs=12, sm=12, md=4, lg=4, xl=4),
            dbc.Col([
              html.H5("Model produced by"),
              dcc.Dropdown(
                id="filter-datadict-produced_by",
                placeholder="all",
                multi=True,
                value=[]
              ),
            ], xs=12, sm=12, md=4, lg=4, xl=4),
          ]),
          html.Br(),
          dbc.Row([
            dbc.Col([
              html.H5("Model ingested by"),
              dcc.Dropdown(
                id="filter-datadict-ingested_by",
                placeholder="all",
                multi=True,
                value=[]
              ),
            ], xs=12, sm=12, md=4, lg=4, xl=4),
            dbc.Col([
              html.H5("Model modified by"),
              dcc.Dropdown(
                id="filter-datadict-modified_by",
                placeholder="all",
                multi=True,
                value=[]
              ),
            ], xs=12, sm=12, md=4, lg=4, xl=4),
            dbc.Col([
              html.H5("Spatial (GIS)"),
              dcc.Dropdown(
                id="filter-datadict-gis",
                placeholder="all",
                multi=False,
                options=["true", "false"],
              ),
            ], xs=12, sm=12, md=4, lg=4, xl=4),
          ]),
          html.Br(),
          html.Br(),
          dbc.Row([
            html.Div([
              html.H1(id='results-title', children='Results: 0'),
            ])
          ]),
          html.Hr(),
          dbc.Row([
            dcc.Loading([
              html.Div(id='data_dict_datatable'),
              ],
              overlay_style={"visibility": "visible", "filter": "blur(2px)"},
            )
          ]),
        ], className='selection box'),
      ], xs=12, sm=12, md=12, lg=6, xl=6),
      dbc.Col([
        dbc.Row([
          html.Div([
            html.H1(id='item-name', children='Item Details'),
            html.Hr(),
            html.Pre(
              id='datadict-record-display',
              style={
                'white-space': 'pre-wrap',
                'font-family': 'monospace',
                'fontSize': '14px'
              }
            ),
          ], className='selection box'),
        ]),
        html.Br(),
        dbc.Row([
          html.Div([
            dbc.Row([
              dbc.Col([
                html.H1(id='associated-files-title', children='Associated Files: 0'),
              ], width=8),
              dbc.Col([
                html.Div([
                  dbc.ButtonGroup([
                    dbc.Button(
                      'ℹ️',
                      id='object-info-button',
                      n_clicks=0,
                      className='me-1',
                      outline=True,
                      color='secondary',
                      size='lg',
                      disabled=True
                    ),
                    dbc.Button(
                      '❌',
                      id='deselect-button',
                      n_clicks=0,
                      className='me-1',
                      outline=True,
                      color='secondary',
                      size='lg',
                      disabled=True
                    ),
                  ]),
                  dbc.Button(
                    '🗑️',
                    id='delete-button',
                    n_clicks=0,
                    className='me-1',
                    outline=True,
                    color='secondary',
                    size='lg',
                    disabled=True
                  ),
                ], className='btngroup'),
              ], width=4),
            ]),
            html.Hr(),
            dcc.Loading([
              html.Div(
                id='associated-files-table-location',
              )
            ], overlay_style={"visibility": "visible", "filter": "blur(2px)"},
            )
          ], className='selection box'),
        ]),
        html.Br(),
        dbc.Row([
          html.Div([
            dcc.Loading([
              html.Div([
                dbc.Row([
                  dbc.Col([
                    html.H1(id='upload-title', children='Upload')
                  ], width=8),
                  dbc.Col([
                    html.Div([
                      dbc.Button(
                        '⬆️',
                        id='upload-button',
                        n_clicks=0,
                        className='me-1',
                        outline=True,
                        color='secondary',
                        size='lg',
                        disabled=True
                      ),
                    ], className='btngroup')
                  ], width=4)
                ]),
                html.Hr(),
                dbc.Form([
                  dbc.Row([
                    dbc.Col([
                      dbc.Label("File Description"),
                        dbc.Textarea(
                          id='input-description',
                          placeholder="write a description of the file",
                          size="lg",
                          maxLength=1200,
                          className='me-1',
                          invalid=False,
                          style={'width': '99%', 'height': 87},
                        )
                    ], width=6),
                    dbc.Col([
                      dbc.Row([
                        dbc.Label("Tags"),
                        dcc.Dropdown(
                          id="tags-options",
                          placeholder="select tags",
                          multi=True,
                          value=[],
                        ),
                      ]),
                      html.Hr(),
                      dbc.Row([
                        dbc.Col([
                          dcc.Input(
                            id="create-tag",
                            placeholder="Create and append a new tag",
                            size="lg",
                            type='text',
                            maxLength=50,
                            className='me-1',
                            style={'width': '99%'}
                          ),
                        ], width=10),
                        dbc.Col([
                          html.Div([
                            dbc.Button(
                              id='submit-tag',
                              children='Submit',
                              n_clicks=0,
                              className='me-1',
                              outline=True,
                              color='primary',
                              size='lg',
                              disabled=False
                            )
                          ], className='btngroup')
                        ], width=2)
                      ], className='g-0')
                    ], width=6),
                  ]),
                  html.Br(),
                  dbc.Row([
                    html.Div([
                      dcc.Upload(
                        id="upload-data",
                        children=html.Div([
                          'Drag and Drop or ',
                          html.A('Select Files')
                        ]),
                        style={
                          'width': '100%',
                          'height': '100px',
                          'lineHeight': '100px',
                          'borderWidth': '1px',
                          'borderStyle': 'dashed',
                          'borderRadius': '5px',
                          'textAlign': 'center',
                          # 'margin': '10px'
                        },
                        multiple=False,
                        disabled=False,
                        accept='.txt'  # placeholder for inital call
                      ),
                    ]),
                  ]),
                ]),
                html.Div(id="loading-target-output"),
              ]),
            ],
              target_components={"loading-target-output": "children"},
              overlay_style={"visibility": "visible", "filter": "blur(2px)"},
              # type="cube"
            )
          ], className='selection box')
        ])
      ], xs=12, sm=12, md=12, lg=6, xl=6),
    ], className='g-5'),
    dbc.Modal([
      dbc.ModalHeader(
        html.H2(id='object-info-modal-title', children=['Selected Files']),
        close_button=True
      ),
      dbc.ModalBody(
        html.Div(id='object-info-modal-body', children=[
          dbc.Row([
            dbc.Col([
              html.Pre(
                id='object-info-record-display',
                style={
                  'white-space': 'pre-wrap',
                  'font-family': 'monospace',
                  'fontSize': '14px',
                  'height': '700px'
                }
              ),
            ], width=6),
            dbc.Col([
              html.Div(id='map-location', children=[
                dcc.Graph(
                  id='Map',
                  config={'scrollZoom': True},
                  style={'height': '700px'}
                )
              ], className='map'),
            ], width=6)
          ]),
        ])
      ),
      dbc.ModalFooter(
        dbc.Button(
          'Download',
          id='download-button',
          n_clicks=0,
          className='me-1',
          outline=True,
          color='primary',
          size='lg',
          disabled=False,
          # external_link=True,
          # download=""
        )
      )
    ],
      id="object-info-modal",
      size="xl",
      is_open=False,
      centered=True,
    ),
    dbc.Modal([
      dbc.ModalHeader(dbc.ModalTitle(
          "Note: You do not have permission to delete files uploaded by other users. Delete the following?"
      ), close_button=True),
      dbc.ModalBody(
        html.Div(id='delete_datatable')
      ),
      dbc.ModalFooter([
        dbc.Alert(
          id="delete-modal-alert",
          dismissable=True,
          is_open=False,
          fade=True,
          # duration=5000
        ),
        dbc.Button(
          "Delete files",
          id="yes-delete",
          className="ms-auto",
          color='danger',
          n_clicks=0,
          disabled=True,
          external_link=False
        ),
      ]),
    ],
      id="delete-modal",
      centered=True,
      is_open=False,
      size='xl'
    ),
    dbc.Modal([
      dbc.ModalHeader(html.H2(
          "Help"
      ), close_button=True),
      dbc.ModalBody(
        html.Div(children=[
          dbc.Row([
            html.Pre(
              children=
"Contact (email or Teams): daniel.bell2@ncl.ac.uk\n\n"
"For any questions or issues (e.g. access, use, downloading, uploading, deleting) "
"please get in contact. Include as much information as possible, including: a "
"description of your issue, Operating System, browser, file name, file type, "
"file size, the file itself, error message etc.\n\n"
"For technical issues you can also create an issue at:\n"
"    https://github.com/DAReHub/dare-data-store/issues\n\n"
"If you would like to contribute to the data store code you can clone and create "
"pull requests at:\n"
"    https://github.com/DAReHub/dare-data-store\n\n"
"To expand our catalogue of data please send documentation/examples of files "
"which would belong to the item. It would be helpful to include details such as: "
"the model domain, a description, its relation to the model domain (i.e. input, "
"output), the typical source and destination of the item, typical file extensions, "
"and GIS info (if any).\n\n"
"Notes:\n"
"    - Upload file size limit: 2GB\n"
"    - A file can only be deleted by the owner (the user who uploaded it), but "
"can be downloaded by any user\n"
"    - Only one file can be deleted at a time\n"
"    - File copies are retained for a short time after a file is deleted"
"\n\n:)",
              style={'white-space': 'pre-wrap', 'fontSize': '14px'}
            )
          ]),
        ])
      ),
    ],
      id="help-modal",
      centered=True,
      is_open=True,
      size='lg',
      scrollable=True,
    ),
    dbc.Toast(
      id="upload-alert",
      header='File Upload',
      dismissable=True,
      is_open=False,
      style={
        "position": "fixed",
        "top": 66,
        "right": 10,
        "width": 350,
        "font-size": "large"
      },
    ),
    dbc.Toast(
      id="info-alert",
      header='Info',
      dismissable=True,
      is_open=False,
      style={
        "position": "fixed",
        "top": 66,
        "right": 10,
        "width": 350,
        "font-size": "large"
      },
    ),
    html.Div(id="dummy-output", style={"display": "none"}),
    html.Div(id="log-output", style={"display": "none"}),
    dcc.Store(id="download-url", data=""),
    dcc.Interval(
      id='interval_pg',
      interval=1000,
      n_intervals=0,
      max_intervals=0,
    ),
  ], fluid=True)
], className='pagebody')