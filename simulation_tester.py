"""
Standalone simulation testing tool.
File: simulation_tester.py

This script allows step-by-step verification of simulation calculations.
Run this independently of the main application.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import yfinance as yf
import logging
from colorama import Fore, Style, init
import json
import sqlite3
from pathlib import Path
import ast

# Initialize colorama for colored output
init()

@dataclass
class SimulationParameters:
    """Simulation parameters for testing"""
    start_date: datetime
    initial_capital: float
    transaction_fee_percent: float
    investment_rules: Dict[str, float]
    max_single_position_percent: float

    @staticmethod
    def load_from_database(email: str = "gordonlindsay@virginmedia.com") -> Tuple['SimulationParameters', List[str]]:
        """
        Load parameters and watchlist from the app's database
        
        Args:
            email: User's email address
            
        Returns:
            Tuple of (SimulationParameters, watchlist)
        """
        # Define database path relative to app directory
        db_path = Path("./data/auth.db")
        
        if not db_path.exists():
            raise FileNotFoundError(f"Database not found at {db_path}")
        
        try:
            with sqlite3.connect(db_path) as conn:
                # Get user data
                cursor = conn.execute(
                    "SELECT preferences, watchlist FROM users WHERE email = ?",
                    (email,)
                )
                row = cursor.fetchone()
                
                if not row:
                    raise ValueError(f"User {email} not found in database")
                
                # Parse preferences and watchlist
                preferences = ast.literal_eval(row[0]) if row[0] else {}
                watchlist = ast.literal_eval(row[1]) if row[1] else []
                
                # Get simulation parameters from preferences
                sim_params = preferences.get('simulation_parameters', {})
                
                # Create parameters object with defaults if needed
                params = SimulationParameters(
                    start_date=datetime.strptime(
                        sim_params.get('start_date', (datetime.now() - timedelta(days=90)).strftime('%d/%m/%Y')),
                        '%d/%m/%Y'
                    ),
                    initial_capital=float(sim_params.get('initial_capital', 100000.0)),
                    transaction_fee_percent=float(sim_params.get('transaction_fee_percent', 0.1)),
                    investment_rules={
                        'strong_buy_percent': float(sim_params.get('strong_buy_percent', 20.0)),
                        'buy_percent': float(sim_params.get('buy_percent', 10.0)),
                        'sell_percent': float(sim_params.get('sell_percent', 50.0)),
                        'strong_sell_percent': float(sim_params.get('strong_sell_percent', 100.0))
                    },
                    max_single_position_percent=float(sim_params.get('max_single_position_percent', 20.0))
                )
                
                return params, watchlist
                
        except Exception as e:
            raise Exception(f"Error loading parameters from database: {str(e)}")


class SimulationTester:
    def __init__(self, params: SimulationParameters, watchlist: List[str]):
        self.params = params
        self.watchlist = watchlist
        self.current_date = params.start_date
        self.cash = params.initial_capital
        self.positions = {}  # symbol -> {'shares': int, 'avg_price': float}
        self.transactions = []
        self.logger = self._setup_logger()
        
        # Cache for price data to avoid repeated API calls
        self.price_cache = {}
        for symbol in watchlist:
            # Get historical data for the entire simulation period
            self.price_cache[symbol] = self._fetch_historical_data(symbol)

    def _process_signals(
        self,
        symbol: str,
        current_price: float,
        macd: float,
        signal: float,
        hist: float
    ) -> None:
        """
        Process trading signals and execute trades
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            macd: MACD line value
            signal: Signal line value
            hist: Histogram value
        """
        signal_strength = abs(macd - signal)
        
        # Print signal analysis
        print(f"\n{Fore.YELLOW}Signal Analysis for {symbol}:{Style.RESET_ALL}")
        print(f"Signal Strength: {signal_strength:.4f}")
        
        # Determine signal type and execute trade
        if hist > 0 and macd > signal:
            if signal_strength >= 0.5:
                print(f"{Fore.GREEN}STRONG BUY Signal Detected{Style.RESET_ALL}")
                self._execute_trade(symbol, current_price, 'STRONG_BUY')
            else:
                print(f"{Fore.GREEN}BUY Signal Detected{Style.RESET_ALL}")
                self._execute_trade(symbol, current_price, 'BUY')
        elif hist < 0 and macd < signal:
            if signal_strength >= 0.5:
                print(f"{Fore.RED}STRONG SELL Signal Detected{Style.RESET_ALL}")
                self._execute_trade(symbol, current_price, 'STRONG_SELL')
            else:
                print(f"{Fore.RED}SELL Signal Detected{Style.RESET_ALL}")
                self._execute_trade(symbol, current_price, 'SELL')
        else:
            print(f"{Fore.BLUE}No Clear Signal - HOLD{Style.RESET_ALL}")

    def _execute_trade(self, symbol: str, price: float, signal_type: str) -> None:
        """
        Execute a trade based on the signal
        
        Args:
            symbol: Stock symbol
            price: Current stock price
            signal_type: Type of trading signal
        """
        # Calculate total portfolio value for position sizing
        portfolio_value = self.cash + sum(
            pos['shares'] * self._get_current_price(sym) 
            for sym, pos in self.positions.items()
        )
        
        print(f"\n{Fore.CYAN}Trade Analysis:{Style.RESET_ALL}")
        print(f"Portfolio Value: ${portfolio_value:,.2f}")
        print(f"Available Cash: ${self.cash:,.2f}")
        
        # Calculate trade size
        if signal_type in ['STRONG_BUY', 'BUY']:
            # Calculate buy amount
            if signal_type == 'STRONG_BUY':
                base_amount = self.cash * (self.params.investment_rules['strong_buy_percent'] / 100)
                print(f"Strong Buy - Target Investment: {self.params.investment_rules['strong_buy_percent']}% of cash")
            else:
                base_amount = self.cash * (self.params.investment_rules['buy_percent'] / 100)
                print(f"Buy - Target Investment: {self.params.investment_rules['buy_percent']}% of cash")
            
            # Check position size limit
            max_position = portfolio_value * (self.params.max_single_position_percent / 100)
            current_position = self.positions.get(symbol, {'shares': 0, 'avg_price': 0})
            current_value = current_position['shares'] * price
            
            amount = min(base_amount, max_position - current_value)
            
            if amount <= 0:
                print(f"{Fore.RED}Cannot execute buy - position size limit reached{Style.RESET_ALL}")
                print(f"Current Position Value: ${current_value:,.2f}")
                print(f"Maximum Allowed: ${max_position:,.2f}")
                return
            
            # Calculate shares and fees
            shares = int(amount / (price * (1 + self.params.transaction_fee_percent / 100)))
            fees = shares * price * (self.params.transaction_fee_percent / 100)
            total_cost = shares * price + fees
            
            if total_cost > self.cash:
                print(f"{Fore.RED}Cannot execute buy - insufficient funds{Style.RESET_ALL}")
                return
            
            # Execute buy
            if symbol not in self.positions:
                self.positions[symbol] = {'shares': shares, 'avg_price': price}
            else:
                # Update average price
                total_shares = self.positions[symbol]['shares'] + shares
                total_cost = (
                    self.positions[symbol]['shares'] * self.positions[symbol]['avg_price'] +
                    shares * price
                )
                self.positions[symbol] = {
                    'shares': total_shares,
                    'avg_price': total_cost / total_shares
                }
            
            self.cash -= total_cost
            
        else:  # SELL or STRONG_SELL
            if symbol not in self.positions:
                print(f"{Fore.RED}Cannot execute sell - no position in {symbol}{Style.RESET_ALL}")
                return
            
            # Calculate sell amount
            if signal_type == 'STRONG_SELL':
                sell_percent = self.params.investment_rules['strong_sell_percent']
                print(f"Strong Sell - Target Sale: {sell_percent}% of position")
            else:
                sell_percent = self.params.investment_rules['sell_percent']
                print(f"Sell - Target Sale: {sell_percent}% of position")
            
            shares_to_sell = int(self.positions[symbol]['shares'] * (sell_percent / 100))
            
            if shares_to_sell == 0:
                print(f"{Fore.RED}Cannot execute sell - share amount rounds to 0{Style.RESET_ALL}")
                return
            
            # Calculate fees and proceeds
            fees = shares_to_sell * price * (self.params.transaction_fee_percent / 100)
            total_proceeds = shares_to_sell * price - fees
            
            # Execute sell
            self.positions[symbol]['shares'] -= shares_to_sell
            if self.positions[symbol]['shares'] == 0:
                del self.positions[symbol]
            
            self.cash += total_proceeds
        
        # Record transaction
        transaction = {
            'date': self.current_date,
            'type': 'BUY' if signal_type in ['STRONG_BUY', 'BUY'] else 'SELL',
            'symbol': symbol,
            'signal': signal_type,
            'shares': shares if signal_type in ['STRONG_BUY', 'BUY'] else shares_to_sell,
            'price': price,
            'fees': fees,
            'total': -total_cost if signal_type in ['STRONG_BUY', 'BUY'] else total_proceeds
        }
        
        self.transactions.append(transaction)
        
        # Print transaction details
        print(f"\n{Fore.GREEN if 'BUY' in signal_type else Fore.RED}Transaction Executed:{Style.RESET_ALL}")
        print(f"Type: {transaction['type']}")
        print(f"Shares: {transaction['shares']}")
        print(f"Price: ${price:.2f}")
        print(f"Fees: ${fees:.2f}")
        print(f"Total: ${abs(transaction['total']):,.2f}")
        
        # Log transaction
        self.logger.info(f"Transaction executed: {transaction}")

    def _get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        data = self._get_market_data(
            symbol,
            self.current_date,
            self.current_date + timedelta(days=1)
        )
        if data.empty:
            return 0.0
        return data['Close'].iloc[-1]

    def _calculate_macd(
        self,
        prices: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Dict[str, pd.Series]:
        """
        Calculate MACD indicator for given price data
        
        Args:
            prices: Series of price data
            fast_period: Period for fast EMA
            slow_period: Period for slow EMA
            signal_period: Period for signal line
            
        Returns:
            Dict containing MACD line, signal line, and histogram
        """
        try:
            # Calculate exponential moving averages
            fast_ema = prices.ewm(span=fast_period, adjust=False).mean()
            slow_ema = prices.ewm(span=slow_period, adjust=False).mean()
            
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
            # Return empty series with same index as input
            empty_series = pd.Series(0, index=prices.index)
            return {
                'macd_line': empty_series,
                'signal_line': empty_series,
                'histogram': empty_series
            }

    def _setup_logger(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('SimulationTester')
        logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # Create unique log file for each run
        log_file = log_dir / f'simulation_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        
        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Add handler to logger if it doesn't already have one
        if not logger.handlers:
            logger.addHandler(file_handler)
            
        return logger

    def _fetch_historical_data(self, symbol: str) -> pd.DataFrame:
        """Fetch all historical data at once"""
        try:
            end_date = datetime.now()
            stock = yf.Ticker(symbol)
            data = stock.history(
                start=self.params.start_date - timedelta(days=60),  # Extra days for MACD calculation
                end=end_date
            )
            return data
        except Exception as e:
            self.logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return pd.DataFrame()

    def _get_market_data(self, symbol: str, date: datetime, next_date: datetime) -> pd.DataFrame:
        """Get market data for a specific date"""
        if symbol not in self.price_cache:
            return pd.DataFrame()
            
        data = self.price_cache[symbol]
        mask = (data.index.date >= date.date()) & (data.index.date < next_date.date())
        return data[mask]

    def _print_portfolio_status(self):
        """Print current portfolio status with more detailed price information"""
        print(f"\n{Fore.CYAN}Portfolio Status as of {self.current_date.strftime('%Y-%m-%d')}{Style.RESET_ALL}")
        print(f"{'=' * 80}")
        print(f"Cash: ${self.cash:,.2f}")
        
        total_investment = 0
        if self.positions:
            print("\nCurrent Positions:")
            print(f"{'Symbol':<10} {'Shares':<10} {'Avg Price':<12} {'Current Price':<12} {'Current Value':<15} {'P/L':<12}")
            print(f"{'-' * 80}")
            
            for symbol, pos in self.positions.items():
                # Get current day's data
                today_data = self._get_market_data(
                    symbol, 
                    self.current_date, 
                    self.current_date + timedelta(days=1)
                )
                
                if not today_data.empty:
                    current_price = today_data['Close'].iloc[0]
                    # Print daily OHLC prices for verification
                    print(f"\nDaily prices for {symbol}:")
                    print(f"Open: ${today_data['Open'].iloc[0]:.2f}")
                    print(f"High: ${today_data['High'].iloc[0]:.2f}")
                    print(f"Low: ${today_data['Low'].iloc[0]:.2f}")
                    print(f"Close: ${current_price:.2f}")
                    
                    position_value = pos['shares'] * current_price
                    pl = position_value - (pos['shares'] * pos['avg_price'])
                    total_investment += position_value
                    
                    print(f"{symbol:<10} {pos['shares']:<10} ${pos['avg_price']:<11.2f} ${current_price:<11.2f} ${position_value:<14.2f} ${pl:<11.2f}")
                else:
                    print(f"{Fore.RED}No price data available for {symbol} on {self.current_date.strftime('%Y-%m-%d')}{Style.RESET_ALL}")
        
        total_value = self.cash + total_investment
        print(f"\n{Fore.GREEN}Total Portfolio Value: ${total_value:,.2f}{Style.RESET_ALL}")
        print(f"{'=' * 80}")

    def step_simulation(self) -> bool:
        """Execute one step of the simulation"""
        if self.current_date > datetime.now():
            return False

        print(f"\n{Fore.BLUE}Step Date: {self.current_date.strftime('%Y-%m-%d')}{Style.RESET_ALL}")
        
        for symbol in self.watchlist:
            # Get price data
            price_data = self._get_market_data(
                symbol,
                self.current_date - timedelta(days=60),  # For MACD calculation
                self.current_date + timedelta(days=1)
            )
            
            if price_data.empty:
                print(f"{Fore.RED}No price data available for {symbol}{Style.RESET_ALL}")
                continue
                
            current_price = price_data['Close'].iloc[-1]
            
            print(f"\n{Fore.CYAN}Price Data for {symbol}:{Style.RESET_ALL}")
            print(f"Date: {price_data.index[-1].strftime('%Y-%m-%d')}")
            print(f"Open: ${price_data['Open'].iloc[-1]:.2f}")
            print(f"High: ${price_data['High'].iloc[-1]:.2f}")
            print(f"Low: ${price_data['Low'].iloc[-1]:.2f}")
            print(f"Close: ${current_price:.2f}")
            
            # Calculate MACD
            macd_data = self._calculate_macd(price_data['Close'])
            
            # Print technical indicators
            print(f"\n{Fore.CYAN}Technical Indicators for {symbol}:{Style.RESET_ALL}")
            print(f"MACD: {macd_data['macd_line'].iloc[-1]:.4f}")
            print(f"Signal: {macd_data['signal_line'].iloc[-1]:.4f}")
            print(f"Histogram: {macd_data['histogram'].iloc[-1]:.4f}")
            
            input("\nPress Enter to process trading signals...")
            
            self._process_signals(
                symbol,
                current_price,
                macd_data['macd_line'].iloc[-1],
                macd_data['signal_line'].iloc[-1],
                macd_data['histogram'].iloc[-1]
            )
            
            self._print_portfolio_status()
            
            input("\nPress Enter to continue to next stock...")
        
        self.current_date += timedelta(days=1)
        return True

def main():
    print(f"{Fore.CYAN}Loading parameters for gordonlindsay@virginmedia.com...{Style.RESET_ALL}")
    
    try:
        # Load parameters and watchlist from database
        params, watchlist = SimulationParameters.load_from_database()
        
        print(f"\n{Fore.GREEN}Parameters loaded successfully:{Style.RESET_ALL}")
        print(f"Start Date: {params.start_date.strftime('%d/%m/%Y')}")
        print(f"Initial Capital: ${params.initial_capital:,.2f}")
        print(f"Transaction Fee: {params.transaction_fee_percent}%")
        print(f"\nInvestment Rules:")
        print(f"Strong Buy: {params.investment_rules['strong_buy_percent']}%")
        print(f"Buy: {params.investment_rules['buy_percent']}%")
        print(f"Sell: {params.investment_rules['sell_percent']}%")
        print(f"Strong Sell: {params.investment_rules['strong_sell_percent']}%")
        print(f"Max Position Size: {params.max_single_position_percent}%")
        print(f"\nWatchlist: {', '.join(watchlist)}")
        
        if not watchlist:
            print(f"{Fore.RED}Warning: Watchlist is empty{Style.RESET_ALL}")
            return
            
        # Create tester instance
        tester = SimulationTester(params, watchlist)
        
        print(f"\n{Fore.GREEN}Starting Simulation Tester{Style.RESET_ALL}")
        print("\nPress Enter to step through the simulation...")
        
        while True:
            input("\nPress Enter for next step (Ctrl+C to exit)...")
            if not tester.step_simulation():
                break
        
        print(f"\n{Fore.GREEN}Simulation Complete!{Style.RESET_ALL}")
        
    except FileNotFoundError:
        print(f"{Fore.RED}Error: Database file not found. Please ensure you're running this script from the correct directory.{Style.RESET_ALL}")
    except ValueError as ve:
        print(f"{Fore.RED}Error: {str(ve)}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Simulation terminated by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")