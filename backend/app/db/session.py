"""SQLAlchemy engine / session。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import DATABASE_URL

# SQLite 多线程访问需要 check_same_thread=False
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)


def get_db():
    """FastAPI 依赖:每个请求一个 session。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
