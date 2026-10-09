import os
import time
import shutil
import tempfile
import logging
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query

try:
    import psutil
except ImportError:
    psutil = None

from utils.security import verify_admin_credentials

router = APIRouter()
logger = logging.getLogger(__name__)

BASE_TEMP_DIR = os.path.join(tempfile.gettempdir(), "pdf_microservice_temp")


def _get_dir_size_and_count(dir_path: str) -> tuple[int, int]:
    """Calculates total size in bytes and file count for a directory tree."""
    total_size = 0
    file_count = 0
    if not os.path.exists(dir_path):
        return 0, 0
    if os.path.isfile(dir_path):
        return os.path.getsize(dir_path), 1

    for root, _, files in os.walk(dir_path):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.exists(fp):
                try:
                    total_size += os.path.getsize(fp)
                    file_count += 1
                except Exception:
                    pass
    return total_size, file_count


@router.get("/stats")
async def get_system_stats(admin_user: str = Depends(verify_admin_credentials)):
    """Returns server health metrics (CPU, RAM, Disk Usage)."""
    try:
        if psutil is None:
            cpu_percent = 0.0
            cpu_count = os.cpu_count() or 1
            mem_stats = {"total_mb": 0, "used_mb": 0, "free_mb": 0, "percent": 0}
            disk_stats = {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0}
        else:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count(logical=True) or 1
            
            mem = psutil.virtual_memory()
            mem_stats = {
                "total_mb": round(mem.total / (1024 * 1024), 2),
                "used_mb": round(mem.used / (1024 * 1024), 2),
                "free_mb": round(mem.available / (1024 * 1024), 2),
                "percent": mem.percent
            }
            
            disk = psutil.disk_usage(os.getcwd())
            disk_stats = {
                "total_gb": round(disk.total / (1024 ** 3), 2),
                "used_gb": round(disk.used / (1024 ** 3), 2),
                "free_gb": round(disk.free / (1024 ** 3), 2),
                "percent": disk.percent
            }
        
        # Temp storage metrics
        temp_size_bytes, temp_file_count = _get_dir_size_and_count(BASE_TEMP_DIR)
        
        return {
            "status": "online",
            "timestamp": datetime.now().isoformat(),
            "psutil_installed": psutil is not None,
            "cpu": {
                "percent": cpu_percent,
                "cores": cpu_count
            },
            "memory": mem_stats,
            "disk": disk_stats,
            "temp_storage": {
                "bytes": temp_size_bytes,
                "mb": round(temp_size_bytes / (1024 * 1024), 2),
                "file_count": temp_file_count
            }
        }
    except Exception as e:
        logger.error(f"Failed to retrieve system stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve system stats: {str(e)}")


@router.get("/storage")
async def get_storage_details(admin_user: str = Depends(verify_admin_credentials)):
    """Scans temporary storage directories and returns lingering file/job statistics."""
    if not os.path.exists(BASE_TEMP_DIR):
        return {
            "base_temp_dir": BASE_TEMP_DIR,
            "total_bytes": 0,
            "total_mb": 0.0,
            "total_jobs": 0,
            "total_files": 0,
            "jobs": []
        }

    jobs = []
    total_bytes = 0
    total_files = 0
    now = time.time()

    try:
        for entry in os.listdir(BASE_TEMP_DIR):
            entry_path = os.path.join(BASE_TEMP_DIR, entry)
            if os.path.exists(entry_path):
                size, file_cnt = _get_dir_size_and_count(entry_path)
                mtime = os.path.getmtime(entry_path)
                age_seconds = int(now - mtime)
                
                total_bytes += size
                total_files += file_cnt
                
                jobs.append({
                    "job_id": entry,
                    "is_dir": os.path.isdir(entry_path),
                    "size_bytes": size,
                    "size_mb": round(size / (1024 * 1024), 2),
                    "file_count": file_cnt,
                    "created_at": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "age_seconds": age_seconds
                })

        jobs.sort(key=lambda j: j["age_seconds"], reverse=True)

        return {
            "base_temp_dir": BASE_TEMP_DIR,
            "total_bytes": total_bytes,
            "total_mb": round(total_bytes / (1024 * 1024), 2),
            "total_jobs": len(jobs),
            "total_files": total_files,
            "jobs": jobs
        }
    except Exception as e:
        logger.error(f"Failed to scan storage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Storage scan error: {str(e)}")


