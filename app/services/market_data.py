"""
Updated market data service for fetching and managing stock data.
File: app/services/market_data.py
"""

import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, timedelta, date
from typing import Optional, Tuple, Dict, Union
from pathlib import Path
import sqlite3
import json
from io import StringIO
import time

class MarketDataService:
    """Service for fetching and managing stock market data"""
    
    def __init__(self, cache_dir: str = "./data/cache"):
        """
        Initialize the market data service
        
        Args:
            cache_dir: Directory for storing cached data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize SQLite connection for caching
        self.db_path = self.cache_dir / "market_data.db"
        self._init_cache_db()
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
        
        # Cache duration constants
        self.CURRENT_DAY_CACHE_DURATION = timedelta(minutes=15)
        self.HISTORICAL_CACHE_DURATION = timedelta(days=1)
        self.COMPANY_INFO_CACHE_DURATION = timedelta(days=7)
        
        # Rate limiting
        self.last_api_call = 0
        self.MIN_API_CALL_INTERVAL = 0.5  # seconds between API calls

    def _init_cache_db(self):
        """Initialize SQLite database for caching"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_data_cache (
                    key TEXT PRIMARY KEY,
                    data TEXT,
                    timestamp DATETIME,
                    expiry DATETIME
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expiry ON market_data_cache(expiry)")

    def _get_cached_data(self, key: str) -> Optional[pd.DataFrame]:
        """Retrieve cached data if available and not expired"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute(
                    "SELECT data, expiry FROM market_data_cache WHERE key = ?",
                    (key,)
                ).fetchone()
                
                if result and datetime.now() < datetime.fromisoformat(result[1]):
                    return pd.read_json(StringIO(result[0]))
                return None
        except Exception as e:
            self.logger.warning(f"Cache retrieval failed for key {key}: {str(e)}")
            return None

    def _cache_data(self, key: str, data: pd.DataFrame, duration: timedelta):
        """Store data in cache with expiration"""
        try:
            expiry = datetime.now() + duration
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO market_data_cache (key, data, timestamp, expiry)
                    VALUES (?, ?, ?, ?)
                    """,
                    (key, data.to_json(), datetime.now().isoformat(), expiry.isoformat())
                )
        except Exception as e:
            self.logger.warning(f"Cache storage failed for key {key}: {str(e)}")
    
    def _rate_limit(self):
        """Implement rate limiting for API calls"""
        now = time.time()
        elapsed = now - self.last_api_call
        if elapsed < self.MIN_API_CALL_INTERVAL:
            time.sleep(self.MIN_API_CALL_INTERVAL - elapsed)
        self.last_api_call = time.time()

    def get_stock_data(
        self,
        symbol: str,
        start_date: Union[datetime, date],
        end_date: Union[datetime, date]
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Fetch stock data for given symbol and date range
        
        Args:
            symbol: Stock ticker symbol
            start_date: Start date for historical data (datetime or date)
            end_date: End date for historical data (datetime or date)
            
        Returns:
            Tuple of (price_data, metadata)
        """
        # Convert dates to string format for cache key
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        cache_key = f"stock_data_{symbol}_{start_str}_{end_str}"
        
        # Check cache first
        cached_data = self._get_cached_data(cache_key)
        if cached_data is not None:
            return cached_data, self._get_stock_metadata(symbol)
        
        try:
            # Rate limit API calls
            self._rate_limit()
            
            # Download data directly using download method
            data = yf.download(
                symbol,
                start=start_date,
                end=end_date + timedelta(days=1),  # Add one day to ensure end_date is included
                progress=False
            )
            
            if data.empty:
                raise ValueError(f"No data available for symbol {symbol}")
            
            # Process the data
            data.index = pd.to_datetime(data.index)
            
            # Handle multi-index columns if present (this happens with multiple symbols)
            if isinstance(data.columns, pd.MultiIndex):
                # self.logger.info(f"Handling multi-index columns for {symbol}")
                
                # Create a new DataFrame with single-level columns
                processed_data = pd.DataFrame(index=data.index)
                
                # Map standard column names
                column_mapping = {
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume',
                    'Adj Close': 'adj_close'
                }
                
                # Find the symbol in the columns and extract its data
                for col_type in ['Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']:
                    if (col_type, symbol) in data.columns:
                        processed_data[column_mapping[col_type]] = data[(col_type, symbol)]
                    
                # Check if we successfully extracted the data
                if processed_data.empty:
                    # Try an alternative approach
                    # Drop the second level if it exists
                    if isinstance(data.columns, pd.MultiIndex):
                        data = data.droplevel(1, axis=1)
                    
                    # Now rename the columns
                    data = data.rename(columns={
                        'Open': 'open',
                        'High': 'high',
                        'Low': 'low',
                        'Close': 'close',
                        'Volume': 'volume',
                        'Adj Close': 'adj_close'
                    })
                else:
                    data = processed_data
            else:
                # Regular single-level columns
                data = data.rename(columns={
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume',
                    'Adj Close': 'adj_close'
                })
            
            # Safety check: ensure 'close' column exists
            if 'close' not in data.columns:
                # Try to find a suitable column
                for col in data.columns:
                    if 'Close' in str(col) or 'close' in str(col):
                        data['close'] = data[col]
                        break
                
                # If still not found, use Adj Close if available
                if 'close' not in data.columns and 'Adj Close' in data.columns:
                    data['close'] = data['Adj Close']
                elif 'close' not in data.columns and 'adj_close' in data.columns:
                    data['close'] = data['adj_close']
                
                # If we still can't find it, raise an error
                if 'close' not in data.columns:
                    self.logger.error(f"Could not find price data for {symbol}. Columns: {data.columns.tolist()}")
            
            # Cache the data
            cache_duration = (
                self.CURRENT_DAY_CACHE_DURATION
                if end_date.strftime('%Y-%m-%d') == datetime.now().strftime('%Y-%m-%d')
                else self.HISTORICAL_CACHE_DURATION
            )
            self._cache_data(cache_key, data, cache_duration)
            
            return data, self._get_stock_metadata(symbol)
            
        except Exception as e:
            self.logger.error(f"Error fetching data for {symbol}: {str(e)}")
            raise RuntimeError(f"Failed to fetch stock data for {symbol}") from e

    def _get_stock_metadata(self, symbol: str) -> Dict:
        """Get stock metadata including company information"""
        cache_key = f"metadata_{symbol}"
        
        cached_data = self._get_cached_data(cache_key)
        if cached_data is not None:
            return cached_data.iloc[0].to_dict()
        
        try:
            # Rate limit API calls
            self._rate_limit()
            
            # Initialize Ticker - this gets basic info
            stock = yf.Ticker(symbol)
            
            # Handle the case where info is not available or different in structure
            try:
                info = stock.info
                company_name = info.get('longName', info.get('shortName', symbol))
                sector = info.get('sector', '')
                industry = info.get('industry', '')
                currency = info.get('currency', 'USD')
                exchange = info.get('exchange', '')
            except Exception as e:
                self.logger.warning(f"Could not get full info for {symbol}: {str(e)}")
                info = {}
                # Try to get at least the company name
                try:
                    company_name = stock.ticker
                except:
                    company_name = symbol
                sector = ''
                industry = ''
                currency = 'USD'
                exchange = ''
            
            metadata = {
                'symbol': symbol,
                'company_name': company_name,
                'sector': sector,
                'industry': industry,
                'currency': currency,
                'exchange': exchange,
            }
            
            # Cache metadata
            self._cache_data(
                cache_key,
                pd.DataFrame([metadata]),
                self.COMPANY_INFO_CACHE_DURATION
            )
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error fetching metadata for {symbol}: {str(e)}")
            return {
                'symbol': symbol,
                'company_name': symbol,
                'sector': '',
                'industry': '',
                'currency': 'USD',
                'exchange': ''
            }

    def get_latest_price(self, symbol: str) -> float:
        """
        Get latest stock price with improved handling for newer yfinance versions
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Latest price as float
        """
        cache_key = f"latest_price_{symbol}"
        
        # Check cache first
        cached_data = self._get_cached_data(cache_key)
        if cached_data is not None:
            try:
                return float(cached_data.iloc[-1]['close'])
            except Exception:
                # If there's an issue with the cached data, continue to fetch fresh data
                pass
        
        try:
            # Rate limit API calls
            self._rate_limit()
            
            # Method 1: Try downloading with period='1d' first
            try:
                data = yf.download(
                    symbol,
                    period='1d',  # Just get today's data
                    progress=False,
                    timeout=10    # Add timeout to prevent hanging
                )
                
                if not data.empty:
                    latest_price = float(data['Close'].iloc[-1])
                    
                    # Cache for 15 minutes
                    self._cache_data(
                        cache_key,
                        pd.DataFrame({'close': [latest_price]}),
                        self.CURRENT_DAY_CACHE_DURATION
                    )
                    
                    return latest_price
            except Exception as e:
                self.logger.warning(f"Method 1 failed for {symbol}: {str(e)}")
            
            # Method 2: If that fails, try using Ticker.history
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period='1d')
                
                if not data.empty:
                    latest_price = float(data['Close'].iloc[-1])
                    
                    # Cache for 15 minutes
                    self._cache_data(
                        cache_key,
                        pd.DataFrame({'close': [latest_price]}),
                        self.CURRENT_DAY_CACHE_DURATION
                    )
                    
                    return latest_price
            except Exception as e:
                self.logger.warning(f"Method 2 failed for {symbol}: {str(e)}")
            
            # Method 3: Last resort - get the price from a longer period
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)
            
            data = yf.download(
                symbol,
                start=start_date,
                end=end_date,
                progress=False
            )
            
            if data.empty:
                raise ValueError(f"No price data available for {symbol}")
            
            latest_price = float(data['Close'].iloc[-1])
            
            # Cache for 15 minutes
            self._cache_data(
                cache_key,
                pd.DataFrame({'close': [latest_price]}),
                self.CURRENT_DAY_CACHE_DURATION
            )
            
            return latest_price
                
        except Exception as e:
            self.logger.error(f"Error fetching latest price for {symbol}: {str(e)}")
            raise RuntimeError(f"Failed to fetch latest price for {symbol}") from e

    def cleanup_cache(self):
        """Remove expired cache entries"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "DELETE FROM market_data_cache WHERE expiry < ?",
                    (datetime.now().isoformat(),)
                )
        except Exception as e:
            self.logger.error(f"Cache cleanup failed: {str(e)}")