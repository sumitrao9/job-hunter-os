import os
import shutil
import zipfile
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.config import settings

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.get("/status")
def backup_status():
    """Check the backup status and last backup time."""
    backup_dir = os.path.join(settings.data_dir, "backups")
    db_path = settings.database_url.replace("sqlite:///", "")
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.getcwd(), db_path)

    backups = []
    if os.path.isdir(backup_dir):
        for filename in sorted(os.listdir(backup_dir), reverse=True):
            if filename.endswith(".zip"):
                filepath = os.path.join(backup_dir, filename)
                backups.append({
                    "filename": filename,
                    "size_bytes": os.path.getsize(filepath),
                    "created": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat(),
                })

    return {
        "database_path": db_path,
        "database_exists": os.path.exists(db_path),
        "backup_dir": backup_dir,
        "backups": backups,
        "last_backup": backups[0]["created"] if backups else None,
    }


@router.post("/create")
def create_backup(label: str | None = None):
    """Create a backup of the database and uploads."""
    backup_dir = os.path.join(settings.data_dir, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    db_path = settings.database_url.replace("sqlite:///", "")
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.getcwd(), db_path)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    label_str = f"_{label}" if label else ""
    zip_name = f"backup_{timestamp}{label_str}.zip"
    zip_path = os.path.join(backup_dir, zip_name)

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if os.path.exists(db_path):
                zf.write(db_path, os.path.basename(db_path))

            uploads_dir = settings.upload_dir
            if os.path.isdir(uploads_dir):
                for root, dirs, files in os.walk(uploads_dir):
                    for filename in files:
                        if filename.endswith(".zip"):
                            continue
                        filepath = os.path.join(root, filename)
                        arcname = os.path.relpath(filepath, uploads_dir)
                        zf.write(filepath, os.path.join("uploads", arcname))

        return {
            "status": "success",
            "backup_path": zip_path,
            "backup_filename": zip_name,
            "size_bytes": os.path.getsize(zip_path),
            "timestamp": timestamp,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/restore")
def restore_backup(backup_filename: str):
    """Restore from a backup file."""
    backup_dir = os.path.join(settings.data_dir, "backups")
    backup_path = os.path.join(backup_dir, backup_filename)

    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="Backup file not found")

    db_path = settings.database_url.replace("sqlite:///", "")
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.getcwd(), db_path)

    try:
        # Create a safety backup first
        if os.path.exists(db_path):
            safety_name = f"safety_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(db_path, os.path.join(backup_dir, safety_name))

        with zipfile.ZipFile(backup_path, "r") as zf:
            zf.extractall(settings.data_dir)

        # Move extracted database to the expected path
        extracted_db = os.path.join(settings.data_dir, os.path.basename(db_path))
        if os.path.exists(extracted_db):
            shutil.move(extracted_db, db_path)

        return {"status": "success", "message": "Database restored successfully"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
