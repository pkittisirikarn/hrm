import os
import uuid
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile

BASE_UPLOAD = Path("static/uploads/recruitment")
BASE_UPLOAD.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_PDF = {"application/pdf"}


def save_upload(file: UploadFile, subdir: str, allowed: set[str]) -> Tuple[str, int]:
    if file.content_type not in allowed:
        raise ValueError(f"Unsupported content type: {file.content_type}")
    folder = BASE_UPLOAD / subdir
    folder.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or '').suffix or ''
    fname = f"{uuid.uuid4().hex}{ext}"
    path = folder / fname
    # เขียนไฟล์ลงดิสก์
    with path.open("wb") as f:
        data = file.file.read()
        f.write(data)
    # คืนค่า web path (เสิร์ฟผ่าน /static/...)
    web_path = f"/static/uploads/recruitment/{subdir}/{fname}"
    return web_path, len(data)