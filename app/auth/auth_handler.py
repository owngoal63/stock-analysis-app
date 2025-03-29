"""
Authentication management for the application.
File: app/auth/auth_handler.py
"""

import streamlit as st
from datetime import datetime, timedelta
import bcrypt
import jwt
import sqlite3
import os
from typing import Optional, Dict
from dataclasses import asdict
from pathlib import Path
from dotenv import load_dotenv  # Added this import

from app.models.user import User
from app.config import config

# Load environment variables
load_dotenv()

class AuthHandler:
    def __init__(self, db_path: str = "./data/auth.db"):
        """Initialize authentication handler"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Try to get secret key from different sources
        self.secret_key = self._get_secret_key()
        self.token_expiry = timedelta(days=1)
        self._init_db()

    def _get_secret_key(self) -> str:
        """Get secret key from various possible sources"""
        # Try to get from environment variable
        secret_key = os.getenv('JWT_SECRET')
        
        if not secret_key:
            try:
                # Try to get from streamlit secrets
                secret_key = st.secrets.get("JWT_SECRET")
            except:
                # If in development mode, use a default key
                if config.ENVIRONMENT == "development":
                    secret_key = "dev-secret-key-do-not-use-in-production"
                    print("Warning: Using development secret key. Do not use in production!")
                else:
                    raise ValueError(
                        "JWT_SECRET not found. Please set it in .env file or Streamlit secrets."
                    )
        
        return secret_key

    def _init_db(self):
        """Initialize the SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    watchlist TEXT,
                    preferences TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_email ON users(email)")

    def _hash_password(self, password: str) -> bytes:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    def _verify_password(self, password: str, password_hash: bytes) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash)

    def _generate_token(self, user_id: str) -> str:
        """Generate JWT token for user"""
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + self.token_expiry
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')

    def _verify_token(self, token: str) -> Optional[str]:
        """Verify JWT token and return user_id if valid"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload['user_id']
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def register_user(self, email: str, password: str) -> bool:
        """Register a new user"""
        try:
            # Ensure email is lowercase
            email = email.lower().strip()
            
            with sqlite3.connect(self.db_path) as conn:
                # Check if email exists
                if conn.execute(
                    "SELECT 1 FROM users WHERE LOWER(email) = LOWER(?)",
                    (email,)
                ).fetchone():
                    return False
                
                # Create new user
                user = User(
                    id=str(abs(hash(email + datetime.now().isoformat()))),
                    email=email,
                    created_at=datetime.now(),
                    watchlist=[],
                    preferences={},
                    recommendation_params={
                        'strong_buy': {
                            'trend_strength': 0.5,
                            'macd_threshold': 0,
                            'histogram_change': 0
                        },
                        'buy': {
                            'trend_strength': 0,
                            'macd_threshold': 0,
                            'histogram_change': 0
                        },
                        'sell': {
                            'trend_strength': 0,
                            'macd_threshold': 0,
                            'histogram_change': 0
                        },
                        'strong_sell': {
                            'trend_strength': -0.5,
                            'macd_threshold': 0,
                            'histogram_change': 0
                        }
                    },
                    last_login=None
                )
                
                # Hash password
                password_hash = self._hash_password(password)
                
                try:
                    # Store user with hashed password
                    conn.execute(
                        """
                        INSERT INTO users 
                        (id, email, password_hash, created_at, watchlist, preferences, recommendation_params)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            user.id,
                            user.email,
                            password_hash,
                            user.created_at.isoformat(),
                            '[]',  # Empty watchlist
                            '{}',   # Empty preferences
                            str(user.recommendation_params)  # Include recommendation params
                        )
                    )
                    return True
                    
                except sqlite3.IntegrityError as e:
                    print(f"Database error during registration: {e}")
                    return False
                    
        except Exception as e:
            print(f"Registration error: {str(e)}")
            return False

    def login_user(self, email: str, password: str) -> Optional[str]:
        """
        Authenticate user and return token
        
        Args:
            email: User's email (case insensitive)
            password: User's password
        
        Returns:
            Optional[str]: JWT token if successful, None if authentication fails
        """
        try:
            # Ensure email is lowercase
            email = email.lower().strip()
            
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute(
                    "SELECT id, password_hash FROM users WHERE LOWER(email) = LOWER(?)",
                    (email,)
                ).fetchone()
                
                if not result:
                    return None
                
                user_id, password_hash = result
                
                if self._verify_password(password, password_hash):
                    # Update last login
                    conn.execute(
                        "UPDATE users SET last_login = ? WHERE id = ?",
                        (datetime.now().isoformat(), user_id)
                    )
                    return self._generate_token(user_id)
                
                return None
        except Exception as e:
            st.error(f"Login error: {str(e)}")
            return None

    def update_recommendation_params(self, user_id: str, params: Dict) -> bool:
        """Update user's recommendation parameters with comprehensive fixes for persistence"""
        try:
            # Debug: View input parameters
            print(f"Attempting to save params for user {user_id}: {params}")
            
            # Validate params structure
            required_keys = ['strong_buy', 'buy', 'sell', 'strong_sell']
            for key in required_keys:
                if key not in params:
                    self.logger.error(f"Missing required key {key} in recommendation params")
                    return False
            
            # Convert the dictionary to a JSON string instead of using str()
            # This is critical - str() doesn't create valid JSON that can be parsed back
            import json
            params_json = json.dumps(params)
            
            print(f"Serialized params: {params_json}")
            
            with sqlite3.connect(self.db_path) as conn:
                # Check if the recommendation_params column exists
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(users)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'recommendation_params' not in columns:
                    self.logger.error("recommendation_params column not found in users table")
                    return False
                
                # Update the params with proper JSON serialization
                cursor.execute(
                    "UPDATE users SET recommendation_params = ? WHERE id = ?",
                    (params_json, user_id)
                )
                
                # Verify the update worked
                if cursor.rowcount == 0:
                    self.logger.error(f"No rows updated for user {user_id}")
                    
                    # Debug: Check if user exists
                    user_exists = conn.execute(
                        "SELECT 1 FROM users WHERE id = ?", (user_id,)
                    ).fetchone()
                    
                    if not user_exists:
                        self.logger.error(f"User with id {user_id} does not exist")
                        return False
                
                # Verify data was actually saved by reading it back
                saved_params = conn.execute(
                    "SELECT recommendation_params FROM users WHERE id = ?",
                    (user_id,)
                ).fetchone()
                
                if not saved_params:
                    self.logger.error(f"Failed to read back saved params for user {user_id}")
                    return False
                    
                print(f"Saved params read back: {saved_params[0]}")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error updating recommendation parameters: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def get_current_user(self) -> Optional[User]:
        """Get currently authenticated user with fixed reloading"""
        if 'auth_token' not in st.session_state:
            return None

        user_id = self._verify_token(st.session_state.auth_token)
        if not user_id:
            del st.session_state.auth_token
            return None
        
        # Check if we need to force reload the user
        force_reload = st.session_state.get('force_reload_user', False)
        if force_reload:
            # Clear the flag
            st.session_state.force_reload_user = False
            # Clear any cached user
            if 'current_user' in st.session_state:
                del st.session_state.current_user

        # Use cached user if available and not forcing reload
        if not force_reload and 'current_user' in st.session_state:
            return st.session_state.current_user

        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute(
                    "SELECT * FROM users WHERE id = ?",
                    (user_id,)
                ).fetchone()
                
                if result:
                    # Debug info
                    print(f"Loading user from database. ID: {result[0]}, Email: {result[1]}")
                    
                    # Check if recommendation_params exists in the result
                    has_params = len(result) > 7 and result[7] is not None
                    print(f"Has recommendation_params: {has_params}")
                    if has_params:
                        print(f"Raw recommendation_params: {result[7]}")
                    
                    # Handle recommendation_params parsing
                    recommendation_params = None
                    if has_params:
                        try:
                            import json
                            recommendation_params = json.loads(result[7])
                        except json.JSONDecodeError:
                            try:
                                recommendation_params = eval(result[7])
                            except:
                                recommendation_params = None
                    
                    user = User(
                        id=result[0],
                        email=result[1],
                        created_at=datetime.fromisoformat(result[3]),
                        last_login=datetime.fromisoformat(result[4]) if result[4] else None,
                        watchlist=eval(result[5]) if result[5] else [],
                        preferences=eval(result[6]) if result[6] else {},
                        recommendation_params=recommendation_params
                    )
                    
                    # Cache the user in session state
                    st.session_state.current_user = user
                    return user
                return None
        except Exception as e:
            st.error(f"Error getting current user: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None

    def logout_user(self):
        """Log out current user"""
        if 'auth_token' in st.session_state:
            del st.session_state.auth_token

    def check_authentication(self) -> bool:
        """Check if user is authenticated"""
        return self.get_current_user() is not None

    def update_user_preferences(self, user_id: str, preferences: Dict) -> bool:
        """Update user preferences"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE users SET preferences = ? WHERE id = ?",
                    (str(preferences), user_id)
                )
                return True
        except Exception as e:
            st.error(f"Error updating preferences: {str(e)}")
            return False

    def update_watchlist(self, user_id: str, watchlist: list) -> bool:
        """Update user's watchlist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE users SET watchlist = ? WHERE id = ?",
                    (str(watchlist), user_id)
                )
                return True
        except Exception as e:
            st.error(f"Error updating watchlist: {str(e)}")
            return False