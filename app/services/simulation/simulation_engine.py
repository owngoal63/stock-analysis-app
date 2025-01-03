"""
Core simulation engine implementation.
File: app/services/simulation/simulation_engine.py
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable
import pandas as pd
import numpy as np
from dataclasses import dataclass

from app.services.market_data import MarketDataService
from app.services.technical_analysis import TechnicalAnalysisService
from app.services.simulation.models.parameters import SimulationParameters
from app.services.simulation.models.trading import (
    Position, Transaction, PortfolioSnapshot, SignalType, TransactionType
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
                
                if hist > 0 and hist_change > 0 and macd > signal:
                    if signal_strength >= 0.5:
                        signals[symbol] = SignalType.STRONG_BUY
                    else:
                        signals[symbol] = SignalType.BUY
                elif hist < 0 and hist_change < 0 and macd < signal:
                    if signal_strength >= 0.5:
                        signals[symbol] = SignalType.STRONG_SELL
                    else:
                        signals[symbol] = SignalType.SELL
                else:
                    signals[symbol] = SignalType.NEUTRAL
                    
            except Exception as e:
                self.logger.error(f"Error processing {symbol}: {str(e)}")
                continue
                
        return signals, prices

    def _calculate_metrics(
        self,
        snapshots: List[PortfolioSnapshot],
        risk_free_rate: float = 0.02
    ) -> SimulationResults:
        """Calculate performance metrics from simulation results"""
        # Extract daily values using current day's prices
        dates = [s.date for s in snapshots]
        portfolio_values = pd.Series(
            [s.total_value for s in snapshots],  # total_value uses current prices
            index=dates
        )
        cash_values = pd.Series(
            [s.cash for s in snapshots],
            index=dates
        )
        positions_values = pd.Series(
            [s.total_invested for s in snapshots],  # total_invested uses current prices
            index=dates
        )
        
        # Calculate daily returns using current day's values
        daily_returns = portfolio_values.pct_change().fillna(0)
        
        # Calculate metrics
        total_return = portfolio_values.iloc[-1] - self.parameters.initial_capital
        total_return_pct = (total_return / self.parameters.initial_capital) * 100
        
        # Calculate maximum drawdown
        rolling_max = portfolio_values.expanding().max()
        drawdowns = (portfolio_values - rolling_max) / rolling_max
        max_drawdown = abs(drawdowns.min()) * 100
        
        # Get all transactions
        transactions = [t for s in snapshots for t in s.daily_transactions]
        
        # Calculate win rate and holding periods
        completed_trades = []
        position_start_dates = {}
        
        for t in transactions:
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
                while position_start_dates[t.symbol] and t.shares > 0:
                    buy_position = position_start_dates[t.symbol][0]
                    shares_to_sell = min(buy_position['shares'], t.shares)
                    
                    # Calculate profit/loss for this part of the position
                    buy_cost = shares_to_sell * buy_position['price'] + (buy_position['fees'] * shares_to_sell / buy_position['shares'])
                    sell_proceeds = shares_to_sell * t.price - (t.fees * shares_to_sell / t.shares)
                    profit = sell_proceeds - buy_cost
                    
                    completed_trades.append({
                        'profit': profit,
                        'holding_period': (t.date - buy_position['date']).days
                    })
                    
                    # Update remaining shares
                    t.shares -= shares_to_sell
                    buy_position['shares'] -= shares_to_sell
                    
                    if buy_position['shares'] == 0:
                        position_start_dates[t.symbol].pop(0)
                    
                if not position_start_dates[t.symbol]:
                    del position_start_dates[t.symbol]
        
        # Calculate win rate
        winning_trades = len([t for t in completed_trades if t['profit'] > 0])
        win_rate = (winning_trades / len(completed_trades) * 100) if completed_trades else 0
        
        # Calculate average holding period
        avg_holding_period = (
            sum(t['holding_period'] for t in completed_trades) / len(completed_trades)
            if completed_trades else 0
        )
        
        # Calculate Sharpe ratio
        daily_rf_rate = (1 + risk_free_rate) ** (1/252) - 1
        excess_returns = daily_returns - daily_rf_rate
        sharpe_ratio = (
            (excess_returns.mean() * 252) /
            (excess_returns.std() * (252 ** 0.5))
            if excess_returns.std() != 0 else 0
        )
        
        return SimulationResults(
            initial_capital=self.parameters.initial_capital,
            final_portfolio_value=portfolio_values.iloc[-1],
            total_return=total_return,
            total_return_percent=total_return_pct,
            max_drawdown=max_drawdown,
            number_of_trades=len(transactions),
            win_rate=win_rate,
            avg_holding_period=avg_holding_period,
            sharpe_ratio=sharpe_ratio,
            transactions=transactions,
            portfolio_values=portfolio_values,
            cash_values=cash_values,
            positions_values=positions_values,
            daily_returns=daily_returns
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
            
            while current_date <= end_date:
                # Update progress
                if progress_callback:
                    progress = min(days_processed / total_days, 1.0)
                    progress_callback(progress)
                
                # Generate signals and get current prices
                signals, prices = self._generate_signals_and_prices(watchlist, current_date)
                
                # Even if no trades, update position values with current prices
                self.model.update_position_values(prices)
                
                # Process any trading signals
                if signals:
                    self.model.process_signals(
                        current_date,
                        signals,
                        prices
                    )
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
