"""
Enhanced watchlist analysis service with granular recommendations.
File: app/services/watchlist_analyzer.py
"""

from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime, timedelta
import logging
import numpy as np

from app.services.market_data import MarketDataService
from app.services.technical_analysis import TechnicalAnalysisService

class WatchlistAnalyzer:
    """Service for analyzing watchlist stocks and generating detailed recommendations"""
    
    def __init__(self, market_data: MarketDataService, technical_analysis: TechnicalAnalysisService):
        """
        Initialize watchlist analyzer
        
        Args:
            market_data: MarketDataService instance
            technical_analysis: TechnicalAnalysisService instance
        """
        self.market_data = market_data
        self.technical_analysis = technical_analysis
        self.logger = logging.getLogger(__name__)
    
    def _calculate_trend_strength(self, price_data: pd.DataFrame, macd_data: Dict[str, pd.Series]) -> float:
        """
        Calculate trend strength based on price action and MACD
        
        Args:
            price_data: DataFrame with price history
            macd_data: Dictionary containing MACD indicators
            
        Returns:
            float: Trend strength score between -1 and 1
        """
        try:
            # Get recent data (last 10 periods)
            recent_hist = macd_data['histogram'].tail(10)
            recent_price = price_data['close'].tail(10)
            recent_macd = macd_data['macd_line'].tail(10)
            recent_signal = macd_data['signal_line'].tail(10)
            
            # Calculate various strength indicators
            hist_strength = recent_hist.mean() / recent_hist.std() if recent_hist.std() != 0 else 0
            price_trend = (recent_price.pct_change().mean() * 100) * 10  # Scaled percentage change
            macd_trend = (recent_macd - recent_signal).mean()
            
            # Combine indicators into overall strength score
            strength_score = (
                np.tanh(hist_strength) * 0.4 +    # Histogram contribution
                np.tanh(price_trend) * 0.3 +      # Price trend contribution
                np.tanh(macd_trend) * 0.3         # MACD trend contribution
            )
            
            return max(min(strength_score, 1), -1)  # Bound between -1 and 1
            
        except Exception as e:
            self.logger.error(f"Error calculating trend strength: {str(e)}")
            return 0
        
    def _analyze_macd_signal(self, price_data: pd.DataFrame, macd_data: Dict[str, pd.Series]) -> str:
        """
        Analyze MACD signals and return detailed recommendation
        
        Args:
            price_data: DataFrame with price history
            macd_data: Dictionary containing MACD line, signal line and histogram
            
        Returns:
            str: 'Strong Buy', 'Buy', 'Neutral', 'Sell', or 'Strong Sell' recommendation
        """
        try:
            # Get latest values
            latest_macd = macd_data['macd_line'].iloc[-1]
            latest_signal = macd_data['signal_line'].iloc[-1]
            latest_hist = macd_data['histogram'].iloc[-1]
            prev_hist = macd_data['histogram'].iloc[-2]
            
            # Calculate trend strength
            strength = self._calculate_trend_strength(price_data, macd_data)
            
            # Strong Buy conditions
            if (latest_macd > latest_signal and          # MACD above signal line
                latest_hist > 0 and                      # Positive histogram
                latest_hist > prev_hist and              # Increasing histogram
                strength > 0.5):                         # Strong positive trend
                return "Strong Buy"
            
            # Buy conditions
            elif (latest_macd > latest_signal and        # MACD above signal line
                  latest_hist > 0 and                    # Positive histogram
                  strength > 0):                         # Positive trend
                return "Buy"
            
            # Strong Sell conditions
            elif (latest_macd < latest_signal and        # MACD below signal line
                  latest_hist < 0 and                    # Negative histogram
                  latest_hist < prev_hist and            # Decreasing histogram
                  strength < -0.5):                      # Strong negative trend
                return "Strong Sell"
            
            # Sell conditions
            elif (latest_macd < latest_signal and        # MACD below signal line
                  latest_hist < 0 and                    # Negative histogram
                  strength < 0):                         # Negative trend
                return "Sell"
            
            # Neutral conditions
            return "Neutral"
            
        except Exception as e:
            self.logger.error(f"Error analyzing MACD signal: {str(e)}")
            return "Neutral"
    
    def analyze_watchlist(self, watchlist: List[str]) -> List[Dict]:
        """
        Analyze all stocks in watchlist and generate detailed recommendations
        
        Args:
            watchlist: List of stock symbols
            
        Returns:
            List of dictionaries containing analysis results
        """
        results = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)  # Get 60 days of data for analysis
        
        for symbol in watchlist:
            try:
                # Get stock data
                price_data, metadata = self.market_data.get_stock_data(
                    symbol,
                    start_date,
                    end_date
                )
                
                # Calculate MACD
                macd_data = self.technical_analysis.calculate_macd(price_data)
                
                # Get latest price
                latest_price = self.market_data.get_latest_price(symbol)
                
                # Calculate trend strength
                strength = self._calculate_trend_strength(price_data, macd_data)
                
                # Generate recommendation
                recommendation = self._analyze_macd_signal(price_data, macd_data)
                
                # Get latest MACD values
                latest_macd = macd_data['macd_line'].iloc[-1]
                latest_signal = macd_data['signal_line'].iloc[-1]
                latest_hist = macd_data['histogram'].iloc[-1]
                
                # Calculate price change
                price_change = (
                    (price_data['close'].iloc[-1] - price_data['close'].iloc[-2])
                    / price_data['close'].iloc[-2] * 100
                )
                
                # Compile analysis result
                result = {
                    'symbol': symbol,
                    'company_name': metadata.get('company_name', symbol),
                    'current_price': latest_price,
                    'price_change_pct': price_change,
                    'recommendation': recommendation,
                    'trend_strength': strength,
                    'macd_line': latest_macd,
                    'signal_line': latest_signal,
                    'histogram': latest_hist,
                    'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'sector': metadata.get('sector', 'N/A'),
                }
                
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Error analyzing {symbol}: {str(e)}")
                results.append({
                    'symbol': symbol,
                    'error': str(e),
                    'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
        return results