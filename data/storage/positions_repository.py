# -*- coding: utf-8 -*-

from sqlalchemy.orm import Session

from data.storage.database import SessionLocal

from data.storage.models import Trade


class PositionsRepository:

    def __init__(self):

        self.session: Session = SessionLocal()

    def create_position(
        self,
        user_id: int,
        symbol: str,
        action: str,
        entry_price: float,
        quantity: float,
        stop_loss: float,
        take_profit: float,
        trailing_stop: float,
        breakeven_enabled: bool = True
    ):

        try:

            position = Trade(
                user_id=user_id,
                symbol=symbol,
                action=action,
                entry_price=entry_price,
                current_price=entry_price,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
                trailing_stop=trailing_stop,
                breakeven_enabled=breakeven_enabled,
                status="OPEN",
                pnl=0.0
            )

            self.session.add(position)

            self.session.commit()

            self.session.refresh(position)

            return position

        except Exception:

            self.session.rollback()

            raise

    def get_open_position(
        self,
        user_id: int,
        symbol: str
    ):

        try:

            return (
                self.session.query(Trade)
                .filter(
                    Trade.user_id == user_id,
                    Trade.symbol == symbol,
                    Trade.status == "OPEN"
                )
                .first()
            )

        except Exception:

            self.session.rollback()

            raise

    def has_open_position(
        self,
        user_id: int,
        symbol: str
    ) -> bool:

        try:

            position = (
                self.session.query(Trade)
                .filter(
                    Trade.user_id == user_id,
                    Trade.symbol == symbol,
                    Trade.status == "OPEN"
                )
                .first()
            )

            return position is not None

        except Exception:

            self.session.rollback()

            raise
            
            
          
    def get_open_positions(
        self,
        user_id: int
    ):
    
        try:
    
            return (
                self.session.query(Trade)
                .filter(
                    Trade.user_id == user_id,
                    Trade.status == "OPEN"
                )
                .all()
            )
    
        except Exception:
    
            self.session.rollback()
    
            raise              
            
            
            
    def close_position(
        self,
        trade_id: int,
        exit_price: float,
        pnl: float,
        reason: str
    ):
    
        try:
    
            trade = (
                self.session.query(Trade)
                .filter(
                    Trade.id == trade_id
                )
                .first()
            )
    
            if not trade:
                return None
    
            trade.current_price = exit_price
            trade.pnl = pnl
            trade.status = "CLOSED"
    
            if hasattr(trade, "close_reason"):
                trade.close_reason = reason
    
            self.session.commit()
    
            self.session.refresh(trade)
    
            return trade
    
        except Exception:
    
            self.session.rollback()
    
            raise