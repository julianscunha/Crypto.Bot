# -*- coding: utf-8 -*-

"""
Regression tests for core/services/portfolio_service.py

Bug #1 fixed: peak_equity was computed as
max(initial_balance, balance, equity) -- only looking at the *current*
snapshot's own values. This understated drawdown whenever equity had
fallen from a higher point reached in an earlier, already-recorded
snapshot. Fixed by also considering the true historical maximum
equity across all prior snapshots (PortfolioRepository.get_max_equity).

Bug #2 fixed: that historical-peak lookup wasn't scoped to the
account_balance configuration in effect at the time. Deliberately
resetting the paper account (e.g. lowering account_balance from 100
to 10 in core/config/trading_config.py) left old, much higher equity
snapshots in the table. Those got picked up as "historical peak"
forever, turning a config change into what looked like a ~90% real
trading loss the very first time a snapshot was built after the
reset. Fixed by recording initial_balance on every snapshot and
scoping get_max_equity() to snapshots from the same configuration.
"""

from core.services.portfolio_service import (
    portfolio_service
)

from data.storage.repositories.portfolio_repository import (
    portfolio_repository
)


class TestPeakEquityDrawdown:

    def test_drawdown_reflects_historical_peak_not_just_current_snapshot(
        self
    ):

        user_id = 9001

        # simulate equity having risen to 150 in an earlier snapshot
        # from the SAME session (same initial_balance=100)
        portfolio_repository.create_snapshot(
            user_id=user_id,
            balance=150.0,
            equity=150.0,
            realized_pnl=50.0,
            unrealized_pnl=0.0,
            total_pnl=50.0,
            open_positions=0,
            closed_positions=1,
            exposure=0.0,
            drawdown=0.0,
            initial_balance=100.0
        )

        # now equity has fallen back to the initial balance; with the
        # old bug this would report 0% drawdown since it only looked
        # at initial_balance/balance/equity (all 100 here)
        snapshot = portfolio_service.build_snapshot(
            user_id=user_id,
            initial_balance=100.0
        )

        assert snapshot.equity == 100.0

        # true drawdown from the 150 peak: (150-100)/150 = 33.33%
        assert snapshot.drawdown == 33.33

    def test_no_historical_peak_falls_back_to_current_values(self):

        user_id = 9002

        snapshot = portfolio_service.build_snapshot(
            user_id=user_id,
            initial_balance=100.0
        )

        assert snapshot.drawdown == 0.0

    def test_drawdown_zero_when_equity_at_new_high(self):

        user_id = 9003

        portfolio_repository.create_snapshot(
            user_id=user_id,
            balance=100.0,
            equity=100.0,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            total_pnl=0.0,
            open_positions=0,
            closed_positions=0,
            exposure=0.0,
            drawdown=0.0,
            initial_balance=200.0
        )

        # current equity (200) is a new high above any historical
        # peak; drawdown should be 0, not based on a stale lower peak
        snapshot = portfolio_service.build_snapshot(
            user_id=user_id,
            initial_balance=200.0
        )

        assert snapshot.drawdown == 0.0


class TestPeakEquitySessionScoping:

    def test_balance_reset_does_not_inherit_old_session_peak(self):

        user_id = 9004

        # old session: account configured with $100, equity peaked
        # there
        portfolio_repository.create_snapshot(
            user_id=user_id,
            balance=100.0,
            equity=100.0,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            total_pnl=0.0,
            open_positions=0,
            closed_positions=0,
            exposure=0.0,
            drawdown=0.0,
            initial_balance=100.0
        )

        # deliberate reset: account reconfigured to $10. Without the
        # session-scoping fix, get_max_equity() would still return
        # 100.0 here, and (100-10)/100 = 90% drawdown would be
        # reported on a fresh account that never actually lost
        # anything.
        snapshot = portfolio_service.build_snapshot(
            user_id=user_id,
            initial_balance=10.0
        )

        assert snapshot.equity == 10.0

        assert snapshot.drawdown == 0.0

    def test_real_loss_within_the_same_session_still_counts(self):

        user_id = 9005

        # same session throughout (initial_balance=10 both times):
        # equity legitimately rose to 12 in an earlier snapshot
        portfolio_repository.create_snapshot(
            user_id=user_id,
            balance=12.0,
            equity=12.0,
            realized_pnl=2.0,
            unrealized_pnl=0.0,
            total_pnl=2.0,
            open_positions=0,
            closed_positions=1,
            exposure=0.0,
            drawdown=0.0,
            initial_balance=10.0
        )

        # current real balance/equity for this (otherwise trade-less,
        # isolated) user_id resolves to initial_balance=10 -- the
        # point under test is that the 12 peak from the SAME session
        # is correctly picked up and NOT discarded by the session
        # scoping fix: (12-10)/12 = 16.67%
        snapshot = portfolio_service.build_snapshot(
            user_id=user_id,
            initial_balance=10.0
        )

        assert snapshot.drawdown == 16.67

    def test_records_initial_balance_on_new_snapshot(self):

        user_id = 9006

        snapshot = portfolio_service.build_snapshot(
            user_id=user_id,
            initial_balance=42.0
        )

        assert snapshot.initial_balance == 42.0

    def test_unscoped_lookup_still_works_for_backward_compatibility(
        self
    ):

        # get_max_equity(initial_balance=None) -- the default --
        # must still return the unscoped historical max, for any
        # existing caller that doesn't pass initial_balance
        user_id = 9007

        portfolio_repository.create_snapshot(
            user_id=user_id,
            balance=500.0,
            equity=500.0,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            total_pnl=0.0,
            open_positions=0,
            closed_positions=0,
            exposure=0.0,
            drawdown=0.0,
            initial_balance=100.0
        )

        unscoped = portfolio_repository.get_max_equity(
            user_id=user_id
        )

        assert unscoped == 500.0

        scoped = portfolio_repository.get_max_equity(
            user_id=user_id,
            initial_balance=999.0
        )

        assert scoped == 0.0
