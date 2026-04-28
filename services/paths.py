import os
import shutil
from datetime import datetime

from flask import current_app

from config import CST


def is_safe_path(base_dir, target_path):
    """防止路径遍历：确保 resolved path 在 base_dir 内部。"""
    try:
        real_base = os.path.realpath(base_dir)
        real_target = os.path.realpath(target_path)
        common = os.path.commonpath([real_base, real_target])
        return common == real_base
    except (ValueError, TypeError):
        return os.path.realpath(target_path).startswith(os.path.realpath(base_dir))


def safe_filename(name):
    """保留中文文件名，同时去掉目录部分，避免路径穿越。"""
    cleaned = os.path.basename((name or '').replace('\\', '/')).strip()
    return cleaned.replace('\x00', '')


def move_to_trash(path, root_dir):
    """把文件或目录移动到 trash/时间戳/原相对路径，避免硬删除。"""
    real_root = os.path.realpath(root_dir)
    real_path = os.path.realpath(path)
    if not is_safe_path(real_root, real_path):
        raise ValueError('非法路径')

    rel_path = os.path.relpath(real_path, real_root)
    stamp = datetime.now(tz=CST).strftime('%Y%m%d_%H%M%S')
    trash_path = os.path.join(current_app.config['TRASH_FOLDER'], stamp, rel_path)
    os.makedirs(os.path.dirname(trash_path), exist_ok=True)

    counter = 1
    final_path = trash_path
    while os.path.exists(final_path):
        base, ext = os.path.splitext(trash_path)
        final_path = f'{base}_{counter}{ext}'
        counter += 1

    shutil.move(real_path, final_path)
    return final_path
