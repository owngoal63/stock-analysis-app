"""
BLUE model trading strategy implementation.
File: app/services/simulation/models/blue_model.py
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
import pandas as pd

from app.services.simulation.models.parameters import SimulationParameters
from app.services.simulation.models.trading import (
    Position, Transaction, PortfolioSnapshot, SignalType, TransactionType
)
from app.services.market_data import MarketDataService
from app.services.technical_analysis import TechnicalAnalysisService

class BlueModel:
    """BLUE model trading strategy implementation"""
    
    def __init__(
        self,
        parameters: SimulationParameters,
        market_data: MarketDataService,
        technical_analysis: TechnicalAnalysisService
    ):
        """Initialize BLUE model"""
        self.parameters = parameters
        self.market_data = market_data
        self.technical_analysis = technical_analysis
        self.logger = logging.getLogger(__name__)
        
        # Initialize portfolio state
        self.cash = parameters.initial_capital
        self.positions: Dict[str, Position] = {}
        self.transactions: List[Transaction] = []
        self.snapshots: List[PortfolioSnapshot] = []
    
    def _calculate_max_shares(self, price: float, available_cash: float) -> int:
        """
        Calculate maximum shares that can be purchased
        
        Args:
            price: Current stock price
            available_cash: Available cash for purchase
            
        Returns:
            int: Maximum number of whole shares that can be purchased
        """
        # Account for transaction fee
        fee_multiplier = 1 + (self.parameters.transaction_fee_percent / 100)
        max_shares = int(available_cash / (price * fee_multiplier))
        return max_shares
    
    def _calculate_investment_amount(
        self,
        signal: SignalType,
        available_cash: float,
        current_position_value: float = 0
    ) -> float:
        """
        Calculate investment amount based on signal type
        
        Args:
            signal: Signal type
            available_cash: Available cash
            current_position_value: Current position value (for sells)
            
        Returns:
            float: Target investment amount
        """
        portfolio_value = self.get_total_portfolio_value()
        
        if signal in [SignalType.STRONG_BUY, SignalType.BUY]:
            # Calculate base amount from available cash
            if signal == SignalType.STRONG_BUY:
                base_amount = available_cash * (self.parameters.investment_rules['strong_buy_percent'] / 100)
            else:
                base_amount = available_cash * (self.parameters.investment_rules['buy_percent'] / 100)
            
            # Check maximum position size constraint
            max_allowed = portfolio_value * (self.parameters.max_single_position_percent / 100)
            return min(base_amount, max_allowed - current_position_value)
            
        elif signal in [SignalType.STRONG_SELL, SignalType.SELL]:
            # Calculate sell amount from current position
            if signal == SignalType.STRONG_SELL:
                return current_position_value * (self.parameters.investment_rules['strong_sell_percent'] / 100)
            else:
                return current_position_value * (self.parameters.investment_rules['sell_percent'] / 100)
        
        return 0.0
    
    def _execute_transaction(
        self,
        date: datetime,
        symbol: str,
        signal: SignalType,
        price: float
    ) -> Optional[Transaction]:
        """
        Execute a buy or sell transaction
        
        Args:
            date: Transaction date
            symbol: Stock symbol
            signal: Signal type
            price: Current stock price
            
        Returns:
            Optional[Transaction]: Executed transaction or None
        """
        try:
            current_position = self.positions.get(symbol)
            current_position_value = current_position.market_value if current_position else 0
            
            # Calculate investment amount
            amount = self._calculate_investment_amount(
                signal,
                self.cash,
                current_position_value
            )
            
            if amount <= 0:
                return None
            
            # Calculate transaction details
            if signal in [SignalType.STRONG_BUY, SignalType.BUY]:
                transaction_type = TransactionType.BUY
                shares = self._calculate_max_shares(price, amount)
                if shares <= 0:
                    return None
                    
            else:  # SELL or STRONG_SELL
                if not current_position or current_position.shares <= 0:
                    return None
                transaction_type = TransactionType.SELL
                shares = int(min(
                    current_position.shares,
                    (amount / price)
                ))
            
            # Calculate fees
            fee = (shares * price) * (self.parameters.transaction_fee_percent / 100)
            
            # Create transaction
            transaction = Transaction(
                date=date,
                symbol=symbol,
                transaction_type=transaction_type,
                signal_type=signal,
                shares=shares,
                price=price,
                fees=fee
            )
            
            # Update position
            if transaction_type == TransactionType.BUY:
                if symbol not in self.positions:
                    self.positions[symbol] = Position(
                        symbol=symbol,
                        shares=shares,
                        average_price=price,
                        last_price=price
                    )
                else:
                    position = self.positions[symbol]
                    total_cost = (position.shares * position.average_price) + (shares * price)
                    total_shares = position.shares + shares
                    position.average_price = total_cost / total_shares
                    position.shares = total_shares
                    position.last_price = price
                
                self.cash -= transaction.total_amount
                
            else:  # SELL
                position = self.positions[symbol]
                position.shares -= shares
                position.last_price = price
                if position.shares == 0:
                    del self.positions[symbol]
                
                self.cash += transaction.total_amount
            
            self.transactions.append(transaction)
            return transaction
            
        except Exception as e:
            self.logger.error(f"Error executing transaction: {str(e)}")
            return None
    
    def _create_snapshot(self, date: datetime, daily_transactions: List[Transaction]) -> None:
        """Create daily portfolio snapshot"""
        snapshot = PortfolioSnapshot(
            date=date,
            cash=self.cash,
            positions=self.positions.copy(),
            daily_transactions=daily_transactions
        )
        self.snapshots.append(snapshot)
    
    def get_total_portfolio_value(self) -> float:
        """Get current total portfolio value"""
        return self.cash + sum(p.market_value for p in self.positions.values())
    
    def process_signals(
        self,
        date: datetime,
        signals: Dict[str, SignalType],
        prices: Dict[str, float]
    ) -> List[Transaction]:
        """
        Process trading signals for the day
        
        Args:
            date: Current date
            signals: Dictionary of stock symbols to signal types
            prices: Dictionary of stock symbols to prices
            
        Returns:
            List[Transaction]: List of executed transactions
        """
        daily_transactions = []
        
        # Process sells first
        for symbol, signal in signals.items():
            if signal in [SignalType.STRONG_SELL, SignalType.SELL]:
                if symbol in self.positions:
                    transaction = self._execute_transaction(
                        date,
                        symbol,
                        signal,
                        prices[symbol]
                    )
                    if transaction:
                        daily_transactions.append(transaction)
        
        # Then process buys
        for symbol, signal in signals.items():
            if signal in [SignalType.STRONG_BUY, SignalType.BUY]:
                transaction = self._execute_transaction(
                    date,
                    symbol,
                    signal,
                    prices[symbol]
                )
                if transaction:
                    daily_transactions.append(transaction)
        
        # Update positions with latest prices
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].last_price = price
        
        # Create daily snapshot
        self._create_snapshot(date, daily_transactions)
        
        return daily_transactions