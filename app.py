import os
import sys

from flask import Flask

import config
from db import close_db, init_db
from routes.essays import register_routes as register_essay_routes
from routes.main import register_routes as register_main_routes
from routes.messages import register_routes as register_message_routes
from routes.notes import register_routes as register_note_routes
from services.auth import is_admin
from services.network import get_lan_ip
from services.note_index import ensure_uncategorized
from services.search import rebuild_fts_from_files


sys.stdout.reconfigure(encoding='utf-8')


def create_app():
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
    app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
    app.config['SNIPPET_IMAGES'] = config.SNIPPET_IMAGES
    app.config['TRASH_FOLDER'] = config.TRASH_FOLDER

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['SNIPPET_IMAGES'], exist_ok=True)
    os.makedirs(app.config['TRASH_FOLDER'], exist_ok=True)

    app.teardown_appcontext(close_db)
    app.context_processor(lambda: {'is_admin': is_admin()})

    with app.app_context():
        init_db()
        ensure_uncategorized()
        rebuild_fts_from_files()

    register_main_routes(app)
    register_essay_routes(app)
    register_message_routes(app)
    register_note_routes(app)

    return app


app = create_app()


if __name__ == '__main__':
    lan_ip = get_lan_ip()
    print('=' * 50)
    print('  个人网站已启动！')
    print(f'  本机访问: http://127.0.0.1:{config.APP_PORT}')
    if config.APP_HOST == '0.0.0.0':
        print(f'  局域网访问: http://{lan_ip}:{config.APP_PORT}')
    else:
        print('  当前仅监听本机；如需局域网访问，请设置 APP_HOST=0.0.0.0')
    print('=' * 50)
    app.run(debug=config.APP_DEBUG, host=config.APP_HOST, port=config.APP_PORT)
