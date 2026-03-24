import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import re
import shutil
import socket
import sqlite3
import markdown
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime


def get_lan_ip():
    """获取本机局域网IP地址（用于移动设备扫码访问）"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # 降级：遍历网卡获取
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            # 排除回环地址
            if ip.startswith("127."):
                for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
                    addr = info[4][0]
                    if not addr.startswith("127."):
                        return addr
            return ip
        except Exception:
            return "127.0.0.1"

try:
    import bleach
    BLEACH_AVAILABLE = True
except ImportError:
    BLEACH_AVAILABLE = False


def is_safe_path(base_dir, target_path):
    """防止路径遍历：确保 resolved path 在 base_dir 内部，不受 junction/symlink 影响。"""
    try:
        real_base = os.path.realpath(base_dir)
        real_target = os.path.realpath(target_path)
        # os.path.commonpath 在跨盘符时抛 ValueError，用 startswith 兜底
        common = os.path.commonpath([real_base, real_target])
        return common == real_base
    except (ValueError, TypeError):
        # 跨盘符等罕见情况，降级为 startswith 检查
        return os.path.realpath(target_path).startswith(os.path.realpath(base_dir))


def _render_markdown(content):
    """将 Markdown 转为 HTML，并清除危险标签（防 XSS）。"""
    html = markdown.markdown(content, extensions=['fenced_code', 'tables'])
    if BLEACH_AVAILABLE:
        allowed_tags = [
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'p', 'br', 'hr',
            'ul', 'ol', 'li',
            'blockquote', 'pre', 'code',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'a', 'img',
            'strong', 'em', 'del', 'sup', 'sub',
            'div', 'span',
        ]
        allowed_attrs = {
            'a': ['href', 'title'],
            'img': ['src', 'alt', 'title'],
            'code': ['class'],
            'pre': ['class'],
            'th': ['align'],
            'td': ['align'],
            'div': ['class'],
            'span': ['class'],
        }
        html = bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs, strip=True)
    return html

# 解决 PythonAnywhere 工作目录不一致问题，强制基于 app.py 所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'my-secret-key-2024')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['SNIPPET_IMAGES'] = os.path.join(BASE_DIR, 'static', 'snippet_images')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['SNIPPET_IMAGES'], exist_ok=True)

DB_NAME = os.path.join(BASE_DIR, 'blog.db')

# ===== 分类系统常量与工具 =====
UNCATEGORIZED = '未分类'  # 唯一的默认分类目录名

def ensure_uncategorized():
    """确保未分类目录存在"""
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], UNCATEGORIZED), exist_ok=True)

def get_categories_list():
    """扫描 uploads/ 下的真实子文件夹作为分类列表（未分类永远在最后）"""
    ensure_uncategorized()
    subs = []
    for item in os.listdir(app.config['UPLOAD_FOLDER']):
        path = os.path.join(app.config['UPLOAD_FOLDER'], item)
        if os.path.isdir(path) and item != UNCATEGORIZED:
            subs.append(item)
    subs.sort()
    subs.append(UNCATEGORIZED)
    return subs


def _sync_fts_insert(rel_path, title, content, category):
    """向 FTS 表插入（或替换）一条记录"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO notes_fts (path, title, content, category) VALUES (?, ?, ?, ?)',
              (rel_path, title, content, category))
    conn.commit()
    conn.close()


