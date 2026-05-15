# -*- coding: utf-8 -*-

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///data/storage/trades.db"

# =====================================================
# ENGINE
# =====================================================

engine = create_engine(
    DATABASE_URL,

    connect_args={
        "check_same_thread": False
    },

    # =================================================
    # POOL CONTROL
    # =================================================

    pool_size=20,
    max_overflow=40,
    pool_timeout=30,
    pool_recycle=1800
)

# =====================================================
# SESSION FACTORY
# =====================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,

    # =================================================
    # IMPORTANT:
    # Prevent ORM object expiration after commit.
    # Avoids implicit lazy reloads reopening
    # connections in async/event-driven flows.
    # =================================================

    expire_on_commit=False,

    bind=engine
)

# =====================================================
# BASE
# =====================================================

class Base(DeclarativeBase):
    pass

# =====================================================
# INIT DATABASE
# =====================================================

def init_db():

    from data.storage.models import (
        Trade,
        EquityCurve
    )

    Base.metadata.create_all(
        bind=engine
    )