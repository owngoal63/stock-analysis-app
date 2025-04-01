"""
Core models for simulation engine with transaction sequence tracking.
File: app/services/simulation/models/trading.py
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any
import uuid

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
        if self.transaction_type == TransactionType.BUY:
            return (self.shares * self.price) + self.fees
        else:
            return (self.shares * self.price) - self.fees
    
    @property
    def net_amount(self) -> float:
        """Net transaction amount excluding fees"""
        return self.shares * self.price
        
    def get_signature(self) -> str:
        """Generate a unique signature for this transaction"""
        date_str = self.date.strftime('%Y-%m-%d')
        # Use a simple consistent format
        type_value = self.transaction_type.value if hasattr(self.transaction_type, 'value') else str(self.transaction_type)
        return f"{date_str}_{self.symbol}_{type_value}_{self.shares}"

@dataclass
class TransactionRecord:
    """Record for transaction table display"""
    date: datetime
    symbol: str
    type: str
    signal: str
    shares: int
    price: float
    fees: float
    total: float
    available_capital: float
    investment_value: float
    portfolio_total: float
    sequence_num: int = 0  # Added sequence number for ordering
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def get_formatted_record(self) -> Dict[str, Any]:
        """Get formatted record for display"""
        return {
            'Date': self.date.strftime('%d/%m/%Y'),
            'Symbol': self.symbol,
            'Type': self.type,
            'Signal': self.signal,
            'Shares': self.shares,
            'Price': f"£{self.price:.2f}",
            'Fees': f"£{self.fees:.2f}",
            'Total': f"£{self.total:.2f}",
            'Available Capital': f"£{self.available_capital:.2f}",
            'Investment Value': f"£{self.investment_value:.2f}",
            'Portfolio Total': f"£{self.portfolio_total:.2f}",
            'Sequence': self.sequence_num  # Include sequence number in output
        }
        
    def get_signature(self) -> str:
        """Generate a unique signature for this record"""
        date_str = self.date.strftime('%Y-%m-%d')
        # Use a simple consistent format matching the Transaction signature format
        return f"{date_str}_{self.symbol}_{self.type}_{self.shares}"

@dataclass
class PortfolioSnapshot:
    """Daily snapshot of portfolio state"""
    date: datetime
    cash: float
    positions: dict[str, Position]
    daily_transactions: list[Transaction]
    transaction_records: list[TransactionRecord] = field(default_factory=list)
    
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