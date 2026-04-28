import os
from datetime import datetime

from config import UNCATEGORIZED, UPLOAD_FOLDER


NOTE_INDEX_CACHE = None
NOTE_INDEX_CACHE_MTIME = None


def invalidate_note_index_cache():
    global NOTE_INDEX_CACHE, NOTE_INDEX_CACHE_MTIME
    NOTE_INDEX_CACHE = None
    NOTE_INDEX_CACHE_MTIME = None


def get_note_index_signature():
    latest_mtime = 0
    if os.path.exists(UPLOAD_FOLDER):
        for root, dirs, files in os.walk(UPLOAD_FOLDER):
            try:
                latest_mtime = max(latest_mtime, os.path.getmtime(root))
            except OSError:
                pass
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    latest_mtime = max(latest_mtime, os.path.getmtime(fpath))
                except OSError:
                    continue
    return latest_mtime


def get_note_index_state():
    ensure_uncategorized()
    latest_mtime = get_note_index_signature()

    categories = {}
    if os.path.exists(UPLOAD_FOLDER):
        for item in os.listdir(UPLOAD_FOLDER):
            path = os.path.join(UPLOAD_FOLDER, item)
            if os.path.isdir(path):
                categories[item] = []

    if os.path.exists(UPLOAD_FOLDER):
        for root, dirs, files in os.walk(UPLOAD_FOLDER):
            for fname in files:
                ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
                if ext not in ('md', 'pdf'):
                    continue
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, UPLOAD_FOLDER)
                if os.sep in rel:
                    category = os.path.dirname(rel).replace('\\', '/')
                    category = category if category != '.' else UNCATEGORIZED
                else:
                    category = UNCATEGORIZED

                mtime = os.path.getmtime(fpath)
                entry = {
                    'filename': fname,
                    'title': fname.rsplit('.', 1)[0] if '.' in fname else fname,
                    'mtime': datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M'),
                    'mtime_ts': mtime,
                    'category': category,
                    'full_path': rel.replace('\\', '/'),
                    'file_type': ext,
                    'is_markdown': ext == 'md',
                }

                if category not in categories:
                    categories[category] = []
                categories[category].append(entry)

    for cat in categories:
        categories[cat].sort(key=lambda x: x['mtime_ts'], reverse=True)

    return categories, latest_mtime


def get_note_index():
    global NOTE_INDEX_CACHE, NOTE_INDEX_CACHE_MTIME
    if NOTE_INDEX_CACHE is not None and NOTE_INDEX_CACHE_MTIME == get_note_index_signature():
        return NOTE_INDEX_CACHE

    categories, latest_mtime = get_note_index_state()
    NOTE_INDEX_CACHE = categories
    NOTE_INDEX_CACHE_MTIME = latest_mtime
    return NOTE_INDEX_CACHE


def ensure_uncategorized():
    os.makedirs(os.path.join(UPLOAD_FOLDER, UNCATEGORIZED), exist_ok=True)


def get_categories_list():
    ensure_uncategorized()
    subs = []
    for item in os.listdir(UPLOAD_FOLDER):
        path = os.path.join(UPLOAD_FOLDER, item)
        if os.path.isdir(path) and item != UNCATEGORIZED:
            subs.append(item)
    subs.sort()
    subs.append(UNCATEGORIZED)
    return subs
