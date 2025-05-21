from flask import Flask, session, redirect, render_template
from flask_login import logout_user
from flask_wtf.csrf import CSRFProtect, CSRFError, generate_csrf
from flask_talisman import Talisman
from config import Config
from extensions import db, login_manager
from auth import auth_bp
from minio_routes import minio_bp
from datetime import datetime, timezone

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    csrf = CSRFProtect(app)
    csrf._exempt_views.add('dash.dash.dispatch')

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = '/login'

    csp = {
        'default-src': ["'self'"],
        'script-src': [
            "'self'",
            "'sha256-jZlsGVOhUAIcH+4PVs7QuGZkthRMgvT2n0ilH6/zTM0='",
            "'sha256-20FwRg9o1k6YUFNC1byjqt5wIFUmmeoosMZCSCwKkPw='",
        ],
        'script-src-elem': ["'self'", "'unsafe-inline'"],
        'style-src': [
            "'self'",
            "https://cdn.jsdelivr.net",
            "maxcdn.bootstrapcdn.com",
        ],
        'style-src-elem': [
            "'self'",
            "'unsafe-inline'",
            "https://cdn.jsdelivr.net",
            "maxcdn.bootstrapcdn.com",
        ],
        'img-src': [
            "'self'",
            "data:",
            "https://cartodb-basemaps-c.global.ssl.fastly.net"
        ],
        'connect-src': [
            "'self'",
            "ws://*",
            "wss://*",
            "https://dash-version.plotly.com:8080",
            "https://cartodb-basemaps-c.global.ssl.fastly.net"
        ],
        'worker-src': ["blob:"]
    }
    Talisman(
        app,
        content_security_policy=csp,
        content_security_policy_nonce_in=['script-src'],
        force_https=True,
        session_cookie_secure=True,
        session_cookie_http_only=True,
    )

    app.register_blueprint(auth_bp)
    app.register_blueprint(minio_bp)

    # Logs the user out after inactivity
    @app.before_request
    def session_timeout():
        session.permanent = True
        now = datetime.now(timezone.utc)
        last_activity = session.get('last_activity')
        if last_activity:
            elapsed = now - last_activity
            if elapsed > app.config['PERMANENT_SESSION_LIFETIME']:
                logout_user()
                session.clear()
                return redirect('/login?timeout=1')
        session['last_activity'] = now

    # prevents being able to use back button to return after logging out
    @app.after_request
    def add_header(response):
        response.headers[
            'Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    @app.after_request
    def add_security_headers(response):
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return render_template('csrf_error.html', reason=e.description), 400

    return app
