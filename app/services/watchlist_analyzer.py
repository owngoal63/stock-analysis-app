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
        Calculate trend strength based on price action and MACD with improved robustness
        
        Args:
            price_data: DataFrame with price history
            macd_data: Dictionary containing MACD indicators
            
        Returns:
            float: Trend strength score between -1 and 1
        """
        try:
            # Make sure we're using numeric data with no missing values
            # Get recent data (last 10 periods or less if not enough data)
            periods = min(10, len(price_data))
            if periods < 3:  # Need at least 3 data points for meaningful analysis
                return 0.0
                
            # Convert to numeric and handle NaN values
            try:
                recent_hist = pd.to_numeric(macd_data['histogram'].tail(periods), errors='coerce').fillna(0)
                recent_price = pd.to_numeric(price_data['close'].tail(periods), errors='coerce').fillna(0)
                recent_macd = pd.to_numeric(macd_data['macd_line'].tail(periods), errors='coerce').fillna(0)
                recent_signal = pd.to_numeric(macd_data['signal_line'].tail(periods), errors='coerce').fillna(0)
            except KeyError as e:
                # If any key is missing, log the error and use alternate column names
                self.logger.warning(f"Key error calculating trend strength: {e}")
                # Try alternate column names
                recent_price = pd.to_numeric(
                    price_data.get('close', price_data.get('Close', pd.Series([0] * periods))).tail(periods),
                    errors='coerce'
                ).fillna(0)
                # For the rest, we'll use the fallbacks from the except block below
                raise
                
            # Add debugging to see the values we're working with
            # print(f"Recent histogram values: {recent_hist.values.tolist()}")
            # print(f"Recent price values: {recent_price.values.tolist()}")
            # print(f"Recent MACD values: {recent_macd.values.tolist()}")
            
            # Calculate various strength indicators
            if recent_hist.std() != 0:
                hist_strength = recent_hist.mean() / recent_hist.std()
            else:
                hist_strength = 0
                
            # Calculate price trend (scaled percentage change)
            price_pct_changes = recent_price.pct_change().dropna()
            if not price_pct_changes.empty:
                price_trend = price_pct_changes.mean() * 100 * 10  # Scaled percentage change
            else:
                price_trend = 0
                
            # MACD trend (difference between MACD and signal line)
            macd_trend = (recent_macd - recent_signal).mean()
            
            # Combine indicators into overall strength score
            # Use numpy.tanh to bound values between -1 and 1
            import numpy as np
            strength_score = (
                np.tanh(hist_strength) * 0.4 +    # Histogram contribution
                np.tanh(price_trend) * 0.3 +      # Price trend contribution
                np.tanh(macd_trend) * 0.3         # MACD trend contribution
            )
            
            # Ensure the final score is between -1 and 1
            final_score = max(min(strength_score, 1), -1)
            
            # print(f"Calculated strength score: {final_score}")
            return final_score
            
        except Exception as e:
            # Log the error but don't crash the analysis
            self.logger.error(f"Error calculating trend strength: {str(e)}")
            # Return a small non-zero value to avoid all-zero results
            # Use a small positive or negative value based on the last MACD histogram value
            try:
                last_hist = macd_data['histogram'].iloc[-1]
                return 0.1 if last_hist > 0 else -0.1
            except:
                return 0.0
        
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
            # Get latest values - ensure they're numeric
            try:
                latest_macd = float(macd_data['macd_line'].iloc[-1])
                latest_signal = float(macd_data['signal_line'].iloc[-1])
                latest_hist = float(macd_data['histogram'].iloc[-1])
                prev_hist = float(macd_data['histogram'].iloc[-2]) if len(macd_data['histogram']) > 1 else 0.0
            except (IndexError, KeyError) as e:
                self.logger.warning(f"Error accessing MACD values: {e}")
                # Default to neutral if we can't get the values
                return "Neutral"
                
            # Calculate trend strength - now should return non-zero values
            strength = self._calculate_trend_strength(price_data, macd_data)
            hist_change = latest_hist - prev_hist
            
            # Debug output to verify values
            # print(f"MACD Analysis - Strength: {strength}, Strong Buy Threshold: {params['strong_buy']['trend_strength']}")
            # print(f"Latest MACD: {latest_macd}, Signal: {latest_signal}, Hist: {latest_hist}, Change: {hist_change}")
            
            # Ensure params are valid and have default fallbacks
            strong_buy_threshold = float(params.get('strong_buy', {}).get('trend_strength', 0.5))
            buy_threshold = float(params.get('buy', {}).get('trend_strength', 0.0))
            sell_threshold = float(params.get('sell', {}).get('trend_strength', 0.0))
            strong_sell_threshold = float(params.get('strong_sell', {}).get('trend_strength', -0.5))
            
            # Strong Buy: strength >= strong_buy threshold
            if strength >= strong_buy_threshold:
                return "Strong Buy"
            
            # Buy: strength >= buy threshold (but < strong_buy threshold, implicitly)
            if strength >= buy_threshold:
                return "Buy"
            
            # Strong Sell: strength <= strong_sell threshold
            if strength <= strong_sell_threshold:
                return "Strong Sell"
            
            # Sell: strength <= sell threshold (but > strong_sell threshold, implicitly)
            if strength <= sell_threshold:
                return "Sell"
            
            # Neutral: everything between buy and sell thresholds
            return "Neutral"
            
        except Exception as e:
            self.logger.error(f"Error analyzing MACD signal: {str(e)}")
            return "Neutral"  # Default to neutral on error
    
    def analyze_watchlist(self, watchlist: List[str], user_params: Dict) -> List[Dict]:
        """
        Analyze all stocks in watchlist and generate detailed recommendations
        with fix for float conversion error.
        
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
                
                # Debug print to understand data structure
                self.logger.info(f"Data columns for {symbol}: {price_data.columns.tolist()}")
                self.logger.info(f"Metadata for {symbol}: {type(metadata)}")
                
                # Validate price data before processing
                if price_data.empty:
                    self.logger.warning(f"Empty price data for {symbol}")
                    results.append({
                        'symbol': symbol,
                        'error': "No price data available",
                        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    continue
                
                # Handle potential multi-index columns
                if isinstance(price_data.columns, pd.MultiIndex):
                    # Create a simpler DataFrame
                    simple_data = pd.DataFrame(index=price_data.index)
                    
                    # Look for price data
                    for col in price_data.columns:
                        if isinstance(col, tuple) and len(col) > 0:
                            col_name = col[0].lower() if isinstance(col[0], str) else str(col[0])
                            simple_data[col_name] = price_data[col]
                    
                    price_data = simple_data
                
                # Ensure 'close' column exists
                if 'close' not in price_data.columns:
                    if 'Close' in price_data.columns:
                        price_data['close'] = price_data['Close']
                    else:
                        # Try to find any closing price column
                        close_col = None
                        for col in price_data.columns:
                            if 'close' in str(col).lower() or 'adj' in str(col).lower():
                                close_col = col
                                break
                        
                        if close_col:
                            price_data['close'] = price_data[close_col]
                        else:
                            self.logger.warning(f"No close price found for {symbol}")
                            results.append({
                                'symbol': symbol,
                                'error': "Missing close price data",
                                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })
                            continue
                
                # Calculate MACD
                try:
                    macd_data = self.technical_analysis.calculate_macd(price_data)
                except Exception as e:
                    self.logger.error(f"MACD calculation failed for {symbol}: {str(e)}")
                    results.append({
                        'symbol': symbol,
                        'error': f"MACD calculation failed: {str(e)}",
                        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    continue
                
                # Get latest price - with improved error handling
                try:
                    # Get latest price from market data service
                    latest_price = self.market_data.get_latest_price(symbol)
                    
                    # Ensure it's a simple numeric value
                    if isinstance(latest_price, dict):
                        self.logger.warning(f"Latest price for {symbol} is a dict: {latest_price}")
                        # Try to extract a numeric value from the dict
                        if 'close' in latest_price:
                            latest_price = latest_price['close']
                        elif 'price' in latest_price:
                            latest_price = latest_price['price']
                        else:
                            # Fall back to last close price from DataFrame
                            latest_price = float(price_data['close'].iloc[-1])
                    
                    # Final conversion to float with safety check
                    try:
                        latest_price = float(latest_price)
                    except (ValueError, TypeError):
                        latest_price = float(price_data['close'].iloc[-1])
                        
                except Exception as e:
                    self.logger.warning(f"Failed to get latest price for {symbol}: {str(e)}")
                    # Use the last close price from price_data as a fallback
                    latest_price = float(price_data['close'].iloc[-1])
                
                # Calculate trend strength
                strength = self._calculate_trend_strength(price_data, macd_data)
                
                # Generate recommendation using user's parameters
                recommendation = self._analyze_macd_signal(price_data, macd_data, user_params)
                
                # Get latest MACD values - with safety checks
                try:
                    latest_macd = float(macd_data['macd_line'].iloc[-1])
                    latest_signal = float(macd_data['signal_line'].iloc[-1])
                    latest_hist = float(macd_data['histogram'].iloc[-1])
                except Exception as e:
                    self.logger.warning(f"Error extracting MACD values for {symbol}: {str(e)}")
                    latest_macd = 0.0
                    latest_signal = 0.0
                    latest_hist = 0.0
                
                # Calculate price change - with additional error handling
                try:
                    if len(price_data) >= 2:
                        price_change = (price_data['close'].iloc[-1] - price_data['close'].iloc[-2]) / price_data['close'].iloc[-2] * 100
                        price_change = float(price_change)  # Ensure it's a simple float
                    else:
                        price_change = 0.0
                except Exception as e:
                    self.logger.warning(f"Error calculating price change for {symbol}: {str(e)}")
                    price_change = 0.0
                
                # Safely extract metadata
                if isinstance(metadata, dict):
                    company_name = metadata.get('company_name', symbol)
                    sector = metadata.get('sector', 'N/A')
                else:
                    company_name = symbol
                    sector = 'N/A'
                    
                # Handle nested dictionary case
                if isinstance(company_name, dict):
                    company_name = company_name.get('name', symbol)
                if isinstance(sector, dict):
                    sector = sector.get('sector', 'N/A')
                    
                # Compile analysis result - ensure all values are simple types
                result = {
                    'symbol': str(symbol),
                    'company_name': str(company_name),
                    'current_price': float(latest_price),
                    'price_change_pct': float(price_change),
                    'recommendation': str(recommendation),
                    'trend_strength': float(strength),
                    'macd_line': float(latest_macd),
                    'signal_line': float(latest_signal),
                    'histogram': float(latest_hist),
                    'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'sector': str(sector),
                }
                
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Error analyzing {symbol}: {str(e)}")
                import traceback
                self.logger.error(traceback.format_exc())
                results.append({
                    'symbol': symbol,
                    'error': str(e),
                    'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
        return results