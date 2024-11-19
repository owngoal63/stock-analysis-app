"""
Fetch raw stock price data for watchlist stocks.
"""

import sqlite3
import ast
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
from pathlib import Path

def get_user_data(email="gordonlindsay@virginmedia.com"):
    db_path = Path("./data/auth.db")
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT preferences, watchlist FROM users WHERE email = ?",
            (email,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"User {email} not found")
        
        preferences = ast.literal_eval(row[0]) if row[0] else {}
        watchlist = ast.literal_eval(row[1]) if row[1] else []
        
        sim_params = preferences.get('simulation_parameters', {})
        start_date = datetime.strptime(
            sim_params.get('start_date', (datetime.now() - timedelta(days=90)).strftime('%d/%m/%Y')),
            '%d/%m/%Y'
        )
        
        return watchlist, start_date

def fetch_stock_data(symbols, start_date):
    for symbol in symbols:
        print(f"\nFetching data for {symbol}")
        stock = yf.Ticker(symbol)
        data = stock.history(start=start_date)
        print(f"\nDaily prices for {symbol} from {start_date.strftime('%Y-%m-%d')}:")
        print(data.to_string())

if __name__ == "__main__":
    watchlist, start_date = get_user_data()
    print(f"Watchlist: {watchlist}")
    print(f"Start Date: {start_date.strftime('%Y-%m-%d')}")
    fetch_stock_data(watchlist, start_date)