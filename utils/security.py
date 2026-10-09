import os
import secrets
from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# Set auto_error=False so unauthenticated API calls return clean JSON 401 without browser native popup freezes
security = HTTPBasic(auto_error=False)

# Read admin credentials from environment variables with safe defaults
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


def verify_admin_credentials(credentials: Optional[HTTPBasicCredentials] = Depends(security)) -> str:
    """
    Verifies HTTP Basic authentication credentials using timing-attack safe comparison.
    Returns username if authorized, or raises HTTP 401 JSON error.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required. Please log in.",
        )

    current_user_bytes = credentials.username.encode("utf-8")
    correct_user_bytes = ADMIN_USERNAME.encode("utf-8")
    is_user_correct = secrets.compare_digest(current_user_bytes, correct_user_bytes)

    current_pass_bytes = credentials.password.encode("utf-8")
    correct_pass_bytes = ADMIN_PASSWORD.encode("utf-8")
    is_pass_correct = secrets.compare_digest(current_pass_bytes, correct_pass_bytes)

    if not (is_user_correct and is_pass_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin username or password.",
        )
    return credentials.username
