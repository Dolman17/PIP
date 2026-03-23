from __future__ import annotations

import os

from flask import current_app
from werkzeug.utils import secure_filename

from models import DocumentFile


def next_version_for(pip_id, doc_type):
    last = (
        DocumentFile.query
        .filter_by(pip_id=pip_id, doc_type=doc_type)
        .order_by(DocumentFile.version.desc())
        .first()
    )
    return 1 if not last else last.version + 1


def save_file(bytes_data: bytes, rel_dir: str, filename: str) -> str:
    dir_path = os.path.join(current_app.config['UPLOAD_FOLDER'], rel_dir)
    os.makedirs(dir_path, exist_ok=True)
    fpath = os.path.join(dir_path, secure_filename(filename))
    with open(fpath, 'wb') as f:
        f.write(bytes_data)
    return os.path.join(rel_dir, secure_filename(filename))