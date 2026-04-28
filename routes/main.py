from flask import flash, jsonify, redirect, render_template, request, session, url_for

from config import APP_PORT
from services.auth import is_safe_next_url, password_matches
from services.network import get_lan_ip


def register_routes(app):
    @app.route('/')
    def home():
        return render_template('home.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        next_url = request.values.get('next') or url_for('notes')
        if not is_safe_next_url(next_url):
            next_url = url_for('notes')

        if request.method == 'POST':
            password = request.form.get('password', '')
            if password_matches(password):
                session['is_admin'] = True
                flash('已进入管理模式', 'success')
                return redirect(next_url)
            flash('管理员密码错误', 'error')

        return render_template('login.html', next_url=next_url)

    @app.route('/logout', methods=['POST'])
    def logout():
        session.pop('is_admin', None)
        flash('已退出管理模式', 'success')
        next_url = request.form.get('next') or url_for('notes')
        if not is_safe_next_url(next_url):
            next_url = url_for('notes')
        return redirect(next_url)

    @app.route('/api/get_lan_ip', methods=['GET'])
    def get_lan_ip_api():
        return jsonify({'ip': get_lan_ip(), 'port': APP_PORT}), 200
