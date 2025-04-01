"""
BLUE model trading strategy implementation with transaction sequence counting.
File: app/services/simulation/models/blue_model.py
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
import logging
import pandas as pd
import uuid

from app.services.simulation.models.parameters import SimulationParameters
from app.services.simulation.models.trading import (
    Position, Transaction, PortfolioSnapshot, SignalType, TransactionType, TransactionRecord
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
        self.transaction_records: List[TransactionRecord] = []
        
        # Track processed transactions to prevent duplicates
        self.processed_transaction_signatures: Set[str] = set()
        
        # Transaction sequence counter for ensuring correct display order
        self.transaction_counter = 0
    
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
    
    def _get_transaction_signature(self, date: datetime, symbol: str, transaction_type: TransactionType, shares: int, price: float) -> str:
        """
        Generate a unique signature for a transaction to detect duplicates
        
        Args:
            date: Transaction date
            symbol: Stock symbol
            transaction_type: Buy or Sell
            shares: Number of shares
            price: Share price
            
        Returns:
            str: Unique transaction signature
        """
        date_str = date.strftime('%Y-%m-%d')
        type_value = transaction_type.value if hasattr(transaction_type, 'value') else str(transaction_type)
        # Use a simple consistent format
        return f"{date_str}_{symbol}_{type_value}_{shares}"
    
    def _execute_transaction(
        self,
        date: datetime,
        symbol: str,
        signal: SignalType,
        price: float
    ) -> Optional[Transaction]:
        """
        Execute a buy or sell transaction with zero-share prevention and duplicate detection
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
                
                # ZERO SHARE PREVENTION: Skip if shares would be zero or negative
                if shares <= 0:
                    return None
                    
            else:  # SELL or STRONG_SELL
                if not current_position or current_position.shares <= 0:
                    return None
                    
                transaction_type = TransactionType.SELL
                
                # Calculate shares to sell - ensure at least 1 share is sold
                amount_shares = max(1, int((amount / current_position_value) * current_position.shares))
                shares = min(current_position.shares, amount_shares)
                
                # ZERO SHARE PREVENTION: Ensure at least 1 share is sold if selling
                if shares <= 0:
                    return None
                    
            # DUPLICATE TRANSACTION PREVENTION: Check if this exact transaction has already been processed
            transaction_signature = self._get_transaction_signature(
                date, symbol, transaction_type, shares, price
            )
            
            if transaction_signature in self.processed_transaction_signatures:
                self.logger.warning(
                    f"Duplicate transaction detected and prevented: {transaction_signature}"
                )
                return None
                
            # Add signature to processed set to prevent future duplicates
            self.processed_transaction_signatures.add(transaction_signature)
            
            # Calculate fees
            fee = (shares * price) * (self.parameters.transaction_fee_percent / 100)
            
            # Create transaction with verified positive share count
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
            
            # Calculate the investment value after this transaction
            investment_value = sum(p.market_value for p in self.positions.values())
            
            # Increment transaction sequence counter
            self.transaction_counter += 1
            
            # Create a transaction record with sequence number to ensure correct display order
            record = TransactionRecord(
                date=transaction.date,
                symbol=transaction.symbol,
                type=transaction.transaction_type.value,
                signal=transaction.signal_type.value,
                shares=transaction.shares,
                price=transaction.price,
                fees=transaction.fees,
                total=transaction.total_amount,
                available_capital=self.cash,
                investment_value=investment_value,
                portfolio_total=self.cash + investment_value,
                sequence_num=self.transaction_counter  # Add sequence number for ordering
            )
            
            # Add the record to our list of transaction records
            self.transaction_records.append(record)
            
            self.transactions.append(transaction)
            return transaction
            
        except Exception as e:
            self.logger.error(f"Error executing transaction: {str(e)}")
            return None
    
    def update_position_values(self, prices: Dict[str, float]) -> None:
        """
        Update all position values with latest prices
        
        Args:
            prices: Dictionary mapping symbols to their current prices
        """
        for symbol, position in self.positions.items():
            if symbol in prices:
                position.last_price = prices[symbol]  # Update the last price to current day's price

    def _create_snapshot(self, date: datetime, daily_transactions: List[Transaction]) -> None:
        """Create daily portfolio snapshot using current day's prices"""
        # Create a deep copy of positions to avoid reference issues
        current_positions = {}
        for symbol, pos in self.positions.items():
            current_positions[symbol] = Position(
                symbol=pos.symbol,
                shares=pos.shares,
                average_price=pos.average_price,
                last_price=pos.last_price  # This should be current day's price
            )

        # Get the transaction records that were created during this batch of transactions
        # (i.e., transaction records created since the last snapshot)
        start_idx = len(self.transaction_records) - len(daily_transactions) if daily_transactions else len(self.transaction_records)
        # Be extra cautious - if start_idx is out of range, use empty list
        current_transaction_records = (
            self.transaction_records[start_idx:] if start_idx < len(self.transaction_records) else []
        )

        snapshot = PortfolioSnapshot(
            date=date,
            cash=self.cash,
            positions=current_positions,
            daily_transactions=daily_transactions,
            transaction_records=current_transaction_records
        )
        self.snapshots.append(snapshot)

    def get_total_portfolio_value(self) -> float:
        """Get current total portfolio value using current day's prices"""
        position_values = sum(p.market_value for p in self.positions.values())  # market_value uses last_price
        return self.cash + position_values

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
            prices: Dictionary of stock symbols to current day's prices
            
        Returns:
            List[Transaction]: List of executed transactions
        """
        # First, update all position values with latest prices
        self.update_position_values(prices)
        
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
        
        # Create daily snapshot with current prices
        self._create_snapshot(date, daily_transactions)
        
        return daily_transactions