# database/connection.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator
from database.base import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hrm.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_all_tables() -> None:
    from modules.data_management import models as _dm_models  # noqa: F401
    from modules.payroll import models as _pr_models         # noqa: F401
    from modules.time_tracking import models as _tt_models   # noqa: F401
    Base.metadata.create_all(bind=engine)
