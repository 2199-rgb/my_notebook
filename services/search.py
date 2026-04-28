import os
import re

from config import UNCATEGORIZED, UPLOAD_FOLDER
from db import get_db, get_direct_db_connection


def sync_fts_insert(rel_path, title, content, category):
    conn = get_direct_db_connection()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO notes_fts (path, title, content, category) VALUES (?, ?, ?, ?)',
              (rel_path, title, content, category))
    conn.commit()
    conn.close()


def sync_fts_delete(rel_path):
    conn = get_direct_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM notes_fts WHERE path = ?', (rel_path,))
    conn.commit()
    conn.close()


def build_snippet(content, keyword, radius=80):
    if not content:
        return ''
    if not keyword:
        return content[:radius * 2] + ('...' if len(content) > radius * 2 else '')

    lower_content = content.lower()
    lower_kw = keyword.lower()
    pos = lower_content.find(lower_kw)

    if pos == -1:
        return content[:radius * 2] + ('...' if len(content) > radius * 2 else '')

    start = max(0, pos - radius)
    end = min(len(content), pos + len(keyword) + radius)
    snippet = content[start:end]

    prefix = '...' if start > 0 else ''
    suffix = '...' if end < len(content) else ''
    snippet = prefix + snippet + suffix

    def mark_replace(m):
        return '<mark>' + m.group(0) + '</mark>'

    escaped_kw = re.escape(keyword)
    return re.sub(escaped_kw, mark_replace, snippet, flags=re.IGNORECASE)


def rebuild_fts_from_files():
    conn = get_direct_db_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM notes_fts')
    count = c.fetchone()[0]
    if count > 0:
        conn.close()
        return

    if not os.path.exists(UPLOAD_FOLDER):
        conn.close()
        return

    for root, dirs, files in os.walk(UPLOAD_FOLDER):
        for fname in files:
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, UPLOAD_FOLDER).replace('\\', '/')
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


def search_notes(q):
    if not q:
        return []

    db = get_db()
    like_q = '%' + q + '%'

    try:
        fts_query = q.replace('"', '""')
        fts_rows = db.execute('''
            SELECT path, title, content, category,
                   bm25(notes_fts, 3) as rank
            FROM notes_fts
            WHERE notes_fts MATCH ?
            ORDER BY rank
            LIMIT 10
        ''', (fts_query,)).fetchall()
    except Exception:
        fts_rows = []

    like_rows = db.execute('''
        SELECT path, title, content, category
        FROM notes_fts
        WHERE title LIKE ? OR content LIKE ?
        ORDER BY path
        LIMIT 30
    ''', (like_q, like_q)).fetchall()

    seen_paths = set()
    results = []
    for row in fts_rows:
        seen_paths.add(row['path'])
        results.append({
            'path': row['path'],
            'title': row['title'],
            'snippet': build_snippet(row['content'], q),
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
            'snippet': build_snippet(row['content'], q),
            'category': row['category']
        })

    return results
