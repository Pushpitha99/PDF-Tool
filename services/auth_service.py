import os
import jwt
import hashlib
import logging
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

try:
    import bcrypt
except ImportError:
    bcrypt = None

from database import UserModel

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "pdf_master_super_secret_jwt_key_2026_x987")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def hash_password(password: str) -> str:
    """Hashes a password using direct bcrypt with SHA-256 fallback."""
    if bcrypt is not None:
        try:
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
            return hashed.decode("utf-8")
        except Exception as e:
            logger.warning(f"Bcrypt hash error: {str(e)}")

    # Fallback hashing if bcrypt fails
    salt_str = "pdf_master_salt_"
    return "sha256$" + hashlib.sha256((salt_str + password).encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against a stored hash."""
    if hashed_password.startswith("sha256$"):
        salt_str = "pdf_master_salt_"
        expected = "sha256$" + hashlib.sha256((salt_str + plain_password).encode("utf-8")).hexdigest()
        return expected == hashed_password
    
    if bcrypt is not None and hashed_password.startswith("$2"):
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception as e:
            logger.warning(f"Bcrypt verify error: {str(e)}")

    return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT access token containing claims (username, role)."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decodes and validates a JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError as e:
        logger.warning(f"JWT decode error: {str(e)}")
        return None


def get_user_by_username(db: Session, username: str) -> Optional[UserModel]:
    """Fetches a user document from the database by username."""
    return db.query(UserModel).filter(UserModel.username == username).first()


def authenticate_user(db: Session, username: str, password: str) -> Optional[UserModel]:
    """Authenticates a user by username and password."""
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_user_account(db: Session, username: str, password: str, role: str = "user") -> UserModel:
    """Creates and saves a new user document in the database."""
    hashed_pwd = hash_password(password)
    user_model = UserModel(
        username=username,
        hashed_password=hashed_pwd,
        role=role
    )
    db.add(user_model)
    db.commit()
    db.refresh(user_model)
    return user_model
