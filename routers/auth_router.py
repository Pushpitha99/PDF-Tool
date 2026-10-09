import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db, UserModel
from models.user import LoginRequest, UserCreate, UserResponse, Token
from services import auth_service

router = APIRouter()
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserModel:
    """Dependency that decodes Bearer JWT token and returns the current user model."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = auth_service.decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    username = payload["sub"]
    user = auth_service.get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found."
        )

    return user


def require_admin_role(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """Dependency that restricts route access strictly to Admin users."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Admin privilege required."
        )
    return current_user


def require_user_role(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """Dependency that ensures the user is authenticated."""
    return current_user


@router.post("/login", response_model=Token)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Verifies username and password, returning a JWT token and user role."""
    user = auth_service.authenticate_user(db, req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password."
        )

    token = auth_service.create_access_token(data={"sub": user.username, "role": user.role})
    logger.info(f"User '{user.username}' logged in successfully (Role: {user.role}).")

    return Token(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            role=user.role
        )
    )


@router.post("/register", response_model=UserResponse)
async def register(req: UserCreate, db: Session = Depends(get_db)):
    """Registers a new standard user account."""
    existing = auth_service.get_user_by_username(db, req.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken. Please choose another."
        )

    new_user = auth_service.create_user_account(db, req.username, req.password, role="user")
    logger.info(f"New user registered: '{new_user.username}'.")

    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        role=new_user.role
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserModel = Depends(get_current_user)):
    """Returns profile details for the currently authenticated user."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role
    )