def _sync_fts_delete(rel_path):
    """从 FTS 表删除一条记录"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM notes_fts WHERE path = ?', (rel_path,))
    conn.commit()
    conn.close()


def _build_snippet(content, keyword, radius=80):
    """从正文中提取含关键词的摘要片段，关键词用 <mark> 包裹"""
    if not content:
        return ''
    if not keyword:
        return content[:radius * 2] + ('...' if len(content) > radius * 2 else '')

    lower_content = content.lower()
    lower_kw = keyword.lower()
    pos = lower_content.find(lower_kw)

    if pos == -1:
        # 找不到关键词，退化为截取开头
        return content[:radius * 2] + ('...' if len(content) > radius * 2 else '')

    start = max(0, pos - radius)
    end = min(len(content), pos + len(keyword) + radius)
    snippet = content[start:end]

    # 判断是否被截断
    prefix = '...' if start > 0 else ''
    suffix = '...' if end < len(content) else ''
    snippet = prefix + snippet + suffix

    # 用正则把原文中的关键词替换为 <mark> 包裹版本（大小写不敏感）
    def mark_replace(m):
        return '<mark>' + m.group(0) + '</mark>'

    escaped_kw = re.escape(keyword)
    snippet = re.sub(escaped_kw, mark_replace, snippet, flags=re.IGNORECASE)
    return snippet

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS essays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            image_path TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # 兼容旧数据库：若无 image_path 列则新增
    try:
        c.execute('ALTER TABLE essays ADD COLUMN image_path TEXT DEFAULT ""')
    except sqlite3.OperationalError:
        pass
    # 兼容旧数据库：若无 author_name / author_type 列则新增
    try:
        c.execute('ALTER TABLE essays ADD COLUMN author_name TEXT DEFAULT "寒食季"')
    except sqlite3.OperationalError:
        pass
    try:
        c.execute('ALTER TABLE essays ADD COLUMN author_type TEXT DEFAULT "protected"')
    except sqlite3.OperationalError:
        pass
    # 兼容旧数据：为已有随笔填充 author_name（之前的行该列为 NULL）
    c.execute("UPDATE essays SET author_name = '寒食季' WHERE author_name IS NULL OR author_name = ''")
    c.execute("UPDATE essays SET author_type = 'protected' WHERE author_type IS NULL OR author_type = ''")
    c.execute('''
        CREATE TABLE IF NOT EXISTS ddls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            target_date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # 修正常驻标志：确保 meta 表存在
    c.execute('''
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    # FTS5 全文搜索表
    c.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
            path, title, content, category
        )
    ''')
    # 修正旧数据（只执行一次）：SQLite 的 CURRENT_TIMESTAMP 是 UTC，批量加回 8 小时
    c.execute("SELECT value FROM meta WHERE key = 'tz_fixed'")
    row = c.fetchone()
    if not row:
        c.execute("UPDATE essays SET created_at = datetime(created_at, '+8 hours')")
        c.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('tz_fixed', '1')")
    conn.commit()
    conn.close()

init_db()
ensure_uncategorized()


def rebuild_fts_from_files():
    """把 uploads/ 下所有 .md 文件一次性灌入 FTS 表（幂等，只在 FTS 为空时执行）"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM notes_fts')
    count = c.fetchone()[0]
    if count > 0:
        conn.close()
        return  # FTS 已有数据，跳过

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        conn.close()
        return

    for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER']):
        for fname in files:
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, app.config['UPLOAD_FOLDER']).replace('\\', '/')
            title = fname.replace('.md', '')
            if '/' in rel:
                category = os.path.dirname(rel)
            else:
                category = UNCATEGORIZED
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                content = ''
            c.execute('INSERT INTO notes_fts (path, title, content, category) VALUES (?, ?, ?, ?)',
                     (rel, title, content, category))
    conn.commit()
    conn.close()


rebuild_fts_from_files()

# 主页
@app.route('/')
def home():
    return render_template('home.html')

# ===== 随笔区 =====
@app.route('/essays')
def essays():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM essays ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    return render_template('essays.html', essays=rows)

@app.route('/essays/add', methods=['POST'])
def add_essay():
    content = request.form.get('content', '').strip()
    if not content:
        flash('内容不能为空', 'error')
        return redirect(url_for('essays'))

    author_name = request.form.get('author_name', '寒食季').strip()
    password = request.form.get('password', '').strip()

    # 寒食季需要密码验证
    if author_name == '寒食季':
        if not password:
            flash('使用"寒食季"发布需要密码', 'error')
            return redirect(url_for('essays'))
        if password != os.environ.get('HANSHIJI_PASSWORD', '1992634518'):
            flash('密码错误', 'error')
            return redirect(url_for('essays'))

    # 处理图片上传
    image_filename = ''
    file = request.files.get('image')
    if file and file.filename:
        # 检查文件大小（MAX_CONTENT_LENGTH 只拦截超过 50MB 的，但这里做主动提示）
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        if file_size > 50 * 1024 * 1024:
            flash('图片大小不能超过 50MB', 'error')
            return redirect(url_for('essays'))
        ext = os.path.splitext(file.filename)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            sf = secure_filename(file.filename)
            # 加时间戳防止重名
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            image_filename = f'{timestamp}_{sf}'
            file.save(os.path.join(app.config['SNIPPET_IMAGES'], image_filename))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    local_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('INSERT INTO essays (content, image_path, created_at, author_name, author_type) VALUES (?, ?, ?, ?, ?)',
              (content, image_filename, local_time, author_name, 'protected' if author_name == '寒食季' else 'public'))
    conn.commit()
    conn.close()
    flash('发布成功！', 'success')
    return redirect(url_for('essays'))

