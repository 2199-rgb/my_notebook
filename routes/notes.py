import os
from datetime import datetime
from urllib.parse import quote

from flask import current_app, flash, redirect, render_template, request, send_file, url_for

from config import UNCATEGORIZED
from db import get_db
from services.auth import admin_required
from services.markdown_render import render_markdown
from services.note_index import (
    get_categories_list,
    get_note_index,
    invalidate_note_index_cache,
)
from services.paths import is_safe_path, move_to_trash, safe_filename
from services.search import search_notes, sync_fts_delete, sync_fts_insert


def _note_path(full_path):
    return os.path.join(current_app.config['UPLOAD_FOLDER'], full_path.replace('/', os.sep))


def register_routes(app):
    @app.route('/notes')
    def notes():
        categories = get_note_index()
        cats_sorted = get_categories_list()
        categories_list = cats_sorted

        selected = request.args.get('note')
        current_note = None

        if selected:
            fpath = _note_path(selected)
            if is_safe_path(current_app.config['UPLOAD_FOLDER'], fpath) and os.path.exists(fpath):
                mtime = os.path.getmtime(fpath)
                fname = os.path.basename(fpath)
                ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
                if ext == 'md':
                    with open(fpath, 'r', encoding='utf-8') as f:
                        md_content = f.read()
                    current_note = {
                        'title': fname.replace('.md', ''),
                        'filename': fname,
                        'full_path': selected,
                        'mtime': datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M'),
                        'html_content': render_markdown(md_content),
                        'file_type': 'md',
                        'is_markdown': True,
                    }
                else:
                    current_note = {
                        'title': fname.rsplit('.', 1)[0] if '.' in fname else fname,
                        'filename': fname,
                        'full_path': selected,
                        'mtime': datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M'),
                        'file_type': ext,
                        'is_markdown': False,
                    }

        db = get_db()
        ddls = db.execute('SELECT * FROM ddls ORDER BY target_date ASC').fetchall()

        return render_template(
            'notes.html',
            categories=categories,
            categories_order=cats_sorted,
            uncategorized_key=UNCATEGORIZED,
            categories_list=categories_list,
            current_note=current_note,
            ddls=ddls
        )

    @app.route('/notes/upload', methods=['POST'])
    @admin_required
    def upload_note():
        if 'file' not in request.files:
            flash('没有选择文件', 'error')
            return redirect(url_for('notes'))
        file = request.files['file']
        if file.filename == '':
            flash('没有选择文件', 'error')
            return redirect(url_for('notes'))

        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ('.' + ext) not in ('.md', '.pdf'):
            flash('只能上传 .md, .pdf 文件', 'error')
            return redirect(url_for('notes'))

        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        if file_size > current_app.config['MAX_CONTENT_LENGTH']:
            flash('文件大小不能超过 50MB', 'error')
            return redirect(url_for('notes'))

        category = request.form.get('category', '').strip()
        if not category or category == UNCATEGORIZED:
            category = UNCATEGORIZED

        cat_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], category.replace('/', os.sep))
        os.makedirs(cat_folder, exist_ok=True)

        filename = safe_filename(file.filename)
        if not filename:
            filename = 'note.' + ext
        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        counter = 1
        fpath = os.path.join(cat_folder, filename)
        while os.path.exists(fpath):
            filename = f'{base_name}_{counter}.{ext}'
            fpath = os.path.join(cat_folder, filename)
            counter += 1

        file.save(fpath)
        invalidate_note_index_cache()

        fts_content = ''
        if ext == 'md':
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    fts_content = f.read()
            except Exception:
                fts_content = ''

        title = filename.rsplit('.', 1)[0] if '.' in filename else filename
        sync_fts_insert((category + '/' + filename).replace('\\', '/'), title, fts_content, category)

        flash('上传成功！', 'success')
        return redirect(url_for('notes'))

    @app.route('/notes/delete', methods=['POST'])
    @admin_required
    def delete_note():
        full_path = request.form.get('filename', '')
        if not full_path:
            flash('缺少文件路径', 'error')
            return redirect(url_for('notes'))
        fpath = _note_path(full_path)
        if not is_safe_path(current_app.config['UPLOAD_FOLDER'], fpath):
            flash('非法路径', 'error')
            return redirect(url_for('notes'))
        real_path = os.path.realpath(fpath)
        if not os.path.exists(real_path):
            flash('文件不存在，可能已被删除', 'error')
            return redirect(url_for('notes'))
        try:
            sync_fts_delete(full_path)
            move_to_trash(real_path, current_app.config['UPLOAD_FOLDER'])
            invalidate_note_index_cache()
            flash('已移入回收站', 'success')
        except Exception as e:
            flash('删除失败：' + str(e), 'error')
        return redirect(url_for('notes'))

    @app.route('/add_category', methods=['POST'])
    @admin_required
    def add_category():
        name = safe_filename(request.form.get('name', ''))
        if not name:
            flash('分类名不能为空', 'error')
            return redirect(url_for('notes'))
        if name == UNCATEGORIZED:
            flash('该名称为系统保留', 'error')
            return redirect(url_for('notes'))
        cat_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], name)
        if not is_safe_path(current_app.config['UPLOAD_FOLDER'], cat_folder):
            flash('非法路径', 'error')
            return redirect(url_for('notes'))
        if os.path.exists(cat_folder) and os.path.isdir(cat_folder):
            flash('分类已存在', 'error')
            return redirect(url_for('notes'))
        try:
            os.makedirs(cat_folder, exist_ok=True)
            invalidate_note_index_cache()
            flash('分类已创建', 'success')
        except Exception as e:
            flash('创建失败：' + str(e), 'error')
        return redirect(url_for('notes'))

    @app.route('/delete_category/<category_name>', methods=['POST'])
    @admin_required
    def delete_category(category_name):
        if category_name == UNCATEGORIZED:
            flash('不能删除"未分类"', 'error')
            return redirect(url_for('notes'))
        cat_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], category_name)
        if not is_safe_path(current_app.config['UPLOAD_FOLDER'], cat_folder):
            flash('非法路径', 'error')
            return redirect(url_for('notes'))
        if not os.path.exists(cat_folder) or not os.path.isdir(cat_folder):
            flash('分类不存在', 'error')
            return redirect(url_for('notes'))

        file_count = sum(len(files) for _, _, files in os.walk(cat_folder))
        confirm_token = request.form.get('confirm_token', '')
        if file_count > 0 and confirm_token != 'DELETE':
            flash(f'该分类下有 {file_count} 篇笔记，请再次确认移入回收站', 'error')
            return redirect(url_for('notes'))

        try:
            move_to_trash(cat_folder, current_app.config['UPLOAD_FOLDER'])
            invalidate_note_index_cache()
            db = get_db()
            db.execute('DELETE FROM notes_fts WHERE category = ?', (category_name,))
            db.commit()
            flash('分类已移入回收站', 'success')
        except Exception as e:
            flash('删除失败：' + str(e), 'error')
        return redirect(url_for('notes'))

    @app.route('/create_md', methods=['POST'])
    @admin_required
    def create_md():
        filename = safe_filename(request.form.get('filename', ''))
        category = request.form.get('category', '').strip()
        if not filename:
            flash('文件名不能为空', 'error')
            return redirect(url_for('notes'))
        if not filename.endswith('.md'):
            filename += '.md'
        if not category or category == UNCATEGORIZED:
            category = UNCATEGORIZED
        cat_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], category.replace('/', os.sep))
        os.makedirs(cat_folder, exist_ok=True)
        fpath = os.path.join(cat_folder, filename)
        if os.path.exists(fpath):
            flash('文件已存在，请换个名字', 'error')
            return redirect(url_for('notes'))
        try:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write('')
            invalidate_note_index_cache()
            rel_path = (category + '/' + filename).replace('\\', '/')
            sync_fts_insert(rel_path, filename.replace('.md', ''), '', category)
            return redirect(url_for('notes', note=quote(rel_path, safe='')))
        except Exception as e:
            flash('创建失败：' + str(e), 'error')
            return redirect(url_for('notes'))

    @app.route('/download_md', methods=['GET'])
    def download_md():
        return _send_note_file(as_attachment=True)

    @app.route('/download_file', methods=['GET'])
    def download_file():
        return _send_note_file(as_attachment=True)

    @app.route('/view_file', methods=['GET'])
    def view_file():
        return _send_note_file(as_attachment=False)

    @app.route('/add_ddl', methods=['POST'])
    @admin_required
    def add_ddl():
        title = request.form.get('title', '').strip()
        target_date = request.form.get('target_date', '').strip()
        if title and target_date:
            db = get_db()
            db.execute('INSERT INTO ddls (title, target_date) VALUES (?, ?)', (title, target_date))
            db.commit()
        return redirect(url_for('notes'))

    @app.route('/delete_ddl/<int:ddl_id>', methods=['POST'])
    @admin_required
    def delete_ddl(ddl_id):
        db = get_db()
        db.execute('DELETE FROM ddls WHERE id = ?', (ddl_id,))
        db.commit()
        return redirect(url_for('notes'))

    @app.route('/api/get_raw_md', methods=['GET'])
    @admin_required
    def get_raw_md():
        full_path = request.args.get('path', '')
        if not full_path:
            return {'error': '缺少 path 参数'}, 400
        fpath = _note_path(full_path)
        if not is_safe_path(current_app.config['UPLOAD_FOLDER'], fpath):
            return {'error': '非法路径'}, 403
        if not os.path.exists(fpath):
            return {'error': '文件不存在'}, 404
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            return {'content': content}, 200
        except Exception as e:
            return {'error': str(e)}, 500

    @app.route('/api/save_md', methods=['POST'])
    @admin_required
    def save_md():
        data = request.get_json()
        full_path = data.get('path', '') if data else ''
        content = data.get('content', '') if data else ''
        if not full_path:
            return {'error': '缺少 path 参数'}, 400
        fpath = _note_path(full_path)
        if not is_safe_path(current_app.config['UPLOAD_FOLDER'], fpath):
            return {'error': '非法路径'}, 403
        if not os.path.exists(fpath):
            return {'error': '文件不存在'}, 404
        try:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(content)
            title = os.path.basename(full_path).replace('.md', '')
            if '/' in full_path:
                category = os.path.dirname(full_path).replace('\\', '/')
            else:
                category = UNCATEGORIZED
            sync_fts_insert(full_path, title, content, category)
            return {'success': True}, 200
        except Exception as e:
            return {'error': str(e)}, 500

    @app.route('/api/search', methods=['GET'])
    def search_notes_api():
        q = request.args.get('q', '').strip()
        return {'results': search_notes(q)}, 200


def _send_note_file(as_attachment):
    full_path = request.args.get('path', '')
    if not full_path:
        return '缺少 path 参数', 400
    fpath = _note_path(full_path)
    if not is_safe_path(current_app.config['UPLOAD_FOLDER'], fpath):
        return '非法路径', 403
    if not os.path.exists(fpath):
        return '文件不存在', 404
    return send_file(fpath, as_attachment=as_attachment, download_name=os.path.basename(full_path))
