from flask import Blueprint, render_template, redirect, url_for, session, flash
from flask_login import login_required, logout_user
from project.utils.session import SessionKeys

auth = Blueprint('auth', __name__)

@auth.route("/logout")
@login_required
def logout():
    session[SessionKeys.USER_TYPE.value] = None
    flash('User successfully logged out', category='success')
    logout_user()
    return redirect(url_for('views.index'))
