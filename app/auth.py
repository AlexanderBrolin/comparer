from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('authenticated'):
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        if (username == current_app.config['LOGIN_USERNAME'] and
                password == current_app.config['LOGIN_PASSWORD']):
            session['authenticated'] = True
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid credentials', 'error')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
