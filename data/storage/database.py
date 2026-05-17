# -*- coding: utf-8 -*-

from sqlalchemy import (
    create_engine,
    event
)

from sqlalchemy.orm import (
    DeclarativeBase,
    sessionmaker
)

# =====================================================
# DATABASE
# =====================================================

DATABASE_URL = (
    "sqlite:///data/storage/trades.db"
)

# =====================================================
# ENGINE
# =====================================================

engine = create_engine(

    DATABASE_URL,

    connect_args={

        "check_same_thread": False
    },

    future=True
)

# =====================================================
# SQLITE PRAGMA
# =====================================================

@event.listens_for(
    engine,
    "connect"
)
def set_sqlite_pragma(
    dbapi_connection,
    connection_record
):

    cursor = dbapi_connection.cursor()

    # =================================================
    # WAL MODE
    # =================================================

    cursor.execute(
        "PRAGMA journal_mode=WAL;"
    )

    # =================================================
    # NORMAL SYNC
    # =================================================

    cursor.execute(
        "PRAGMA synchronous=NORMAL;"
    )

    # =================================================
    # MEMORY TEMP STORE
    # =================================================

    cursor.execute(
        "PRAGMA temp_store=MEMORY;"
    )

    # =================================================
    # FOREIGN KEYS
    # =================================================

    cursor.execute(
        "PRAGMA foreign_keys=ON;"
    )

    cursor.close()

# =====================================================
# SESSION FACTORY
# =====================================================

SessionLocal = sessionmaker(

    autocommit=False,

    autoflush=False,

    # =================================================
    # IMPORTANT
    # =================================================

    expire_on_commit=False,

    bind=engine
)

# =====================================================
# BASE
# =====================================================

class Base(
    DeclarativeBase
):

    pass

# =====================================================
# INIT DATABASE
# =====================================================

def init_db():

    from data.storage.models import (

        Trade,

        EquityCurve,

        PortfolioSnapshot
    )

    Base.metadata.create_all(
        bind=engine
    )