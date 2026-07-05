# -*- coding: utf-8 -*-

from typing import List, Optional
from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):

    mode: str
    allowed_modes: List[str]
    binance_testnet: bool
    binance_api_key_set: bool
    binance_secret_key_set: bool
    binance_api_key_masked: str
    binance_secret_key_masked: str
    live_trading_available: bool
    live_trading_confirmed: bool
    account_balance: float
    live_trading_unavailable_reason: Optional[str] = None
    restart_triggered: bool = False

    # Risk
    risk_per_trade_percent: float
    max_open_positions: int
    max_position_exposure_percent: float
    minimum_risk_reward_ratio: float

    # Daily limits
    max_daily_trades: int
    max_daily_loss_percent: float
    maximum_daily_drawdown_percent: float
    enable_daily_trade_limit: bool
    enable_daily_loss_limit: bool
    enable_drawdown_protection: bool

    # Market
    symbols: str
    kline_interval: str

    # ATR
    atr_period: int
    atr_stop_multiplier: float
    atr_take_profit_multiplier: float
    atr_trailing_multiplier: float
    minimum_atr_percent: float

    # Signal quality
    minimum_signal_strength: float
    min_signal_confidence: float
    enable_volatility_filter: bool
    enable_ema_trend_filter: bool
    enable_market_regime_alignment: bool
    enable_signal_cooldown: bool
    signal_cooldown_seconds: int

    # Structure
    structure_min_score: float
    structure_min_impulse_percent: float
    structure_enable_consolidation_filter: bool

    # Position management
    enable_trailing_stop: bool
    enable_breakeven: bool
    breakeven_trigger_percent: float
    enable_dynamic_take_profit: bool
    dynamic_take_profit_proximity_percent: float

    # Exchange
    quantity_precision: int
    price_precision: int
    min_order_quantity: float
    min_order_notional: float

    # Simulation
    enable_fee_simulation: bool
    enable_slippage_simulation: bool
    maker_fee_percent: float
    taker_fee_percent: float


class SettingsUpdateRequest(BaseModel):

    mode: Optional[str] = None
    binance_testnet: Optional[bool] = None
    binance_api_key: Optional[str] = None
    binance_secret_key: Optional[str] = None
    live_trading_confirmed: Optional[bool] = None
    account_balance: Optional[float] = None

    # Risk
    risk_per_trade_percent: Optional[float] = None
    max_open_positions: Optional[int] = None
    max_position_exposure_percent: Optional[float] = None
    minimum_risk_reward_ratio: Optional[float] = None

    # Daily limits
    max_daily_trades: Optional[int] = None
    max_daily_loss_percent: Optional[float] = None
    maximum_daily_drawdown_percent: Optional[float] = None
    enable_daily_trade_limit: Optional[bool] = None
    enable_daily_loss_limit: Optional[bool] = None
    enable_drawdown_protection: Optional[bool] = None

    # Market — requires restart (websocket reconnect)
    symbols: Optional[str] = None
    kline_interval: Optional[str] = None

    # ATR
    atr_period: Optional[int] = None
    atr_stop_multiplier: Optional[float] = None
    atr_take_profit_multiplier: Optional[float] = None
    atr_trailing_multiplier: Optional[float] = None
    minimum_atr_percent: Optional[float] = None

    # Signal quality
    minimum_signal_strength: Optional[float] = None
    min_signal_confidence: Optional[float] = None
    enable_volatility_filter: Optional[bool] = None
    enable_ema_trend_filter: Optional[bool] = None
    enable_market_regime_alignment: Optional[bool] = None
    enable_signal_cooldown: Optional[bool] = None
    signal_cooldown_seconds: Optional[int] = None

    # Structure
    structure_min_score: Optional[float] = None
    structure_min_impulse_percent: Optional[float] = None
    structure_enable_consolidation_filter: Optional[bool] = None

    # Position management
    enable_trailing_stop: Optional[bool] = None
    enable_breakeven: Optional[bool] = None
    breakeven_trigger_percent: Optional[float] = None
    enable_dynamic_take_profit: Optional[bool] = None
    dynamic_take_profit_proximity_percent: Optional[float] = None

    # Exchange
    quantity_precision: Optional[int] = None
    price_precision: Optional[int] = None
    min_order_quantity: Optional[float] = None
    min_order_notional: Optional[float] = None

    # Simulation
    enable_fee_simulation: Optional[bool] = None
    enable_slippage_simulation: Optional[bool] = None
    maker_fee_percent: Optional[float] = None
    taker_fee_percent: Optional[float] = None
