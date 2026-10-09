import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

logger = logging.getLogger(__name__)

Base = declarative_base()


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")
    created_at = Column(DateTime, default=datetime.utcnow)


# MySQL Configuration with SQLite Fallback
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "pdf_master")

mysql_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
sqlite_url = "sqlite:///./pdf_master.db"

engine = None
SessionLocal = None

try:
    # Try connecting to MySQL database
    engine = create_engine(mysql_url, pool_pre_ping=True, connect_args={"connect_timeout": 3})
    # Test connection
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("Successfully connected to MySQL database.")
except Exception as e:
    logger.warning(f"MySQL connection unavailable ({str(e)}). Falling back to SQLite local database (pdf_master.db).")
    engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Creates database tables and seeds initial admin and user accounts."""
    Base.metadata.create_all(bind=engine)
    
    # Seed default accounts if empty
    from services.auth_service import hash_password
    
    db = SessionLocal()
    try:
        user_count = db.query(UserModel).count()
        if user_count == 0:
            logger.info("Seeding initial Admin and User accounts into database...")
            
            admin_user = UserModel(
                username="admin",
                hashed_password=hash_password("adminpassword123"),
                role="admin"
            )
            standard_user = UserModel(
                username="user1",
                hashed_password=hash_password("userpassword123"),
                role="user"
            )
            
            db.add(admin_user)
            db.add(standard_user)
            db.commit()
            logger.info("Seeded default users: 'admin' (adminpassword123) and 'user1' (userpassword123).")
    except Exception as seed_err:
        logger.error(f"Database seed error: {str(seed_err)}")
        db.rollback()
    finally:
        db.close()


def get_db():
    """FastAPI Dependency providing a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
