"""
Market data service for fetching and managing stock data.
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
            # Fetch data from yfinance
            stock = yf.Ticker(symbol)
            data = stock.history(start=start_date, end=end_date)
            
            if data.empty:
                raise ValueError(f"No data available for symbol {symbol}")
            
            # Process the data
            data.index = pd.to_datetime(data.index)
            data = data.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
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
            stock = yf.Ticker(symbol)
            info = stock.info
            metadata = {
                'symbol': symbol,
                'company_name': info.get('longName', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'currency': info.get('currency', 'USD'),
                'exchange': info.get('exchange', ''),
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
        Get latest stock price
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Latest price as float
        """
        cache_key = f"latest_price_{symbol}"
        
        cached_data = self._get_cached_data(cache_key)
        if cached_data is not None:
            return cached_data.iloc[-1]['close']
        
        try:
            stock = yf.Ticker(symbol)
            data = stock.history(period='1d')
            
            if data.empty:
                raise ValueError(f"No price data available for {symbol}")
            
            latest_price = data['Close'].iloc[-1]
            
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