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
        
    def _analyze_macd_signal(self, 
                        price_data: pd.DataFrame, 
                        macd_data: Dict[str, pd.Series],
                        params: Dict) -> str:
        """
        Analyze MACD signals and return detailed recommendation using custom parameters
        
        Args:
            price_data: DataFrame with price history
            macd_data: Dictionary containing MACD line, signal line and histogram
            params: User's custom recommendation parameters
            
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
            hist_change = latest_hist - prev_hist
            
            # Strong Buy: strength >= strong_buy threshold
            if strength >= params['strong_buy']['trend_strength']:
                return "Strong Buy"
            
            # Buy: strength >= buy threshold (but < strong_buy threshold, implicitly)
            if strength >= params['buy']['trend_strength']:
                return "Buy"
            
            # Strong Sell: strength <= strong_sell threshold
            if strength <= params['strong_sell']['trend_strength']:
                return "Strong Sell"
            
            # Sell: strength <= sell threshold (but > strong_sell threshold, implicitly)
            if strength <= params['sell']['trend_strength']:
                return "Sell"
            
            # Neutral: everything between buy and sell thresholds
            return "Neutral"
            
        except Exception as e:
            self.logger.error(f"Error analyzing MACD signal: {str(e)}")
            return "Neutral"
    
    def analyze_watchlist(self, watchlist: List[str], user_params: Dict) -> List[Dict]:
        """
        Analyze all stocks in watchlist and generate detailed recommendations
        
        Args:
            watchlist: List of stock symbols
            user_params: User's custom recommendation parameters
            
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
                
                # Generate recommendation using user's parameters
                recommendation = self._analyze_macd_signal(price_data, macd_data, user_params)
                
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