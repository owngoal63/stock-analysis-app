"""
Technical analysis service handling MACD and other indicators.
File: app/services/technical_analysis.py
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

class TechnicalAnalysisService:
    """Handles calculation of technical indicators"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def calculate_macd(self, 
                      data: pd.DataFrame, 
                      fast_period: int = 12, 
                      slow_period: int = 26, 
                      signal_period: int = 9) -> Dict[str, pd.Series]:
        """
        Calculate MACD indicator for given price data
        
        Args:
            data: DataFrame with 'close' price column
            fast_period: Period for fast EMA
            slow_period: Period for slow EMA
            signal_period: Period for signal line
            
        Returns:
            Dict containing MACD line, signal line, and histogram
        """
        try:
            # Validate input data
            if 'close' not in data.columns:
                raise ValueError("Input DataFrame must contain 'close' column")
            
            # Calculate EMAs
            fast_ema = data['close'].ewm(span=fast_period, adjust=False).mean()
            slow_ema = data['close'].ewm(span=slow_period, adjust=False).mean()
            
            # Calculate MACD line
            macd_line = fast_ema - slow_ema
            
            # Calculate signal line
            signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
            
            # Calculate histogram
            histogram = macd_line - signal_line
            
            return {
                'macd_line': macd_line,
                'signal_line': signal_line,
                'histogram': histogram
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating MACD: {str(e)}")
            raise

    def calculate_rsi(self, 
                     data: pd.DataFrame, 
                     period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index
        
        Args:
            data: DataFrame with 'close' price column
            period: RSI period
            
        Returns:
            Series containing RSI values
        """
        try:
            if 'close' not in data.columns:
                raise ValueError("Input DataFrame must contain 'close' column")
            
            # Calculate price changes
            delta = data['close'].diff()
            
            # Separate gains and losses
            gain = (delta.where(delta > 0, 0))
            loss = (-delta.where(delta < 0, 0))
            
            # Calculate average gain and loss
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            
            # Calculate RS and RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            self.logger.error(f"Error calculating RSI: {str(e)}")
            raise

    def get_moving_averages(self, 
                           data: pd.DataFrame, 
                           periods: List[int] = [20, 50, 200]) -> Dict[int, pd.Series]:
        """
        Calculate simple moving averages for specified periods
        
        Args:
            data: DataFrame with 'close' price column
            periods: List of periods for MA calculation
            
        Returns:
            Dict mapping periods to their MA Series
        """
        try:
            if 'close' not in data.columns:
                raise ValueError("Input DataFrame must contain 'close' column")
            
            return {
                period: data['close'].rolling(window=period).mean()
                for period in periods
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating moving averages: {str(e)}")
            raise

    def analyze_patterns(self, data: pd.DataFrame) -> Dict[str, List[dict]]:
        """
        Identify technical patterns in the price data
        
        Args:
            data: DataFrame with OHLC price data
            
        Returns:
            Dict of identified patterns with their locations
        """
        try:
            required_columns = ['open', 'high', 'low', 'close']
            if not all(col in data.columns for col in required_columns):
                raise ValueError("Input DataFrame must contain OHLC columns")
            
            patterns = {
                'support_levels': [],
                'resistance_levels': [],
                'trend_lines': []
            }
            
            # Calculate potential support/resistance levels using local min/max
            window = 20  # Look for local min/max in 20-day windows
            
            # Find local minimums (support levels)
            data['local_min'] = data['low'].rolling(window=window, center=True).min()
            support_levels = data[data['low'] == data['local_min']]['low'].unique()
            patterns['support_levels'] = sorted(support_levels)[-3:]  # Keep top 3 recent levels
            
            # Find local maximums (resistance levels)
            data['local_max'] = data['high'].rolling(window=window, center=True).max()
            resistance_levels = data[data['high'] == data['local_max']]['high'].unique()
            patterns['resistance_levels'] = sorted(resistance_levels)[-3:]  # Keep top 3 recent levels
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Error analyzing patterns: {str(e)}")
            raise

    def generate_signals(self, data: pd.DataFrame) -> Dict[str, List[dict]]:
        """
        Generate trading signals based on technical indicators
        
        Args:
            data: DataFrame with OHLC price data
            
        Returns:
            Dict of trading signals with their timestamps
        """
        try:
            signals = {
                'macd': [],
                'rsi': [],
                'ma_crossover': []
            }
            
            # Calculate indicators
            macd_data = self.calculate_macd(data)
            rsi_data = self.calculate_rsi(data)
            mas = self.get_moving_averages(data, [20, 50])
            
            # MACD signals
            macd_crossovers = (
                (macd_data['macd_line'] > macd_data['signal_line']) & 
                (macd_data['macd_line'].shift(1) <= macd_data['signal_line'].shift(1))
            )
            macd_crossunders = (
                (macd_data['macd_line'] < macd_data['signal_line']) & 
                (macd_data['macd_line'].shift(1) >= macd_data['signal_line'].shift(1))
            )
            
            # Generate MACD signals
            for date in data.index[macd_crossovers]:
                signals['macd'].append({
                    'date': date,
                    'type': 'buy',
                    'indicator': 'macd',
                    'price': data.loc[date, 'close']
                })
            
            for date in data.index[macd_crossunders]:
                signals['macd'].append({
                    'date': date,
                    'type': 'sell',
                    'indicator': 'macd',
                    'price': data.loc[date, 'close']
                })
            
            # RSI signals
            rsi_oversold = (rsi_data < 30) & (rsi_data.shift(1) >= 30)
            rsi_overbought = (rsi_data > 70) & (rsi_data.shift(1) <= 70)
            
            for date in data.index[rsi_oversold]:
                signals['rsi'].append({
                    'date': date,
                    'type': 'buy',
                    'indicator': 'rsi',
                    'price': data.loc[date, 'close']
                })
            
            for date in data.index[rsi_overbought]:
                signals['rsi'].append({
                    'date': date,
                    'type': 'sell',
                    'indicator': 'rsi',
                    'price': data.loc[date, 'close']
                })
            
            # Moving Average crossover signals
            ma_crossovers = (
                (mas[20] > mas[50]) & 
                (mas[20].shift(1) <= mas[50].shift(1))
            )
            ma_crossunders = (
                (mas[20] < mas[50]) & 
                (mas[20].shift(1) >= mas[50].shift(1))
            )
            
            for date in data.index[ma_crossovers]:
                signals['ma_crossover'].append({
                    'date': date,
                    'type': 'buy',
                    'indicator': 'ma_crossover',
                    'price': data.loc[date, 'close']
                })
            
            for date in data.index[ma_crossunders]:
                signals['ma_crossover'].append({
                    'date': date,
                    'type': 'sell',
                    'indicator': 'ma_crossover',
                    'price': data.loc[date, 'close']
                })
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating signals: {str(e)}")
            raise