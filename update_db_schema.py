"""
Database schema update script.
File: update_db_schema.py
"""

import sqlite3
import json
from pathlib import Path

def update_database_schema():
    # Path to the database - make sure this matches your app's database path
    db_path = Path("./data/auth.db")
    
    # Default parameters
    default_params = {
        "strong_buy": {"trend_strength": 0.5, "macd_threshold": 0, "histogram_change": 0},
        "buy": {"trend_strength": 0, "macd_threshold": 0, "histogram_change": 0},
        "sell": {"trend_strength": 0, "macd_threshold": 0, "histogram_change": 0},
        "strong_sell": {"trend_strength": -0.5, "macd_threshold": 0, "histogram_change": 0}
    }
    
    # Convert default parameters to string
    default_params_str = json.dumps(default_params)
    
    try:
        with sqlite3.connect(db_path) as conn:
            # Check if column exists
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Add column if it doesn't exist
            if 'recommendation_params' not in columns:
                print("Adding recommendation_params column...")
                conn.execute("ALTER TABLE users ADD COLUMN recommendation_params TEXT")
                
                # Update existing rows with default parameters
                print("Setting default parameters for existing users...")
                conn.execute(
                    "UPDATE users SET recommendation_params = ? WHERE recommendation_params IS NULL",
                    (default_params_str,)
                )
                
                print("Database schema updated successfully!")
            else:
                print("recommendation_params column already exists.")
                
            # Verify the update
            cursor.execute("SELECT id, email, recommendation_params FROM users")
            users = cursor.fetchall()
            print("\nVerifying users:")
            for user in users:
                print(f"User {user[1]}: {'has parameters' if user[2] else 'missing parameters'}")
                
    except sqlite3.Error as e:
        print(f"An error occurred: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    print("Starting database schema update...")
    update_database_schema()