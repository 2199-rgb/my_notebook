import secrets
from functools import wraps
from urllib.parse import urlparse

from flask import flash, redirect, request, session, url_for

from config import ADMIN_PASSWORD


def is_admin():
    return session.get('is_admin') is True


def is_safe_next_url(target):
    if not target:
        return False
    parsed = urlparse(target)
    return not parsed.netloc and not parsed.scheme and target.startswith('/')


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if is_admin():
            return view_func(*args, **kwargs)
        if request.path.startswith('/api/'):
            return {'error': '需要管理员登录'}, 401
        flash('请先登录管理员账号', 'error')
        return redirect(url_for('login', next=request.full_path or url_for('notes')))
    return wrapper


def password_matches(password):
    return secrets.compare_digest(password or '', ADMIN_PASSWORD)
