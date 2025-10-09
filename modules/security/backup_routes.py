import os, shutil, glob
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from modules.security.deps import get_current_employee

api_backup = APIRouter(prefix="/api/v1/security/db", tags=["security-db"])
BACKUP_DIR = "backups"
DB_PATH = "hrm.db"  # ปรับถ้าฐานอยู่ที่อื่น
os.makedirs(BACKUP_DIR, exist_ok=True)

@api_backup.get("/backups")
def list_backups(me=Depends(get_current_employee)):
    if getattr(me, "role", "user") != "admin":
        raise HTTPException(403, "Admins only")
    files = sorted(glob.glob(os.path.join(BACKUP_DIR, "*.sqlite")), reverse=True)
    return [{"name": os.path.basename(f), "size": os.path.getsize(f)} for f in files]

@api_backup.post("/backup")
def make_backup(me=Depends(get_current_employee)):
    if getattr(me, "role", "user") != "admin":
        raise HTTPException(403, "Admins only")
    if not os.path.exists(DB_PATH):
        raise HTTPException(500, "DB file not found")
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"backup-{ts}.sqlite")
    shutil.copyfile(DB_PATH, dest)
    return {"ok": True, "file": os.path.basename(dest)}

@api_backup.get("/download")
def download_backup(name: str, me=Depends(get_current_employee)):
    if getattr(me, "role", "user") != "admin":
        raise HTTPException(403, "Admins only")
    path = os.path.join(BACKUP_DIR, name)
    if not os.path.isfile(path):
        raise HTTPException(404, "Not found")
    return FileResponse(path, media_type="application/octet-stream", filename=name)

@api_backup.post("/restore")
def restore_backup(file: UploadFile = File(None), name: str = "", me=Depends(get_current_employee)):
    if getattr(me, "role", "user") != "admin":
        raise HTTPException(403, "Admins only")
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    safe = os.path.join(BACKUP_DIR, f"auto-before-restore-{ts}.sqlite")
    if os.path.exists(DB_PATH):
        shutil.copyfile(DB_PATH, safe)
    if file and file.filename:
        tmp = os.path.join(BACKUP_DIR, f"upload-{ts}.sqlite")
        with open(tmp, "wb") as f:
            f.write(file.file.read())
        shutil.copyfile(tmp, DB_PATH)
    elif name:
        src = os.path.join(BACKUP_DIR, name)
        if not os.path.isfile(src):
            raise HTTPException(404, "Backup not found")
        shutil.copyfile(src, DB_PATH)
    else:
        raise HTTPException(400, "Provide backup file or name")
    return {"ok": True, "notice": "Restart the app to reload connections"}
