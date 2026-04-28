import os
from datetime import datetime

from flask import current_app, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from config import CST, HANSHIJI_PASSWORD
from db import get_db


def register_routes(app):
    @app.route('/essays')
    def essays():
        db = get_db()
        rows = db.execute('SELECT * FROM essays ORDER BY created_at DESC').fetchall()
        return render_template('essays.html', essays=rows)

    @app.route('/essays/add', methods=['POST'])
    def add_essay():
        content = request.form.get('content', '').strip()
        if not content:
            flash('内容不能为空', 'error')
            return redirect(url_for('essays'))

        author_name = request.form.get('author_name', '寒食季').strip()
        password = request.form.get('password', '').strip()

        if author_name == '寒食季':
            if not password:
                flash('使用"寒食季"发布需要密码', 'error')
                return redirect(url_for('essays'))
            if password != HANSHIJI_PASSWORD:
                flash('密码错误', 'error')
                return redirect(url_for('essays'))

        image_filename = ''
        file = request.files.get('image')
        if file and file.filename:
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)
            if file_size > current_app.config['MAX_CONTENT_LENGTH']:
                flash('图片大小不能超过 50MB', 'error')
                return redirect(url_for('essays'))
            ext = os.path.splitext(file.filename)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                sf = secure_filename(file.filename)
                timestamp = datetime.now(tz=CST).strftime('%Y%m%d%H%M%S')
                image_filename = f'{timestamp}_{sf}'
                file.save(os.path.join(current_app.config['SNIPPET_IMAGES'], image_filename))

        db = get_db()
        local_time = datetime.now(tz=CST).strftime('%Y-%m-%d %H:%M:%S')
        db.execute(
            'INSERT INTO essays (content, image_path, created_at, author_name, author_type) VALUES (?, ?, ?, ?, ?)',
            (content, image_filename, local_time, author_name, 'protected' if author_name == '寒食季' else 'public')
        )
        db.commit()
        flash('发布成功！', 'success')
        return redirect(url_for('essays'))

    @app.route('/essays/delete/<int:essay_id>', methods=['POST'])
    def delete_essay(essay_id):
        db = get_db()
        row = db.execute('SELECT image_path, author_name FROM essays WHERE id = ?', (essay_id,)).fetchone()
        if not row:
            flash('随笔不存在', 'error')
            return redirect(url_for('essays'))

        if row['author_name'] == '寒食季':
            password = request.form.get('password', '').strip()
            if not password:
                flash('删除"寒食季"的随笔需要密码', 'error')
                return redirect(url_for('essays'))
            if password != HANSHIJI_PASSWORD:
                flash('密码错误', 'error')
                return redirect(url_for('essays'))

        if row['image_path']:
            img_path = os.path.join(current_app.config['SNIPPET_IMAGES'], row['image_path'])
            if os.path.exists(img_path):
                os.remove(img_path)
        db.execute('DELETE FROM essays WHERE id = ?', (essay_id,))
        db.commit()
        flash('已删除', 'success')
        return redirect(url_for('essays'))

    @app.route('/essays/edit/<int:essay_id>', methods=['POST'])
    def edit_essay(essay_id):
        content = request.form.get('content', '').strip()
        if not content:
            return {'error': '内容不能为空'}, 400

        db = get_db()
        row = db.execute('SELECT author_name FROM essays WHERE id = ?', (essay_id,)).fetchone()
        if not row:
            return {'error': '随笔不存在'}, 404

        if row['author_name'] == '寒食季':
            password = request.form.get('password', '').strip()
            if not password:
                return {'error': '编辑寒食季的随笔需要密码'}, 403
            if password != HANSHIJI_PASSWORD:
                return {'error': '密码错误'}, 403

        db.execute('UPDATE essays SET content = ? WHERE id = ?', (content, essay_id))
        db.commit()
        return {'success': True}, 200
