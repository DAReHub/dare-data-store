import plotly.graph_objects as go
from dash import dash_table
import random
import plotly.colors as pc

import utils

def default_map():
    fig = go.Figure()
    fig.add_trace(go.Scattermapbox())
    fig.update_layout(
        autosize=True,
        margin={'t': 0, 'b': 0, 'l': 0, 'r': 0},
        mapbox={
            'style': 'carto-positron',
            'center': go.layout.mapbox.Center(
                lat=55,
                lon=-3.5
            ),
            'zoom': 4.7,
        }
    )
    return fig


def update_map(df, existing_traces, current_figure, lat, lon, zoom):
    fig = go.Figure(current_figure)

    for idx, row in df.iterrows():

        display_name = row['filename'] + ' | ' + str(row['uuid'])
        if display_name in existing_traces:
            continue

        poly = row['polygon']
        lons, lats = poly.exterior.coords.xy
        fig.add_trace(go.Scattermapbox(
            lon=list(lons),
            lat=list(lats),
            mode='lines',
            fill='toself',
            line=dict(
                width=2,
                color=pc.sample_colorscale("Viridis", random.random())[0]
            ),
            name=display_name,
            hoverinfo='text',
            hovertext=display_name,
            showlegend=True
        ))

    fig.update_layout(
        mapbox={
            'style': 'carto-positron',
            'center': go.layout.mapbox.Center(
                lat=lat,
                lon=lon
            ),
            'zoom': zoom,
        },
        legend=dict(
            x=0.01,  # x position in paper coordinates (0=left, 1=right)
            y=0.99,  # y position in paper coordinates (0=bottom, 1=top)
            xanchor="left",
            yanchor="top"
        ),
    )

    fig.update_xaxes(gridcolor='#ececec')
    fig.update_yaxes(gridcolor='#ececec')
    # Transparent background
    fig.update_layout({'plot_bgcolor': 'rgba(0, 0, 0, 0)',
                       'paper_bgcolor': 'rgba(0, 0, 0, 0)'})

    return fig


def dataDictTable(df):
    df = df[['name'] + [c for c in df.columns if c != 'name']]
    df = df[[c for c in df.columns if c != 'uuid'] + ['uuid']]
    data = [utils.convert_record(row) for row in df.to_dict('records')]
    return dash_table.DataTable(
        id='datadict-table',
        columns=[
            {'name': str(x),'id': str(x), 'deletable': False,}
            for x in df.columns
        ],
        hidden_columns=[
            'record_insert_time', 'reference_documentation', 'notes',
            'field_delimiter', 'field_types', 'field_names', 'description',
            'filename_extensions', 'produced_by', 'ingested_by', 'modified_by',
            'mime_types'
        ],
        data=data,
        editable=False,
        row_deletable=False,
        row_selectable='single',
        # filter_action="native",
        sort_action="native",
        sort_mode="single",
        page_action='native',
        page_current=0,
        page_size=22,
        style_table={'height': '700px', 'overflowY': 'auto'},
        style_header={'fontSize': '14px'},
        style_cell={
            'textAlign': 'left',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
            'maxWidth': 0,
            'fontSize': '12px'
        },
        css=[
            {  # allows table height to be configured along with style_table
                'selector': '.dash-spreadsheet.dash-freeze-top, .dash-spreadsheet.dash-virtualized',
                'rule': 'max-height: 800px;'
            },
            {  # hides the 'Toggle Columns' button which appears when using
                # hidden_columns
                'selector': '.show-hide',
                'rule': 'display: none'
            }
        ],
        tooltip_data=[
            {
                column: {'value': str(value), 'type': 'markdown'}
                for column, value in row.items()
            } for row in df.to_dict('records')
        ],
        tooltip_duration=None,
        fixed_rows={'headers': True}
    )


def associatedFilesTable(df, selected):
    df = df.drop(columns=['spatial_extents'])
    df = df[['filename'] + [c for c in df.columns if c != 'filename']]
    data = [utils.convert_record(row) for row in df.to_dict('records')]
    return dash_table.DataTable(
        id='associated-files-table',
        columns=[
            {'name': str(x), 'id': str(x), 'deletable': False,}
            for x in df.columns
        ],
        hidden_columns=[
            'status', 'deletion_time', 'model_domain', 'data_dict_uuid',
            'minio_filename', 'minio_bucket', 'description', 'size', 'gis',
            'filename_extension', 'clamav_scan'
        ],
        data=data, #df.to_dict('records'),
        editable=False,
        row_deletable=False,
        row_selectable='multi',
        selected_rows=selected,
        filter_action="native",
        sort_action="native",
        sort_mode="single",
        page_action='native',
        page_current=0,
        page_size=8,
        style_header={'fontSize': '14px'},
        style_table={
            'height': '300px',
            'overflowY': 'auto',
        },
        css=[
            {  # allows table height to be configured along with style_table
                'selector': '.dash-spreadsheet.dash-freeze-top, .dash-spreadsheet.dash-virtualized',
                'rule': 'max-height: 800px;'
            },
            {  # hides the 'Toggle Columns' button which appears when using
                # hidden_columns
                'selector': '.show-hide',
                'rule': 'display: none'
            }
        ],
        style_cell={
            'textAlign': 'left',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
            'maxWidth': 0,
            'fontSize': '12px',
        },
        tooltip_data=[
            {
                column: {'value': str(value), 'type': 'markdown'}
                for column, value in row.items()
            } for row in df.to_dict('records')
        ],
        tooltip_duration=None,
        fixed_rows={'headers': True}
    )


def deleteTable(df):
    return [
        dash_table.DataTable(
            id='delete-table',
            columns=[
                {'name': str(x), 'id': str(x), 'deletable': False}
                for x in df.columns
            ],
            hidden_columns=[
                'status', 'deletion_time', 'model_domain', 'data_dict_uuid',
                'minio_filename', 'minio_bucket', 'description', 'size', 'gis',
                'filename_extension', 'clamav_scan'
            ],
            data=df.to_dict('records'),
            editable=False,
            row_deletable=False,
            sort_action="native",
            sort_mode="single",
            page_action='none',
            style_table={'height': '300px', 'overflowY': 'auto'},
            style_cell={
                'textAlign': 'left',
                'overflow': 'hidden',
                'textOverflow': 'ellipsis',
                'maxWidth': 0,
            },
            css=[
                {  # hides the 'Toggle Columns' button which appears when using
                    # hidden_columns
                    'selector': '.show-hide',
                    'rule': 'display: none'
                }
            ],
            tooltip_data=[
                {column: {'value': str(value), 'type': 'markdown'}}
                for row in df.to_dict('records')
                for column, value in row.items()
            ],
            tooltip_duration=None,
            fixed_rows={'headers': True}
        ),
    ]