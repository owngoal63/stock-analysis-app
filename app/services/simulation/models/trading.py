"""
Core models for simulation engine.
File: app/services/simulation/models/trading.py
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class SignalType(Enum):
    """Trading signal types"""
    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    NEUTRAL = "Neutral"
    SELL = "Sell"
    STRONG_SELL = "Strong Sell"

class TransactionType(Enum):
    """Transaction types"""
    BUY = "Buy"
    SELL = "Sell"

@dataclass
class Position:
    """Represents a stock position in the portfolio"""
    symbol: str
    shares: int
    average_price: float
    last_price: float
    
    @property
    def market_value(self) -> float:
        """Current market value of position"""
        return self.shares * self.last_price
    
    @property
    def cost_basis(self) -> float:
        """Total cost of position"""
        return self.shares * self.average_price
    
    @property
    def unrealized_pl(self) -> float:
        """Unrealized profit/loss"""
        return self.market_value - self.cost_basis
    
    @property
    def unrealized_pl_percent(self) -> float:
        """Unrealized profit/loss percentage"""
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pl / self.cost_basis) * 100

@dataclass
class Transaction:
    """Represents a buy or sell transaction"""
    date: datetime
    symbol: str
    transaction_type: TransactionType
    signal_type: SignalType
    shares: int
    price: float
    fees: float
    
    @property
    def total_amount(self) -> float:
        """Total transaction amount including fees"""
        return (self.shares * self.price) + self.fees
    
    @property
    def net_amount(self) -> float:
        """Net transaction amount excluding fees"""
        return self.shares * self.price

@dataclass
class PortfolioSnapshot:
    """Daily snapshot of portfolio state"""
    date: datetime
    cash: float
    positions: dict[str, Position]
    daily_transactions: list[Transaction]
    
    @property
    def total_value(self) -> float:
        """Total portfolio value including cash"""
        return self.cash + sum(p.market_value for p in self.positions.values())
    
    @property
    def total_invested(self) -> float:
        """Total amount invested in positions"""
        return sum(p.market_value for p in self.positions.values())
    
    @property
    def total_pl(self) -> float:
        """Total unrealized profit/loss"""
        return sum(p.unrealized_pl for p in self.positions.values())