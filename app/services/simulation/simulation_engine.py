"""
Core simulation engine implementation with debug statements removed.
File: app/services/simulation/simulation_engine.py
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable, Set
import pandas as pd
import numpy as np
from dataclasses import dataclass, field

from app.services.market_data import MarketDataService
from app.services.technical_analysis import TechnicalAnalysisService
from app.services.simulation.models.parameters import SimulationParameters
from app.services.simulation.models.trading import (
    Position, Transaction, PortfolioSnapshot, SignalType, TransactionType, TransactionRecord
)
from app.services.simulation.models.blue_model import BlueModel

@dataclass
class SimulationResults:
    """Container for simulation results"""
    initial_capital: float
    final_portfolio_value: float
    total_return: float
    total_return_percent: float
    max_drawdown: float
    number_of_trades: int
    win_rate: float
    avg_holding_period: float
    sharpe_ratio: float
    transactions: List[Transaction]
    transaction_records: List[TransactionRecord]  # New field for transaction records
    portfolio_values: pd.Series
    cash_values: pd.Series
    positions_values: pd.Series
    daily_returns: pd.Series

class SimulationEngine:
    """Portfolio simulation engine"""
    
    def __init__(
        self,
        market_data: MarketDataService,
        technical_analysis: TechnicalAnalysisService,
        parameters: SimulationParameters
    ):
        self.market_data = market_data
        self.technical_analysis = technical_analysis
        self.parameters = parameters
        self.logger = logging.getLogger(__name__)
        self.model = BlueModel(parameters, market_data, technical_analysis)

    def _generate_signals_and_prices(
        self,
        symbols: List[str],
        date: datetime,
        lookback_days: int = 60
    ) -> Tuple[Dict[str, SignalType], Dict[str, float]]:
        """
        Generate signals and get prices for all symbols
        
        Args:
            symbols: List of stock symbols
            date: Current date
            lookback_days: Number of days for MACD calculation
            
        Returns:
            Tuple of (signals dict, prices dict)
        """
        signals = {}
        prices = {}
        lookback = date - timedelta(days=lookback_days)
        
        for symbol in symbols:
            try:
                # Get historical data
                price_data, _ = self.market_data.get_stock_data(
                    symbol,
                    lookback,
                    date
                )
                
                if len(price_data) < 30:  # Minimum required for MACD
                    continue
                
                # Calculate MACD
                macd_data = self.technical_analysis.calculate_macd(price_data)
                
                # Get latest price and store it
                latest_price = price_data['close'].iloc[-1]
                prices[symbol] = latest_price
                
                # Generate signal
                macd = macd_data['macd_line'].iloc[-1]
                signal = macd_data['signal_line'].iloc[-1]
                hist = macd_data['histogram'].iloc[-1]
                prev_hist = macd_data['histogram'].iloc[-2]
                
                signal_strength = abs(macd - signal)
                hist_change = hist - prev_hist
                
                # Explicitly set signal_type to make debugging clearer
                signal_type = None
                
                if hist > 0 and hist_change > 0 and macd > signal:
                    if signal_strength >= 0.5:
                        signal_type = SignalType.STRONG_BUY
                    else:
                        signal_type = SignalType.BUY
                elif hist < 0 and hist_change < 0 and macd < signal:
                    if signal_strength >= 0.5:
                        signal_type = SignalType.STRONG_SELL
                    else:
                        signal_type = SignalType.SELL
                else:
                    signal_type = SignalType.NEUTRAL
                
                signals[symbol] = signal_type
                    
            except Exception as e:
                self.logger.error(f"Error processing {symbol}: {str(e)}")
                continue
                
        return signals, prices

    def _calculate_metrics(
        self,
        snapshots: List[PortfolioSnapshot],
        risk_free_rate: float = 0.02
    ) -> SimulationResults:
        """Calculate performance metrics from simulation results with numeric safeguards"""
        try:
            # Extract daily values using current day's prices
            dates = [s.date for s in snapshots]
            
            # Safely extract values and ensure they're numeric
            portfolio_values_raw = [float(s.total_value) for s in snapshots]
            cash_values_raw = [float(s.cash) for s in snapshots]
            positions_values_raw = [float(s.total_invested) for s in snapshots]
            
            # Create Series with proper indices
            portfolio_values = pd.Series(portfolio_values_raw, index=dates)
            cash_values = pd.Series(cash_values_raw, index=dates)
            positions_values = pd.Series(positions_values_raw, index=dates)
            
            # Calculate daily returns using current day's values
            daily_returns = portfolio_values.pct_change().fillna(0)
            
            # Get all transactions from snapshots
            transactions = []
            for s in snapshots:
                for t in s.daily_transactions:
                    if hasattr(t, 'shares') and t.shares is not None and t.shares > 0:
                        transactions.append(t)
            
            # Get transaction records with deduplication
            transaction_signatures = set()
            unique_transaction_records = []
            
            for s in snapshots:
                for record in s.transaction_records:
                    try:
                        signature = record.get_signature()
                        if signature not in transaction_signatures:
                            transaction_signatures.add(signature)
                            unique_transaction_records.append(record)
                    except Exception as e:
                        self.logger.error(f"Error getting signature for record: {str(e)}")
            
            # If there are no unique records but we have transactions, use those to create records
            if len(unique_transaction_records) == 0 and len(transactions) > 0:
                for t in transactions:
                    # Create a basic record
                    record = TransactionRecord(
                        date=t.date,
                        symbol=t.symbol,
                        type=t.transaction_type.value,
                        signal=t.signal_type.value,
                        shares=t.shares,
                        price=t.price,
                        fees=t.fees,
                        total=t.total_amount,
                        available_capital=0.0,  # Will be fixed up later
                        investment_value=0.0,   # Will be fixed up later
                        portfolio_total=0.0     # Will be fixed up later
                    )
                    unique_transaction_records.append(record)
            
            # Calculate metrics (safely with error handling)
            try:
                total_return = float(portfolio_values.iloc[-1]) - self.parameters.initial_capital
            except (IndexError, TypeError):
                total_return = 0.0
                
            try:
                total_return_pct = (total_return / self.parameters.initial_capital) * 100
            except (ZeroDivisionError, TypeError):
                total_return_pct = 0.0
            
            # Calculate maximum drawdown (safely)
            try:
                rolling_max = portfolio_values.expanding().max()
                drawdowns = (portfolio_values - rolling_max) / rolling_max
                max_drawdown = abs(drawdowns.min()) * 100
            except Exception:
                max_drawdown = 0.0
            
            # Calculate win rate and holding periods (safely)
            completed_trades = []
            position_start_dates = {}
            
            for t in transactions:
                try:
                    if t.transaction_type == TransactionType.BUY:
                        if t.symbol not in position_start_dates:
                            position_start_dates[t.symbol] = []
                        position_start_dates[t.symbol].append({
                            'date': t.date,
                            'price': t.price,
                            'shares': t.shares,
                            'fees': t.fees
                        })
                    elif t.transaction_type == TransactionType.SELL and t.symbol in position_start_dates:
                        # Match FIFO for completed trades
                        shares_to_match = t.shares
                        while position_start_dates[t.symbol] and shares_to_match > 0:
                            buy_position = position_start_dates[t.symbol][0]
                            shares_sold = min(buy_position['shares'], shares_to_match)
                            
                            # Calculate profit/loss for this part of the position
                            buy_cost = shares_sold * buy_position['price'] + (buy_position['fees'] * shares_sold / buy_position['shares'])
                            sell_proceeds = shares_sold * t.price - (t.fees * shares_sold / t.shares)
                            profit = sell_proceeds - buy_cost
                            
                            completed_trades.append({
                                'profit': profit,
                                'holding_period': (t.date - buy_position['date']).days
                            })
                            
                            # Update remaining shares
                            shares_to_match -= shares_sold
                            buy_position['shares'] -= shares_sold
                            
                            if buy_position['shares'] <= 0:
                                position_start_dates[t.symbol].pop(0)
                        
                        if not position_start_dates[t.symbol]:
                            del position_start_dates[t.symbol]
                except Exception as e:
                    self.logger.error(f"Error processing trade for metrics: {str(e)}")
            
            # Calculate win rate (safely)
            try:
                winning_trades = len([t for t in completed_trades if t['profit'] > 0])
                win_rate = (winning_trades / len(completed_trades) * 100) if completed_trades else 0
            except Exception:
                win_rate = 0.0
            
            # Calculate average holding period (safely)
            try:
                avg_holding_period = (
                    sum(t['holding_period'] for t in completed_trades) / len(completed_trades)
                    if completed_trades else 0
                )
            except Exception:
                avg_holding_period = 0.0
            
            # Calculate Sharpe ratio (safely)
            try:
                daily_rf_rate = (1 + risk_free_rate) ** (1/252) - 1
                excess_returns = daily_returns - daily_rf_rate
                
                sharpe_ratio = (
                    (excess_returns.mean() * 252) /
                    (excess_returns.std() * (252 ** 0.5))
                    if excess_returns.std() != 0 else 0
                )
            except Exception:
                sharpe_ratio = 0.0
            
            # Create SimulationResults with all numeric values validated
            results = SimulationResults(
                initial_capital=float(self.parameters.initial_capital),
                final_portfolio_value=float(portfolio_values.iloc[-1]) if len(portfolio_values) > 0 else 0.0,
                total_return=float(total_return),
                total_return_percent=float(total_return_pct),
                max_drawdown=float(max_drawdown),
                number_of_trades=int(len(transactions)),
                win_rate=float(win_rate),
                avg_holding_period=float(avg_holding_period),
                sharpe_ratio=float(sharpe_ratio),
                transactions=transactions,
                transaction_records=unique_transaction_records,  # Use deduplicated records
                portfolio_values=portfolio_values,
                cash_values=cash_values,
                positions_values=positions_values,
                daily_returns=daily_returns
            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error calculating metrics: {str(e)}")
            
            # Return empty results
            empty_index = [datetime.now()]
            return SimulationResults(
                initial_capital=float(self.parameters.initial_capital),
                final_portfolio_value=float(self.parameters.initial_capital),
                total_return=0.0,
                total_return_percent=0.0,
                max_drawdown=0.0,
                number_of_trades=0,
                win_rate=0.0,
                avg_holding_period=0.0,
                sharpe_ratio=0.0,
                transactions=[],
                transaction_records=[],  # Empty transaction records
                portfolio_values=pd.Series([self.parameters.initial_capital], index=empty_index),
                cash_values=pd.Series([self.parameters.initial_capital], index=empty_index),
                positions_values=pd.Series([0.0], index=empty_index),
                daily_returns=pd.Series([0.0], index=empty_index)
            )

    def run_simulation(
        self,
        watchlist: List[str],
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Optional[SimulationResults]:
        try:
            # Validate parameters
            if not self.parameters.is_valid:
                raise ValueError(
                    "Invalid parameters: " +
                    ", ".join(self.parameters.get_validation_errors())
                )
            
            # Initialize simulation dates
            current_date = self.parameters.start_date
            end_date = datetime.now()
            
            total_days = (end_date - current_date).days
            days_processed = 0
            
            # Track processed dates to prevent duplicate processing
            processed_dates = set()
            
            # Temporarily disable duplication prevention for debugging
            use_date_tracking = False
            
            transaction_count = 0
            
            while current_date <= end_date:
                # Skip already processed dates
                date_key = current_date.strftime('%Y-%m-%d')
                if use_date_tracking and date_key in processed_dates:
                    current_date += timedelta(days=1)
                    days_processed += 1
                    continue
                
                # Mark this date as processed
                processed_dates.add(date_key)
                
                # Update progress
                if progress_callback:
                    progress = min(days_processed / total_days, 1.0)
                    progress_callback(progress)
                
                # Generate signals and get current prices
                signals, prices = self._generate_signals_and_prices(watchlist, current_date)
                
                # Filter for actionable signals only
                actionable_signals = {s: signal for s, signal in signals.items() 
                                    if signal != SignalType.NEUTRAL}
                
                # Even if no trades, update position values with current prices
                self.model.update_position_values(prices)
                
                # Process any trading signals
                if signals:
                    daily_transactions = self.model.process_signals(
                        current_date,
                        signals,
                        prices
                    )
                    transaction_count += len(daily_transactions)
                else:
                    # Create a snapshot even if no trades to track daily portfolio value
                    self.model._create_snapshot(current_date, [])
                
                # Move to next day
                current_date += timedelta(days=1)
                days_processed += 1
            
            # Calculate final metrics
            results = self._calculate_metrics(self.model.snapshots)
            
            # Update final progress
            if progress_callback:
                progress_callback(1.0)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Simulation error: {str(e)}")
            raise