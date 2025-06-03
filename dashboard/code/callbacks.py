import os
from dash.dependencies import Input, Output, State
from dash import ctx, html, no_update, callback_context, ClientsideFunction, clientside_callback
from dash.exceptions import PreventUpdate
import pandas as pd
import json
import requests
import io
from geoalchemy2.shape import to_shape
from flask import current_app, request, session
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone
import time
import uuid
import logging
import bleach

import figures
import utils
from utils import csrf_protected
import geo_ingestion
import db_actions
from models import *
import minio_routes

from flask_login import current_user
from flask_login import login_required
from extensions import db

from dotenv import load_dotenv
load_dotenv()

MODELS_BUCKET = os.getenv('MINIO_MODEL_BUCKET')

logger = logging.getLogger(__name__)


def register_callbacks(app):

    @app.callback(
        Output('url', 'pathname'),
        Input('url', 'pathname'),
    )
    def secure_dashboard(pathname):
        if not current_user.is_authenticated:
            return '/login'
        return pathname


    @app.callback(
        Output('results-title', 'children'),
        Input('datadict-table', 'data'))
    def update_results_title(data):
        return f"Results: {str(len(data))}"


    @app.callback(
        Output('object-info-button', 'children'),
        Input('associated-files-table', 'selected_rows'),
        prevent_initial_call=True)
    def update_download_title(selected):
        return f"ℹ️ {str(len(selected))}"


    @app.callback(
        Output("object-info-button", "disabled"),
        Output("deselect-button", "disabled"),
        Output("delete-button", "disabled"),
        Output("object-info-button", "color"),
        Output("deselect-button", "color"),
        Output("delete-button", "color"),
        Input('associated-files-table', 'selected_rows'),
        prevent_initial_call=True
    )
    def activate_selection_buttons(selected):
        if selected is None or selected == []:
            return True, True, True, 'secondary', 'secondary', 'secondary'
        if len(selected) == 1:
            return False, False, False, 'primary', 'primary', 'danger'
        # only allow delete button for one file at a time
        elif len(selected) > 1:
            return False, False, True, 'primary', 'primary', 'secondary'
        return True, True, True, 'secondary', 'secondary', 'secondary'


    @app.callback(
        Output("delete-modal", 'is_open'),
        Output('delete_datatable', 'children'),
        Input('delete-button', 'n_clicks'),
        State('associated-files-table', 'selected_rows'),
        State('associated-files-table', 'data'),
        prevent_initial_call=True,
    )
    def delete_datatable(n, selected, data):
        if not selected:
            return no_update, no_update
        selected = [data[i] for i in selected]
        df = pd.DataFrame(selected)
        df = df.loc[df['owner'] == current_user.email]
        return True, figures.deleteTable(df)


    @app.callback(
        Output('delete-modal-alert', 'children'),
        Output('delete-modal-alert', 'color'),
        Output('delete-modal-alert', 'is_open'),
        Input('yes-delete', 'n_clicks'),
        State('delete-table', 'data'),
        State('csrf-store', 'data'),
        prevent_initial_call=True
    )
    @login_required
    @csrf_protected
    def delete_files(n, data, csrf_token):
        logger.debug(
            f"delete_files: callback triggered, user: {current_user.email}, trigger: {ctx.triggered_id}"
        )

        data = data[0]
        if data['owner'] != current_user.email:
            logger.info(
                f"delete_files: owner does not match current user, user: {current_user.email}, owner: {data['owner']}, object: {data['minio_filename']}, bucket: {data['minio_bucket']}"
            )
            return "You can only delete files belonging to yourself", "danger", True

        bucket = data['minio_bucket']
        object = data['minio_filename']
        uuid = data['uuid']
        minio_filename = data['minio_filename']

        # confirm and get user login details for request
        try:
            dash_session = requests.Session()
            # if 'session' in request.cookies:
            dash_session.cookies.set('session', request.cookies['session'])
        except Exception as e:
            logger.error(
                f"delete_files: user session issue, user: {current_user.email}, exception: {e}"
            )
            return "User session not found", "danger", True

        try:
            minio_routes.minio_tag(bucket, object, 'delete_scheduled', 'true')
            t = datetime.utcnow() + timedelta(days=7)
            db_actions.update_object_status(uuid, 'deletion_scheduled', t)
            db_actions.record_pg_deletes(
                current_user.email, [uuid], t, minio_filename
            )
            logger.info(
                f"delete_files: successful delete, user: {current_user.email}, bucket: {bucket}, object: {minio_filename}"
            )
            return f"Successfully deleted {data['filename']}", "success", True
        except Exception as e:
            logger.error(
                f"delete_files: exception when trying to delete file, user: {current_user.email}, exception: {e}, bucket: {bucket}, object: {minio_filename}"
            )
            return f"Error. Please try again later", "danger", True


    @app.callback(
        Output('yes-delete', 'disabled'),
        Input('delete-table', 'data'),
        prevent_initial_call=True
    )
    def activate_yes_delete(delete_table):
        if delete_table is None or len(delete_table) == 0:
            return True
        delete_table = delete_table[0]
        if delete_table['owner'] != current_user.email:
            return True
        return False


    @app.callback(
        Output('associated-files-table', 'selected_rows'),
        Input('delete-button', 'n_clicks'),
        Input('download-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def uncheck_table(n1, n2):
        return []


    @app.callback(
        Output('object-info-modal', 'is_open'),
        Output('object-info-record-display', 'children'),
        Input('object-info-button', 'n_clicks'),
        State('associated-files-table', 'selected_rows'),
        State('associated-files-table', 'data'),
        prevent_initial_call=True
    )
    def object_info_modal(n, selected_rows, data):
        data = [data[i] for i in selected_rows]
        keys_to_keep = {
            'filename', 'uuid', 'model_domain', 'description',
            'filename_extension', 'data_dict_uuid', 'owner', 'gis', 'size',
            'tags', 'record_insert_time'
        }
        data = [
            {k: v for k, v in item.items() if k in keys_to_keep}
            for item in data
        ]
        text = json.dumps(data, indent=2)
        text = bleach.clean(text)
        return True, text


    @app.callback(
        Output('Map', 'figure'),
        Input('associated-files-table', 'selected_rows'),
        State('associated-files-table', 'data'),
        State('Map', 'figure'),
        prevent_initial_call=True)
    def render_map(pg_selected, pg_data, current_figure):
        if pg_selected is None or len(pg_selected) == 0:
            return figures.default_map()

        selected = [pg_data[i] for i in pg_selected]
        df = pd.read_sql_table('object_store_metadata', con=db.engine)
        df = df.loc[df['uuid'].astype(str).isin([d["uuid"] for d in selected])]
        df['polygon'] = df['spatial_extents'].apply(lambda geom: to_shape(geom) if geom is not None else None)
        df = df.dropna(subset=['polygon'])

        if df.empty:
            return figures.default_map()

        trace_names, current_figure = utils.update_map_traces(df, current_figure)
        lat, lon, zoom = utils.calculate_map_zoom_and_position(df)
        return figures.update_map(df, trace_names, current_figure, lat, lon, zoom)


    @app.callback(
        Output("size-estimation", "children"),
        Input("associated-files-table", "selected_rows"),
        State("associated-files-table", "data"),
    )
    def estimated_download_size(selected_rows, data):
        data = [data[i] for i in selected_rows]
        size = sum(item['size'] for item in data)
        return f"Estimated size: {utils.format_size(size)}"


    @app.callback(
        Output("download-button", "children"),
        Output("download-button", "disabled"),
        Output("download-button", "color"),
        Input("associated-files-table", "selected_rows"),
        State("associated-files-table", "data"),
        prevent_initial_call=True
    )
    def download_button_look(selected_rows, data):
        data = [data[i] for i in selected_rows]
        if 0 < len(data) <= 10:
            size = sum(item['size'] for item in data)
            return f"Download ({utils.format_size(size)})", False, "primary"
        elif len(data) > 10:
            return "Download MAXIMUM EXCEEDED (10 Files)", True, "secondary"
        else:
            return "Download 0B", True, "secondary"


    @app.callback(
        Output("download-url", "data"),
        Input('download-button', 'n_clicks'),
        State("associated-files-table", "selected_rows"),
        State("associated-files-table", "data"),
        State('csrf-store', 'data'),
        prevent_initial_call=True)
    @login_required
    @csrf_protected
    def download(n, selected_rows, data, csrf_token):
        if selected_rows is None:
            return no_update

        data = [data[i] for i in selected_rows]

        if len(data) == 1:
            bucket = data[0]['minio_bucket']
            object = data[0]['minio_filename']
            files = bucket + '/' + object
            token = db_actions.generate_one_time_token('download_file', files)
            path = f"bucket={bucket}&object={object}"
            return f"/download_file?{path}&token={token}"

        elif len(data) > 1:
            files = [item['minio_bucket'] + '/' + item['minio_filename'] for
                     item in data]
            files = ",".join(files)
            token = db_actions.generate_one_time_token('download_zip', files)
            return f"/download_zip?files={files}&token={token}"

        else:
            return ""


    # Openining the download url directly from download-button redirects the
    # user and prevents insert_download_record from being triggered. Now,
    # download-button passes the url to download-url store (which triggers this
    # clientside callback, automatically opening the url for the user), as well
    # as insert_download_record
    app.clientside_callback(
        """
        function(url, n_clicks) {
            if (n_clicks > 0 && url) {
                window.open(url, "_blank");
            }
            return "";
        }
        """,
        Output("dummy-output", "children"),
        Input("download-url", "data"),
        State("download-button", "n_clicks"),
    )


    @app.callback(
        Output("log-output", "children"),
        Input("download-button", "n_clicks"),
        State('associated-files-table', 'selected_rows'),
        State('associated-files-table', 'data'),
        State('csrf-store', 'data'),
        prevent_initial_call=True)
    @login_required
    @csrf_protected
    def insert_download_record(n, selected_rows, data, csrf_token):
        logger.debug(
            f"insert_download_record: callback triggered, user: {current_user.email}, trigger: {ctx.triggered_id}"
        )
        data = [data[i] for i in selected_rows]
        df = pd.DataFrame(data)
        file_uuids = df['uuid'].tolist()
        filenames = df['minio_filename'].tolist()
        db_actions.record_pg_downloads(
            current_user.email, file_uuids, len(file_uuids), filenames
        )
        logger.debug(
            f"insert_download_record: recorded downloaded item(s), user: {current_user.email}, filenames: {', '.join(filenames)}, file UUIDs: {', '.join(file_uuids)}"
        )
        return no_update


    @app.callback(
        Output('filter-datadict-model_domain', 'options'),
        Input('interval_pg', 'n_intervals'))
    def filter_5(n):
        df = pd.read_sql_table('model_data_dictionary', con=db.engine)
        return sorted(list(set(df['model_domain'].dropna())))


    @app.callback(
        Output('filter-datadict-filename_extensions', 'options'),
        Input('interval_pg', 'n_intervals'))
    def filter_6(n):
        df = pd.read_sql_table('model_data_dictionary', con=db.engine)
        return sorted(list(set(item for col in df['filename_extensions'].dropna() for item in col)))


    @app.callback(
        Output('filter-datadict-relation', 'options'),
        Input('interval_pg', 'n_intervals'))
    def filter_7(n):
        df = pd.read_sql_table('model_data_dictionary', con=db.engine)
        return sorted(list(set(df['relation_type'].dropna())))


    @app.callback(
        Output('filter-datadict-produced_by', 'options'),
        Input('interval_pg', 'n_intervals'))
    def filter_8(n):
        df = pd.read_sql_table('model_data_dictionary', con=db.engine)
        return sorted(list(set(item for col in df['produced_by'].dropna() for item in col)))


    @app.callback(
        Output('filter-datadict-ingested_by', 'options'),
        Input('interval_pg', 'n_intervals'))
    def filter_9(n):
        df = pd.read_sql_table('model_data_dictionary', con=db.engine)
        return sorted(list(set(item for col in df['ingested_by'].dropna() for item in col)))


    @app.callback(
        Output('filter-datadict-modified_by', 'options'),
        Input('interval_pg', 'n_intervals'))
    def filter_10(n):
        df = pd.read_sql_table('model_data_dictionary', con=db.engine)
        return sorted(list(set(item for col in df['modified_by'].dropna() for item in col)))


    @app.callback(
        Output('filter-datadict-name', 'value'),
        Output('filter-datadict-uuid', 'value'),
        Output('filter-datadict-model_domain', 'value'),
        Output('filter-datadict-filename_extensions', 'value'),
        Output('filter-datadict-relation', 'value'),
        Output('filter-datadict-produced_by', 'value'),
        Output('filter-datadict-ingested_by', 'value'),
        Output('filter-datadict-modified_by', 'value'),
        Output('filter-datadict-gis', 'value'),
        Output('datadict-table', 'selected_rows'),
        Output('datadict-apply-filters', 'n_clicks'),
        Input('datadict-remove-filters', 'n_clicks'),
        prevent_initial_call=True)
    def remove_datadict_filters(n):
        return "", "", [], [], [], [], [], [], [], [], 0


    @app.callback(
        Output('data_dict_datatable', 'children'),
        Input('datadict-apply-filters', 'n_clicks'),
        State('filter-datadict-name', 'value'),
        State('filter-datadict-uuid', 'value'),
        State('filter-datadict-model_domain', 'value'),
        State('filter-datadict-filename_extensions', 'value'),
        State('filter-datadict-relation', 'value'),
        State('filter-datadict-produced_by', 'value'),
        State('filter-datadict-ingested_by', 'value'),
        State('filter-datadict-modified_by', 'value'),
        State('filter-datadict-gis', 'value'),
        State('csrf-store', 'data'),
    )
    @login_required
    @csrf_protected
    def populate_datadict_datatable(n, name_val, uuid_val, model_domain_val, filename_extensions_val, relation_val, produced_by_val, ingested_by_val, modified_by_val, gis_val, csrf_token):
        name_val = bleach.clean(name_val) if name_val else None
        uuid_val = bleach.clean(uuid_val) if uuid_val else None

        df = pd.read_sql_table('model_data_dictionary', con=db.engine)
        df = df[df['filename_extensions'].notna()]
        df = df[df['mime_types'].notna()]

        if name_val is not None:
            df = df[df['name'].str.contains(name_val, case=False, na=False)]
        if uuid_val is not None:
            df = df[df['uuid'].astype(str).str.contains(uuid_val, case=False, na=False)]
        if len(model_domain_val) > 0:
            df = df.loc[df['model_domain'].isin(model_domain_val)]
        if len(filename_extensions_val) > 0:
            df = utils.filter_df_list(df, 'filename_extensions', filename_extensions_val)
        if len(relation_val) > 0:
            df = df.loc[df['relation_type'].isin(relation_val)]
        if len(produced_by_val) > 0:
            df = utils.filter_df_list(df, 'produced_by', produced_by_val)
        if len(ingested_by_val) > 0:
            df = utils.filter_df_list(df, 'ingested_by', ingested_by_val)
        if len(modified_by_val) > 0:
            df = utils.filter_df_list(df, 'modified_by', modified_by_val)
        if gis_val:
            if gis_val == 'true':
                bool_val = True
            elif gis_val == 'false':
                bool_val = False
            df = df.loc[df['gis'] == bool_val]

        return figures.dataDictTable(df)


    @app.callback(
        Output('datadict-record-display', 'children'),
        Output('item-name', 'children'),
        Input('datadict-table', 'selected_rows'),
        State('datadict-table', 'data'),
    )
    def datadictRecordDisplay(selected_rows, data):
        if selected_rows is None or selected_rows == []:
            return "Select a catalogue record for detialed information and available options", "Item Details"
        data = data[selected_rows[0]]
        text = ""
        for key, value in data.items():
            if key in ["name", "record_insert_time"]:
                continue
            text += f"{key}: {value}\n"
        text = bleach.clean(text)
        name = bleach.clean(data['name'])
        return text, name


    @app.callback(
        Output('associated-files-title', 'children'),
        Output('associated-files-table-location', 'children'),
        Input('yes-delete', 'n_clicks'),
        Input('upload-alert', 'is_open'),
        Input('datadict-table', 'selected_rows'),
        Input('deselect-button', 'n_clicks'),
        State('datadict-table', 'data'),
        prevent_initial_call=True)
    def associatedFilesTable(n_delete, upload_alert, selected_rows, deselect, data):
        if 'yes-delete' == ctx.triggered_id or 'upload-alert' == ctx.triggered_id:
            # wait a moment for db to update before refreshing
            time.sleep(3)
        selected = []
        if selected_rows is None or selected_rows == []:
            return 'Associated Files: 0', []
        data = data[selected_rows[0]]
        uuid = UUID(data['uuid'])
        q = (
            db.session.query(Objects)
            .filter(Objects.data_dict_uuid == uuid)
            .filter(Objects.status == 'active')
        )
        df = pd.read_sql_query(
            sql=q.statement,
            con=db.engine
        )
        return f'Associated Files: {len(df)}', figures.associatedFilesTable(df, selected)


    @app.callback(
        Output('tags-options', 'options'),
        Output('tags-options', 'value'),
        Output('create-tag', 'value'),
        Input('submit-tag', 'n_clicks'),
        Input('interval_pg', 'n_intervals'),
        State('tags-options', 'value'),
        State('create-tag', 'value'),
    )
    def submit_tag(n_clicks, n_intervals, value, tag_text):
        tag_text = bleach.clean(tag_text) if tag_text else None
        df = pd.read_sql_table('tags', con=db.engine)
        tags = df['tag'].tolist()
        options = []
        for tag in tags:
            options.append({'label': tag, 'value': tag})
        if 'submit-tag' != ctx.triggered_id:
            return options, value, no_update
        if tag_text is None or len(tag_text) == 0:
            return options, no_update, no_update
        if any(d.get('value') == tag_text for d in options):
            if value is None:
                return options, [tag_text], ""
            elif tag_text not in value:
                value.append(tag_text)
                return options, value, ""
            return no_update, no_update, ""
        db_actions.add_tag(current_user.email, tag_text)
        options.append({'label': tag_text, 'value': tag_text})
        value.append(tag_text)
        return options, value, ""


    @app.callback(
        Output('upload-data', 'children'),
        Input('upload-data', 'filename'),
        prevent_initial_call=True)
    def upload_name_contents(filename):
        if filename is not None:
            return f"Selected: {filename}"
        return html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ])


    @app.callback(
        Output("upload-button", "disabled"),
        Output('upload-button', 'color'),
        Input('upload-data', 'filename'),
        Input('datadict-table', 'selected_rows'),
        prevent_initial_call=True)
    def enable_upload_button(filename, selected_rows):
        if selected_rows is None:
            return True, 'secondary'
        if filename is not None and len(selected_rows) > 0:
            return False, 'primary'
        return True, 'secondary'


    @app.callback(
        Output('info-alert', 'children'),
        Output('info-alert', 'icon'),
        Output('info-alert', 'is_open'),
        Input('datadict-table', 'selected_rows'),
        State('datadict-table', 'data'),
        prevent_initial_call=True)
    def info_toast(selected, data):
        if not selected:
            return no_update, no_update, no_update
        data = data[selected[0]]
        if 'shp' in data['filename_extensions']:
            return "Shapefiles must be uploaded as a .zip file. For successful extraction of spatial extents it must contain at least one of each: '.shp', '.shx', '.dbf', '.prj'", 'info', True
        return "", no_update, False


    @app.callback(
        Output('upload-alert', 'children'),
        Output('upload-alert', 'icon'),
        Output('upload-alert', 'is_open'),
        Output("loading-target-output", "children"),
        Input("upload-button", "n_clicks"),
        State('upload-data', 'contents'),
        State('upload-data', 'filename'),
        State('datadict-table', 'data'),
        State('datadict-table', 'selected_rows'),
        State('input-description', 'value'),
        State('tags-options', 'value'),
        State('csrf-store', 'data'),
        prevent_initial_call=True)
    @login_required
    @csrf_protected
    def handle_upload(n, contents, filename, data, selected_rows, description, selected_tags, csrf_token):
        logger.debug(
            f"handle_upload: callback triggered, user: {current_user.email}, trigger: {ctx.triggered_id}"
        )

        # confirm and get user login details for request
        try:
            dash_session = requests.Session()
            # if 'session' in request.cookies:
            dash_session.cookies.set('session', request.cookies['session'])
        except Exception as e:
            logger.error(
                f"handle_upload: user session issue, user: {current_user.email}"
                f", exception: {e}"
            )
            return f"Upload of '{filename}' failed: User session not found", "danger", True, None

        if contents is None:
            logger.debug(
                f"handle_upload: no file in upload, user: {current_user.email}"
            )
            return "No file uploaded yet.", "warning", False, None

        filename = bleach.clean(filename) if filename else None
        filename = secure_filename(filename)
        description = bleach.clean(description) if description else None

        user = current_user.email
        tags = selected_tags if len(selected_tags) != 0 else None
        extents = None
        spatial_property = False
        geo_failed = False
        clamav_scan = "succeeded"
        unique_id = uuid.uuid4()

        data = [data[i] for i in selected_rows][0]
        dict_extension = data['filename_extensions']
        upload_extension = filename.split(".")[-1]
        mime_type = data['mime_types']
        minio_filename = f"{data['uuid']}/{str(unique_id)}/{filename}"
        decoded = utils.decode(contents)
        io_decoded = io.BytesIO(decoded)
        length = len(decoded)

        try:
            utils.validate_extension(dict_extension, filename)
            detected_mime = utils.validate_mime(mime_type, io_decoded)
            logger.info(f"security checks passed, user: {current_user.email}")
        except Exception as e:
            logger.info(f"security check exception: {str(e)}")
            return f"Upload of '{filename}' failed: {str(e)}", "danger", True, None

        # todo: fix errors and add to other security checks try block above
        try:
            if c := utils.clamav_scanner(io_decoded):
                return c, "danger", True, None
        except Exception as e:
            logger.error(
                f"upload_file: ClamAV exception, exception: {str(e)}"
            )
            clamav_scan = f"exception: {str(e)}"

        if data['gis'] is True and dict_extension != 'asc':
            try:
                extents = geo_ingestion.main(filename, decoded)
                spatial_property = True
            except Exception as e:
                logger.warning(
                    f"handle_upload: spatial extraction exception, user: {current_user.email}, exception: {e}, decoded length: {length}, catalogue UUID: {data['uuid']}"
                )
                geo_error = e
                geo_failed = True
                if str(e) == "Extension not allowed":
                    return f"Upload of '{filename}' failed: .zip contains a file which is not allowed", "danger", True, None

        try:
            minio_routes.upload_file(minio_filename, io_decoded, detected_mime)
            logger.info(
                f"upload_file success, bucket={MODELS_BUCKET}, object={filename}"
            )
        except Exception as e:
            logger.error(
                f"upload_file exception, bucket={MODELS_BUCKET}, "
                f"object={filename}, exception={e}"
            )
            return f"Upload of '{filename}' failed: Upload to database error", "danger", True, None

        try:
            minio_routes.check_file_exists(MODELS_BUCKET, minio_filename)
            logger.info(
                f"check_file_exists success, bucket: {MODELS_BUCKET}, "
                f"object: {filename}"
            )
        except Exception as e:
            logger.error(
                f"check_file_exists exception, bucket: {MODELS_BUCKET}, "
                f"object: {filename}, exception: {e}"
            )
            return f"Upload of '{filename}' failed: File not confirmed in database", "danger", True, None

        db.session.add(Objects(
            uuid=unique_id,
            filename=filename,
            model_domain=data['model_domain'],
            description=description,
            filename_extension=upload_extension,
            data_dict_uuid=UUID(data['uuid']),
            owner=user,
            gis=spatial_property,
            spatial_extents=extents,
            size=length,
            tags=tags,
            minio_filename=minio_filename,
            minio_bucket=MODELS_BUCKET,
            status="active",
            clamav_scan=clamav_scan
        ))
        db.session.commit()
        db_actions.record_pg_uploads(user, minio_filename, length)

        logger.info(
            f"handle_upload: upload successful, user: {current_user.email}, bucket: {MODELS_BUCKET}, object: {minio_filename}, decoded length: {length}, catalogue UUID: {data['uuid']}"
        )

        if geo_failed is True:
            return f"Upload of '{filename}' successful, but failed to extract spatial extents: {geo_error}", "warning", True, None

        return f"Upload of '{filename}' successful", "success", True, None


    @app.callback(
        Output('input-description', 'value'),
        Output('upload-data', 'filename'),
        Output('upload-data', 'contents'),
        Input('upload-alert', 'icon'),
        Input('datadict-table', 'selected_rows'),
        prevent_initial_call=True)
    def reset_upload_components(alert_state, selected):
        if 'upload-alert' == ctx.triggered_id:
            if alert_state == "success":
                return "", None, None
            else:
                return no_update, no_update, no_update
        elif 'datadict-table' == ctx.triggered_id:
            return no_update, None, None


    @app.callback(
        Output('upload-data', 'accept'),
        Input('datadict-table', 'selected_rows'),
        State('datadict-table', 'data'),
        prevent_initial_call=True
    )
    def upload_accepts(selected_rows, data):
        if not selected_rows:
            return no_update
        data = data[selected_rows[0]]
        extension = '.' + data['filename_extensions'].split(".")[-1]
        if extension == '.shp':
            extension = '.zip'
        return extension


    @app.callback(
        Output('help-modal', 'is_open'),
        Input('help-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def show_help(n):
        return True