from flask import Blueprint, render_template, redirect, request, session, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from extensions import login_manager
import logging

import forms
import db_actions

auth_bp = Blueprint('auth', __name__)

logger = logging.getLogger(__name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = forms.LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            logger.info(f"login successful, user: {current_user.email}")
            db_actions.record_pg_logins('login', current_user.email)
            return redirect('/home')
        logger.info(f"login unsuccessful, user: {request.form['email']}")
        flash('Invalid credentials, please try again.')
    return render_template('login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    db_actions.record_pg_logins('logout', current_user.email)
    logger.info(f"logout, user: {current_user.email}")
    logout_user()
    session.clear()
    return redirect('/login')
