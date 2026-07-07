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

    # Rodar migrations pendentes antes de criar tabelas
    # Garante que colunas adicionadas via Alembic existam
    # mesmo quando o banco já existia (optimizer, backtest, etc.)
    try:

        from alembic.config import Config as AlembicConfig
        from alembic import command as alembic_command
        from pathlib import Path
        import logging

        # Suprimir logs verbosos do Alembic no stdout
        logging.getLogger("alembic").setLevel(logging.WARNING)

        # Caminho absoluto baseado no arquivo database.py — independente do cwd
        _db_file = Path(__file__).resolve()
        _project_root = _db_file.parents[2]  # data/storage/database.py → project root

        alembic_cfg = AlembicConfig(
            str(_project_root / "alembic.ini")
        )
        # Garantir que alembic encontre os scripts na raiz correta
        alembic_cfg.set_main_option("script_location", str(_project_root / "alembic"))

        alembic_command.upgrade(alembic_cfg, "head")

    except Exception:

        # Se alembic falhar (ex: banco novo sem tabela alembic_version),
        # cai no create_all abaixo que cria tudo do zero
        pass

    Base.metadata.create_all(
        bind=engine
    )
