"""
Core simulation engine implementation.
File: app/services/simulation/simulation_engine.py
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
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
        """
        Initialize simulation engine
        
        Args:
            market_data: Market data service instance
            technical_analysis: Technical analysis service instance
            parameters: Simulation parameters
        """
        self.market_data = market_data
        self.technical_analysis = technical_analysis
        self.parameters = parameters
        self.logger = logging.getLogger(__name__)
        
        # Initialize simulation model
        self.model = BlueModel(parameters, market_data, technical_analysis)

    def _generate_signals(
        self,
        symbols: List[str],
        date: datetime
    ) -> Dict[str, Tuple[SignalType, float]]:
        """
        Generate trading signals for given symbols on specified date
        
        Args:
            symbols: List of stock symbols
            date: Date to generate signals for
            
        Returns:
            Dict mapping symbols to tuples of (signal_type, price)
        """
        signals = {}
        
        for symbol in symbols:
            try:
                # Get historical data up to date
                lookback = date - timedelta(days=60)  # 60 days for MACD calculation
                price_data, _ = self.market_data.get_stock_data(
                    symbol,
                    lookback,
                    date
                )
                
                # Skip if not enough data
                if len(price_data) < 30:  # Minimum required for MACD
                    continue
                
                # Calculate MACD
                macd_data = self.technical_analysis.calculate_macd(price_data)
                
                # Get latest price
                latest_price = price_data['close'].iloc[-1]
                
                # Get latest MACD values
                macd = macd_data['macd_line'].iloc[-1]
                signal = macd_data['signal_line'].iloc[-1]
                hist = macd_data['histogram'].iloc[-1]
                prev_hist = macd_data['histogram'].iloc[-2]
                
                # Determine signal type based on MACD analysis
                signal_strength = abs(macd - signal)
                hist_change = hist - prev_hist
                
                if hist > 0 and hist_change > 0 and macd > signal:
                    if signal_strength >= 0.5:  # Strong positive divergence
                        signal_type = SignalType.STRONG_BUY
                    else:
                        signal_type = SignalType.BUY
                elif hist < 0 and hist_change < 0 and macd < signal:
                    if signal_strength >= 0.5:  # Strong negative divergence
                        signal_type = SignalType.STRONG_SELL
                    else:
                        signal_type = SignalType.SELL
                else:
                    signal_type = SignalType.NEUTRAL
                
                signals[symbol] = (signal_type, latest_price)
                
            except Exception as e:
                self.logger.error(f"Error generating signal for {symbol}: {str(e)}")
                continue
        
        return signals

    def _calculate_metrics(
        self,
        snapshots: List[PortfolioSnapshot],
        risk_free_rate: float = 0.02
    ) -> SimulationResults:
        """
        Calculate performance metrics from simulation results
        
        Args:
            snapshots: List of daily portfolio snapshots
            risk_free_rate: Annual risk-free rate for Sharpe ratio
            
        Returns:
            SimulationResults instance with calculated metrics
        """
        # Extract daily values
        dates = [s.date for s in snapshots]
        portfolio_values = pd.Series(
            [s.total_value for s in snapshots],
            index=dates
        )
        cash_values = pd.Series(
            [s.cash for s in snapshots],
            index=dates
        )
        positions_values = pd.Series(
            [s.total_invested for s in snapshots],
            index=dates
        )
        
        # Calculate daily returns
        daily_returns = portfolio_values.pct_change().fillna(0)
        
        # Calculate metrics
        initial_value = portfolio_values.iloc[0]
        final_value = portfolio_values.iloc[-1]
        total_return = final_value - initial_value
        total_return_pct = (total_return / initial_value) * 100
        
        # Calculate maximum drawdown
        rolling_max = portfolio_values.expanding().max()
        drawdowns = (portfolio_values - rolling_max) / rolling_max
        max_drawdown = abs(drawdowns.min()) * 100
        
        # Get all transactions
        transactions = [
            t for s in snapshots for t in s.daily_transactions
        ]
        
        # Calculate win rate
        closed_positions = [
            t for t in transactions
            if t.transaction_type == TransactionType.SELL
        ]
        winning_trades = len([
            t for t in closed_positions
            if t.total_amount > 0  # Profitable trade
        ])
        win_rate = (
            winning_trades / len(closed_positions)
            if closed_positions else 0
        ) * 100
        
        # Calculate average holding period
        holding_periods = []
        position_start_dates = {}
        
        for t in transactions:
            if t.transaction_type == TransactionType.BUY:
                position_start_dates[t.symbol] = t.date
            elif t.transaction_type == TransactionType.SELL:
                if t.symbol in position_start_dates:
                    start_date = position_start_dates[t.symbol]
                    holding_period = (t.date - start_date).days
                    holding_periods.append(holding_period)
        
        avg_holding_period = (
            sum(holding_periods) / len(holding_periods)
            if holding_periods else 0
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
            initial_capital=initial_value,
            final_portfolio_value=final_value,
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
        progress_callback=None
    ) -> Optional[SimulationResults]:
        """
        Run portfolio simulation
        
        Args:
            watchlist: List of stock symbols to trade
            progress_callback: Optional callback for progress updates
            
        Returns:
            SimulationResults if successful, None if error
        """
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
                    progress = days_processed / total_days
                    progress_callback(progress)
                
                # Generate signals for watchlist stocks
                signals = self._generate_signals(watchlist, current_date)
                
                # Convert signals to format expected by model
                signal_dict = {
                    symbol: signal_data[0]
                    for symbol, signal_data in signals.items()
                }
                price_dict = {
                    symbol: signal_data[1]
                    for symbol, signal_data in signals.items()
                }
                
                # Process signals through model
                self.model.process_signals(
                    current_date,
                    signal_dict,
                    price_dict
                )
                
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
            return None