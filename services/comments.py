import hashlib
from datetime import datetime, timedelta

from config import COMMENTS_REQUIRE_APPROVAL, CST, SECRET_KEY
from db import get_db


VISIBLE_STATUS = 'visible'
PENDING_STATUS = 'pending'
HIDDEN_STATUS = 'hidden'
DELETED_STATUS = 'deleted'


def hash_value(value):
    if not value:
        return ''
    raw = f'{SECRET_KEY}:{value}'.encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def normalize_author(name):
    cleaned = (name or '').strip()
    if not cleaned:
        return '匿名访客'
    return cleaned[:24]


def normalize_content(content):
    cleaned = (content or '').strip()
    return cleaned[:1200]


def is_rate_limited(ip_hash, seconds=20):
    if not ip_hash:
        return False
    db = get_db()
    row = db.execute(
        '''
        SELECT created_at FROM comments
        WHERE ip_hash = ?
        ORDER BY created_at DESC
        LIMIT 1
        ''',
        (ip_hash,)
    ).fetchone()
    if not row:
        return False
    try:
        created_at = datetime.strptime(row['created_at'], '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return False
    return datetime.now(tz=CST).replace(tzinfo=None) - created_at < timedelta(seconds=seconds)


def create_comment(target_type, target_id, parent_id, author_name, email, content,
                   ip, user_agent, is_admin=False):
    author_name = normalize_author(author_name)
    content = normalize_content(content)
    if not content:
        raise ValueError('留言内容不能为空')
    if len(content) < 2:
        raise ValueError('留言内容太短啦')

    ip_hash = hash_value(ip)
    if not is_admin and is_rate_limited(ip_hash):
        raise ValueError('留言太快了，稍等一下再发')

    status = VISIBLE_STATUS if is_admin or not COMMENTS_REQUIRE_APPROVAL else PENDING_STATUS
    is_admin_reply = 1 if is_admin else 0
    now = datetime.now(tz=CST).strftime('%Y-%m-%d %H:%M:%S')
    db = get_db()
    cur = db.execute(
        '''
        INSERT INTO comments (
            target_type, target_id, parent_id, author_name, author_email_hash,
            content, status, is_admin_reply, ip_hash, user_agent_hash,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            target_type,
            target_id,
            parent_id,
            author_name,
            hash_value((email or '').strip().lower()),
            content,
            status,
            is_admin_reply,
            ip_hash,
            hash_value(user_agent),
            now,
            now,
        )
    )
    db.commit()
    return cur.lastrowid, status


def list_comments(target_type='site', target_id=None, include_moderation=False):
    db = get_db()
    params = [target_type]
    target_clause = 'target_id IS NULL'
    if target_id is not None:
        target_clause = 'target_id = ?'
        params.append(target_id)

    if include_moderation:
        status_clause = 'status != ?'
        params.append(DELETED_STATUS)
    else:
        status_clause = 'status = ?'
        params.append(VISIBLE_STATUS)

    rows = db.execute(
        f'''
        SELECT * FROM comments
        WHERE target_type = ?
          AND {target_clause}
          AND {status_clause}
        ORDER BY is_pinned DESC, created_at DESC, id DESC
        ''',
        params
    ).fetchall()

    comments = [dict(row) for row in rows]
    by_id = {item['id']: {**item, 'replies': []} for item in comments}
    roots = []
    for item in by_id.values():
        parent_id = item['parent_id']
        if parent_id and parent_id in by_id:
            by_id[parent_id]['replies'].append(item)
        elif parent_id is None:
            roots.append(item)
        elif include_moderation:
            roots.append(item)

    for item in by_id.values():
        item['replies'].sort(key=lambda x: (x['created_at'], x['id']))
    return roots


def list_pending_count():
    db = get_db()
    row = db.execute("SELECT COUNT(*) AS count FROM comments WHERE status = ?", (PENDING_STATUS,)).fetchone()
    return row['count'] if row else 0


def update_comment_status(comment_id, status):
    if status not in {VISIBLE_STATUS, PENDING_STATUS, HIDDEN_STATUS, DELETED_STATUS}:
        raise ValueError('非法状态')
    now = datetime.now(tz=CST).strftime('%Y-%m-%d %H:%M:%S')
    db = get_db()
    db.execute('UPDATE comments SET status = ?, updated_at = ? WHERE id = ?', (status, now, comment_id))
    db.commit()


def set_comment_pinned(comment_id, pinned):
    now = datetime.now(tz=CST).strftime('%Y-%m-%d %H:%M:%S')
    db = get_db()
    db.execute(
        'UPDATE comments SET is_pinned = ?, updated_at = ? WHERE id = ?',
        (1 if pinned else 0, now, comment_id)
    )
    db.commit()