@app.route('/essays/delete/<int:essay_id>', methods=['POST'])
def delete_essay(essay_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # 先查图片路径和作者再删
    c.execute('SELECT image_path, author_name FROM essays WHERE id = ?', (essay_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        flash('随笔不存在', 'error')
        return redirect(url_for('essays'))

    # 寒食季的随笔需要密码验证
    if row['author_name'] == '寒食季':
        password = request.form.get('password', '').strip()
        if not password:
            conn.close()
            flash('删除"寒食季"的随笔需要密码', 'error')
            return redirect(url_for('essays'))
        if password != os.environ.get('HANSHIJI_PASSWORD', '1992634518'):
            conn.close()
            flash('密码错误', 'error')
            return redirect(url_for('essays'))

    if row['image_path']:
        img_path = os.path.join(app.config['SNIPPET_IMAGES'], row['image_path'])
        if os.path.exists(img_path):
            os.remove(img_path)
    c.execute('DELETE FROM essays WHERE id = ?', (essay_id,))
    conn.commit()
    conn.close()
    flash('已删除', 'success')
    return redirect(url_for('essays'))

@app.route('/essays/edit/<int:essay_id>', methods=['POST'])
def edit_essay(essay_id):
    """更新随笔内容"""
    content = request.form.get('content', '').strip()
    if not content:
        return {'error': '内容不能为空'}, 400
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('UPDATE essays SET content = ? WHERE id = ?', (content, essay_id))
    if c.rowcount == 0:
        conn.close()
        return {'error': '随笔不存在'}, 404
    conn.commit()
    conn.close()
    return {'success': True}, 200

# ===== 笔记区 =====
@app.route('/notes')
def notes():
    # 结构: {'分类名': [{filename, title, mtime, mtime_ts, category, full_path}, ...]}
    # 第一步：预建所有分类骨架（确保空文件夹也显示）
    categories = {}
    ensure_uncategorized()
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        for item in os.listdir(app.config['UPLOAD_FOLDER']):
            path = os.path.join(app.config['UPLOAD_FOLDER'], item)
            if os.path.isdir(path):
                categories[item] = []

    # 第二步：遍历所有 .md 文件，填入对应分类
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER']):
            for fname in files:
                if not fname.endswith('.md'):
                    continue
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, app.config['UPLOAD_FOLDER'])
                if os.sep in rel:
                    category = os.path.dirname(rel).replace('\\', '/')
                    category = category if category != '.' else UNCATEGORIZED
                else:
                    category = UNCATEGORIZED

                mtime = os.path.getmtime(fpath)
                mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')

                # html_content 不再预渲染（节省内存）；单篇阅读时在 current_note 中单独渲染
                entry = {
                    'filename': fname,
                    'title': fname.replace('.md', ''),
                    'mtime': mtime_str,
                    'mtime_ts': mtime,
                    'category': category,
                    'full_path': rel.replace('\\', '/'),
                }

                if category not in categories:
                    categories[category] = []
                categories[category].append(entry)

    # 各分类内部按时间倒序
    for cat in categories:
        categories[cat].sort(key=lambda x: x['mtime_ts'], reverse=True)

    # 复用 get_categories_list() 获取排序后的分类列表（未分类固定在最后）
    cats_sorted = get_categories_list()
    categories_list = cats_sorted  # 下拉菜单与分类树同序

    # 检查是否有指定查看某篇笔记
    selected = request.args.get('note')
    current_note = None

    if selected:
        fpath = os.path.join(app.config['UPLOAD_FOLDER'], selected.replace('/', os.sep))
        if is_safe_path(app.config['UPLOAD_FOLDER'], fpath) and os.path.exists(fpath):
            with open(fpath, 'r', encoding='utf-8') as f:
                md_content = f.read()
            html_content = _render_markdown(md_content)
            mtime = os.path.getmtime(fpath)
            fname = os.path.basename(fpath)
            current_note = {
                'title': fname.replace('.md', ''),
                'filename': fname,
                'full_path': selected,
                'mtime': datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M'),
                'html_content': html_content
            }

    # 读取 DDL 数据
    conn_ddl = sqlite3.connect(DB_NAME)
    conn_ddl.row_factory = sqlite3.Row
    c_ddl = conn_ddl.cursor()
    c_ddl.execute('SELECT * FROM ddls ORDER BY target_date ASC')
    ddls = c_ddl.fetchall()
    conn_ddl.close()

    return render_template('notes.html',
                           categories=categories,
                           categories_order=cats_sorted,
                           uncategorized_key=UNCATEGORIZED,
                           categories_list=categories_list,
                           current_note=current_note,
                           ddls=ddls)

@app.route('/notes/upload', methods=['POST'])
def upload_note():
    if 'file' not in request.files:
        flash('没有选择文件', 'error')
        return redirect(url_for('notes'))
    file = request.files['file']
    if file.filename == '':
        flash('没有选择文件', 'error')
        return redirect(url_for('notes'))
    if not file.filename.endswith('.md'):
        flash('只能上传 .md 文件', 'error')
        return redirect(url_for('notes'))

    # 检查文件大小
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    if file_size > 50 * 1024 * 1024:
        flash('文件大小不能超过 50MB', 'error')
        return redirect(url_for('notes'))

    category = request.form.get('category', '').strip()
    if not category or category == UNCATEGORIZED:
        category = UNCATEGORIZED

    # 创建分类子文件夹
    cat_folder = os.path.join(app.config['UPLOAD_FOLDER'], category.replace('/', os.sep))
    os.makedirs(cat_folder, exist_ok=True)

    base_name = file.filename.replace('.md', '')
    # 处理重名
    counter = 1
    filename = base_name + '.md'
    fpath = os.path.join(cat_folder, filename)
    while os.path.exists(fpath):
        filename = f'{base_name}_{counter}.md'
        fpath = os.path.join(cat_folder, filename)
        counter += 1

    file.save(fpath)

    # 读取文件内容用于 FTS 索引
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            fts_content = f.read()
    except Exception:
        fts_content = ''

    # 同步 FTS（title 与实际文件名保持一致）
    title = filename.replace('.md', '')
    _sync_fts_insert((category + '/' + filename).replace('\\', '/'), title, fts_content, category)

    flash('上传成功！', 'success')
    return redirect(url_for('notes'))

@app.route('/notes/delete', methods=['POST'])
def delete_note():
    full_path = request.form.get('filename', '')  # 格式: category/filename.md
    if not full_path:
        flash('缺少文件路径', 'error')
        return redirect(url_for('notes'))
    fpath = os.path.join(app.config['UPLOAD_FOLDER'], full_path.replace('/', os.sep))
    if not is_safe_path(app.config['UPLOAD_FOLDER'], fpath):
        flash('非法路径', 'error')
        return redirect(url_for('notes'))
    real_path = os.path.realpath(fpath)
    if not os.path.exists(real_path):
        flash('文件不存在，可能已被删除', 'error')
        return redirect(url_for('notes'))
    try:
        _sync_fts_delete(full_path)
        os.remove(real_path)
        flash('已删除', 'success')
    except Exception as e:
        flash('删除失败：' + str(e), 'error')
    return redirect(url_for('notes'))

# ===== 分类管理 API =====
@app.route('/add_category', methods=['POST'])
def add_category():
    name = request.form.get('name', '').strip()
    if not name:
        flash('分类名不能为空', 'error')
        return redirect(url_for('notes'))
    # 禁止创建"未分类"同名
    if name == UNCATEGORIZED:
        flash('该名称为系统保留', 'error')
        return redirect(url_for('notes'))
    cat_folder = os.path.join(app.config['UPLOAD_FOLDER'], name)
    if not is_safe_path(app.config['UPLOAD_FOLDER'], cat_folder):
        flash('非法路径', 'error')
        return redirect(url_for('notes'))
    if os.path.exists(cat_folder) and os.path.isdir(cat_folder):
        flash('分类已存在', 'error')
        return redirect(url_for('notes'))
    try:
        os.makedirs(cat_folder, exist_ok=True)
        flash('分类已创建', 'success')
    except Exception as e:
        flash('创建失败：' + str(e), 'error')
    return redirect(url_for('notes'))

@app.route('/delete_category/<category_name>', methods=['POST'])
def delete_category(category_name):
    # 安全限制：绝对不允许删除未分类
    if category_name == UNCATEGORIZED:
        flash('不能删除"未分类"', 'error')
        return redirect(url_for('notes'))
    cat_folder = os.path.join(app.config['UPLOAD_FOLDER'], category_name)
    if not is_safe_path(app.config['UPLOAD_FOLDER'], cat_folder):
        flash('非法路径', 'error')
        return redirect(url_for('notes'))
    if not os.path.exists(cat_folder) or not os.path.isdir(cat_folder):
        flash('分类不存在', 'error')
        return redirect(url_for('notes'))

    # 统计文件数量，非空分类要求二次确认
    file_count = sum(len(files) for _, _, files in os.walk(cat_folder))
    confirm_token = request.form.get('confirm_token', '')
    if file_count > 0 and confirm_token != 'DELETE':
        flash(f'该分类下有 {file_count} 篇笔记，请再次确认删除（操作不可恢复）', 'error')
        return redirect(url_for('notes'))

    try:
        shutil.rmtree(cat_folder)
        # 同步 FTS：删除该分类下所有笔记记录
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('DELETE FROM notes_fts WHERE category = ?', (category_name,))
        conn.commit()
        conn.close()
        flash('分类已删除', 'success')
    except Exception as e:
        flash('删除失败：' + str(e), 'error')
    return redirect(url_for('notes'))

# ===== 新建 & 下载笔记 =====
@app.route('/create_md', methods=['POST'])
def create_md():
    filename = request.form.get('filename', '').strip()
    category = request.form.get('category', '').strip()
    if not filename:
        flash('文件名不能为空', 'error')
        return redirect(url_for('notes'))
    if not filename.endswith('.md'):
        filename += '.md'
    if not category or category == UNCATEGORIZED:
        category = UNCATEGORIZED
    # 创建分类目录
    cat_folder = os.path.join(app.config['UPLOAD_FOLDER'], category.replace('/', os.sep))
    os.makedirs(cat_folder, exist_ok=True)
    fpath = os.path.join(cat_folder, filename)
    if os.path.exists(fpath):
        flash('文件已存在，请换个名字', 'error')
        return redirect(url_for('notes'))
    try:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write('')
        rel_path = (category + '/' + filename).replace('\\', '/')
        # 同步 FTS（新建空笔记，内容为空）
        _sync_fts_insert(rel_path, filename.replace('.md', ''), '', category)
        from urllib.parse import quote
        return redirect(url_for('notes', note=quote(rel_path, safe='')))
    except Exception as e:
        flash('创建失败：' + str(e), 'error')
        return redirect(url_for('notes'))

@app.route('/download_md', methods=['GET'])
def download_md():
    full_path = request.args.get('path', '')
    if not full_path:
        return '缺少 path 参数', 400
    fpath = os.path.join(app.config['UPLOAD_FOLDER'], full_path.replace('/', os.sep))
    if not is_safe_path(app.config['UPLOAD_FOLDER'], fpath):
        return '非法路径', 403
    if not os.path.exists(fpath):
        return '文件不存在', 404
    return send_file(fpath, as_attachment=True, download_name=os.path.basename(full_path))

# ===== DDL 倒计时 =====
@app.route('/add_ddl', methods=['POST'])
def add_ddl():
    title = request.form.get('title', '').strip()
    target_date = request.form.get('target_date', '').strip()
    if title and target_date:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('INSERT INTO ddls (title, target_date) VALUES (?, ?)', (title, target_date))
        conn.commit()
        conn.close()
    return redirect(url_for('notes'))

@app.route('/delete_ddl/<int:ddl_id>', methods=['POST'])
def delete_ddl(ddl_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM ddls WHERE id = ?', (ddl_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('notes'))

# ===== Markdown 文件在线编辑 API =====
@app.route('/api/get_raw_md', methods=['GET'])
def get_raw_md():
    full_path = request.args.get('path', '')
    if not full_path:
        return {'error': '缺少 path 参数'}, 400
    # 安全检查：防止路径遍历
    fpath = os.path.join(app.config['UPLOAD_FOLDER'], full_path.replace('/', os.sep))
    if not is_safe_path(app.config['UPLOAD_FOLDER'], fpath):
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
def save_md():
    data = request.get_json()
    full_path = data.get('path', '') if data else ''
    content = data.get('content', '') if data else ''
    if not full_path:
        return {'error': '缺少 path 参数'}, 400
    # 安全检查：防止路径遍历
    fpath = os.path.join(app.config['UPLOAD_FOLDER'], full_path.replace('/', os.sep))
    if not is_safe_path(app.config['UPLOAD_FOLDER'], fpath):
        return {'error': '非法路径'}, 403
    if not os.path.exists(fpath):
        return {'error': '文件不存在'}, 404
    try:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        # 同步 FTS：更新 title（从 path 提取）和 content
        title = os.path.basename(full_path).replace('.md', '')
        if '/' in full_path:
            category = os.path.dirname(full_path).replace('\\', '/')
        else:
            category = UNCATEGORIZED
        _sync_fts_insert(full_path, title, content, category)
        return {'success': True}, 200
    except Exception as e:
        return {'error': str(e)}, 500


# ===== 笔记全文搜索 API =====
@app.route('/api/search', methods=['GET'])
def search_notes():
    q = request.args.get('q', '').strip()
    if not q:
        return {'results': []}, 200

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 始终执行 LIKE 搜索（FTS5 默认分词器对中文/混合内容支持差）
    # FTS MATCH 结果与 LIKE 取并集，以 FTS rank 优先
    like_q = '%' + q + '%'

    try:
        fts_query = q.replace('"', '""')
        c.execute('''
            SELECT path, title, content, category,
                   bm25(notes_fts, 3) as rank
            FROM notes_fts
            WHERE notes_fts MATCH ?
            ORDER BY rank
            LIMIT 10
        ''', (fts_query,))
        fts_rows = c.fetchall()
    except Exception:
        fts_rows = []

    # LIKE 搜索
    c.execute('''
        SELECT path, title, content, category
        FROM notes_fts
        WHERE title LIKE ? OR content LIKE ?
        ORDER BY path
        LIMIT 30
    ''', (like_q, like_q))
    like_rows = c.fetchall()

    # 去重合并：fts_rows 优先，like_rows 补充
    seen_paths = set()
    results = []
    for row in fts_rows:
        seen_paths.add(row['path'])
        results.append({
            'path': row['path'],
            'title': row['title'],
            'snippet': _build_snippet(row['content'], q),
            'category': row['category']
        })

    for row in like_rows:
        if row['path'] in seen_paths:
            continue
        if len(results) >= 10:
            break
        seen_paths.add(row['path'])
        results.append({
            'path': row['path'],
            'title': row['title'],
            'snippet': _build_snippet(row['content'], q),
            'category': row['category']
        })

    conn.close()
    return {'results': results}, 200

# ===== 获取局域网IP（供前端生成二维码） =====
@app.route('/api/get_lan_ip', methods=['GET'])
def get_lan_ip_api():
    return jsonify({'ip': get_lan_ip(), 'port': 5001}), 200

if __name__ == '__main__':
    lan_ip = get_lan_ip()
    print('=' * 50)
    print('  个人网站已启动！')
    print(f'  本机访问: http://127.0.0.1:5001')
    print(f'  局域网访问: http://{lan_ip}:5001')
    print('=' * 50)
    app.run(debug=True, host='0.0.0.0', port=5001)
