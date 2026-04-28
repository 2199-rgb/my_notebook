import os
import secrets
from datetime import timezone, timedelta


CST = timezone(timedelta(hours=8))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_NAME = os.path.join(BASE_DIR, 'blog.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
SNIPPET_IMAGES = os.path.join(BASE_DIR, 'static', 'snippet_images')
TRASH_FOLDER = os.path.join(BASE_DIR, 'trash')
UNCATEGORIZED = '未分类'

SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
HANSHIJI_PASSWORD = os.environ.get('HANSHIJI_PASSWORD') or os.environ.get('ADMIN_PASSWORD') or '1992634518'
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or HANSHIJI_PASSWORD

APP_DEBUG = os.environ.get('APP_DEBUG', '1').lower() in ('1', 'true', 'yes', 'on')
APP_HOST = os.environ.get('APP_HOST', '127.0.0.1')
APP_PORT = int(os.environ.get('APP_PORT', '5001'))
MAX_CONTENT_LENGTH = 50 * 1024 * 1024
