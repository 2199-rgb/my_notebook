from flask import flash, redirect, render_template, request, url_for

from config import COMMENTS_REQUIRE_APPROVAL
from services.auth import admin_required, is_admin
from services.comments import (
    DELETED_STATUS,
    HIDDEN_STATUS,
    PENDING_STATUS,
    VISIBLE_STATUS,
    create_comment,
    list_comments,
    list_pending_count,
    set_comment_pinned,
    update_comment_status,
)


def register_routes(app):
    @app.route('/messages')
    def messages():
        moderation = is_admin() and request.args.get('view') == 'moderation'
        comments = list_comments(include_moderation=moderation)
        pending_count = list_pending_count() if is_admin() else 0
        return render_template(
            'messages.html',
            comments=comments,
            pending_count=pending_count,
            moderation=moderation,
            comments_require_approval=COMMENTS_REQUIRE_APPROVAL,
        )

    @app.route('/messages/add', methods=['POST'])
    def add_message():
        honeypot = request.form.get('website', '').strip()
        if honeypot:
            flash('留言已收到，稍后会显示', 'success')
            return redirect(url_for('messages'))

        parent_id = request.form.get('parent_id') or None
        try:
            comment_id, status = create_comment(
                target_type='site',
                target_id=None,
                parent_id=int(parent_id) if parent_id else None,
                author_name=request.form.get('author_name', ''),
                email=request.form.get('email', ''),
                content=request.form.get('content', ''),
                ip=request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip(),
                user_agent=request.headers.get('User-Agent', ''),
                is_admin=is_admin(),
            )
        except ValueError as exc:
            flash(str(exc), 'error')
            return redirect(url_for('messages'))

        if status == VISIBLE_STATUS:
            flash('留言已发布', 'success')
            return redirect(url_for('messages') + f'#comment-{comment_id}')

        flash('留言已提交，管理员审核后会显示', 'success')
        return redirect(url_for('messages'))

    @app.route('/messages/<int:comment_id>/approve', methods=['POST'])
    @admin_required
    def approve_message(comment_id):
        update_comment_status(comment_id, VISIBLE_STATUS)
        flash('留言已通过', 'success')
        return _moderation_redirect(comment_id)

    @app.route('/messages/<int:comment_id>/hide', methods=['POST'])
    @admin_required
    def hide_message(comment_id):
        update_comment_status(comment_id, HIDDEN_STATUS)
        flash('留言已隐藏', 'success')
        return _moderation_redirect(comment_id)

    @app.route('/messages/<int:comment_id>/restore', methods=['POST'])
    @admin_required
    def restore_message(comment_id):
        update_comment_status(comment_id, VISIBLE_STATUS)
        flash('留言已恢复显示', 'success')
        return _moderation_redirect(comment_id)

    @app.route('/messages/<int:comment_id>/delete', methods=['POST'])
    @admin_required
    def delete_message(comment_id):
        update_comment_status(comment_id, DELETED_STATUS)
        flash('留言已移入删除状态', 'success')
        return redirect(url_for('messages', view='moderation'))

    @app.route('/messages/<int:comment_id>/pin', methods=['POST'])
    @admin_required
    def pin_message(comment_id):
        set_comment_pinned(comment_id, True)
        flash('留言已置顶', 'success')
        return _moderation_redirect(comment_id)

    @app.route('/messages/<int:comment_id>/unpin', methods=['POST'])
    @admin_required
    def unpin_message(comment_id):
        set_comment_pinned(comment_id, False)
        flash('已取消置顶', 'success')
        return _moderation_redirect(comment_id)


def _moderation_redirect(comment_id):
    return redirect(url_for('messages', view='moderation') + f'#comment-{comment_id}')
