# -*- coding: utf-8 -*-

"""
Regression tests for the duplicate-Base bug between
data/storage/database.py and data/storage/models.py.

Bug fixed: models.py declared its own DeclarativeBase, separate from
database.py's Base. init_db() called Base.metadata.create_all() using
database.py's Base, which never registered Trade/EquityCurve/
PortfolioSnapshot (they were mapped against the *other* Base). This
meant init_db() silently created zero tables on a fresh database; it
only appeared to work because a pre-built trades.db shipped in the repo.
"""

from data.storage.database import (
    Base
)

from data.storage.models import (
    Trade,
    EquityCurve,
    PortfolioSnapshot
)


class TestSharedDeclarativeBase:

    def test_models_use_the_database_base(self):

        assert Trade.metadata is Base.metadata

        assert EquityCurve.metadata is Base.metadata

        assert PortfolioSnapshot.metadata is Base.metadata

    def test_base_metadata_contains_all_tables(self):

        table_names = set(
            Base.metadata.tables.keys()
        )

        assert "trades" in table_names

        assert "equity_curve" in table_names

        assert "portfolio_snapshots" in table_names

    def test_trade_table_has_position_lifecycle_columns(self):

        columns = {
            column.name
            for column in Base.metadata.tables["trades"].columns
        }

        # these 4 columns exist in the shipped trades.db but were
        # never added by any alembic migration; confirm the ORM
        # model (and therefore init_db) knows about them too

        for expected in (
            "highest_price",
            "lowest_price",
            "unrealized_pnl",
            "realized_pnl"
        ):

            assert expected in columns


class TestInitDbCreatesRealTables:

    def test_init_db_creates_all_mapped_tables(self):

        # the autouse _isolated_test_database fixture already calls
        # create_all via Base.metadata; re-running init_db() here
        # must be a no-op that doesn't error, and the tables must
        # already be queryable

        from data.storage.database import init_db, engine

        init_db()

        from sqlalchemy import inspect

        inspector = inspect(engine)

        table_names = set(
            inspector.get_table_names()
        )

        assert "trades" in table_names

        assert "equity_curve" in table_names

        assert "portfolio_snapshots" in table_names