@router.delete("/storage/clean")
async def clean_storage(
    max_age_seconds: int = Query(3600, description="Delete temp files older than this many seconds (default 3600 = 1 hr)"),
    admin_user: str = Depends(verify_admin_credentials)
):
    """Forcefully deletes temporary files/directories older than max_age_seconds."""
    if not os.path.exists(BASE_TEMP_DIR):
        return {
            "status": "success",
            "message": "Temporary storage directory is empty.",
            "cleaned_jobs_count": 0,
            "freed_bytes": 0,
            "freed_mb": 0.0
        }

    now = time.time()
    freed_bytes = 0
    cleaned_count = 0

    try:
        for entry in os.listdir(BASE_TEMP_DIR):
            entry_path = os.path.join(BASE_TEMP_DIR, entry)
            if not os.path.exists(entry_path):
                continue
                
            mtime = os.path.getmtime(entry_path)
            age = now - mtime
            
            # Clean if older than threshold
            if age >= max_age_seconds:
                size, _ = _get_dir_size_and_count(entry_path)
                try:
                    if os.path.isdir(entry_path):
                        shutil.rmtree(entry_path, ignore_errors=True)
                    else:
                        os.remove(entry_path)
                    freed_bytes += size
                    cleaned_count += 1
                except Exception as del_err:
                    logger.warning(f"Could not delete temp path '{entry_path}': {str(del_err)}")

        freed_mb = round(freed_bytes / (1024 * 1024), 2)
        logger.info(f"Admin '{admin_user}' cleaned {cleaned_count} temp jobs, freeing {freed_mb} MB.")

        return {
            "status": "success",
            "message": f"Successfully cleaned {cleaned_count} temporary job(s). Freed {freed_mb} MB.",
            "cleaned_jobs_count": cleaned_count,
            "freed_bytes": freed_bytes,
            "freed_mb": freed_mb
        }
    except Exception as e:
        logger.error(f"Failed to clean storage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Storage cleanup failed: {str(e)}")


# ==========================================
# USER MANAGEMENT ENDPOINTS (Admin Only)
# ==========================================

from pydantic import BaseModel, Field
from database import get_db, UserModel
from sqlalchemy.orm import Session
from services import auth_service


class UserRoleUpdate(BaseModel):
    role: str = Field(..., description="'admin' or 'user'")


class UserPasswordReset(BaseModel):
    new_password: str = Field(..., min_length=6)


class AdminUserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    role: str = Field("user", description="'admin' or 'user'")


@router.get("/users")
async def list_users(
    db: Session = Depends(get_db),
    admin_user: str = Depends(verify_admin_credentials)
):
    """Lists all registered users and user metrics."""
    try:
        users = db.query(UserModel).order_by(UserModel.id.desc()).all()
        users_list = []
        admin_cnt = 0
        user_cnt = 0

        for u in users:
            if u.role == "admin":
                admin_cnt += 1
            else:
                user_cnt += 1
                
            users_list.append({
                "id": u.id,
                "username": u.username,
                "role": u.role,
                "created_at": u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else "-"
            })

        return {
            "total_users": len(users),
            "admin_count": admin_cnt,
            "user_count": user_cnt,
            "users": users_list
        }
    except Exception as e:
        logger.error(f"Failed to list users: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve users: {str(e)}")


@router.post("/users")
async def create_user_by_admin(
    req: AdminUserCreate,
    db: Session = Depends(get_db),
    admin_user: str = Depends(verify_admin_credentials)
):
    """Allows Admin to create new user accounts directly."""
    existing = auth_service.get_user_by_username(db, req.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists.")

    new_user = auth_service.create_user_account(
        db, username=req.username, password=req.password, role=req.role
    )
    logger.info(f"Admin '{admin_user}' created user '{new_user.username}' with role '{new_user.role}'.")

    return {
        "status": "success",
        "message": f"User '{new_user.username}' created successfully.",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "role": new_user.role
        }
    }


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    req: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin_user: str = Depends(verify_admin_credentials)
):
    """Updates a user's role (admin <-> user)."""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if req.role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="Invalid role specified. Use 'admin' or 'user'.")

    user.role = req.role
    db.commit()
    logger.info(f"Admin '{admin_user}' updated role of '{user.username}' to '{user.role}'.")

    return {
        "status": "success",
        "message": f"User '{user.username}' role updated to '{user.role}'.",
        "role": user.role
    }


@router.put("/users/{user_id}/password")
async def reset_user_password(
    user_id: int,
    req: UserPasswordReset,
    db: Session = Depends(get_db),
    admin_user: str = Depends(verify_admin_credentials)
):
    """Resets a user's password directly."""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.hashed_password = auth_service.hash_password(req.new_password)
    db.commit()
    logger.info(f"Admin '{admin_user}' reset password for user '{user.username}'.")

    return {
        "status": "success",
        "message": f"Password reset successfully for user '{user.username}'."
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: str = Depends(verify_admin_credentials)
):
    """Deletes a user account from the database."""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Prevent deleting own current admin user
    if user.username == admin_user:
        raise HTTPException(status_code=400, detail="You cannot delete your own active admin account.")

    username = user.username
    db.delete(user)
    db.commit()
    logger.info(f"Admin '{admin_user}' deleted user account '{username}'.")

    return {
        "status": "success",
        "message": f"User account '{username}' deleted successfully."
    }
