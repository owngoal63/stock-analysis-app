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
        """
        Register a new user
        
        Args:
            email: User's email address
            password: User's password
        
        Returns:
            bool: True if registration successful, False if email exists
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if email exists
                if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
                    return False
                
                # Create new user
                user = User(
                    id=str(abs(hash(email + datetime.now().isoformat()))),
                    email=email,
                    created_at=datetime.now(),
                    watchlist=[],
                    preferences={},
                    last_login=None
                )
                
                # Hash password
                password_hash = self._hash_password(password)
                
                try:
                    # Store user with hashed password
                    conn.execute(
                        """
                        INSERT INTO users 
                        (id, email, password_hash, created_at, watchlist, preferences)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            user.id,
                            user.email,
                            password_hash,
                            user.created_at.isoformat(),
                            '[]',  # Empty watchlist
                            '{}'   # Empty preferences
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
            email: User's email
            password: User's password
        
        Returns:
            Optional[str]: JWT token if successful, None if authentication fails
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute(
                    "SELECT id, password_hash FROM users WHERE email = ?",
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
        """Update user's recommendation parameters"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE users SET recommendation_params = ? WHERE id = ?",
                    (str(params), user_id)
                )
                return True
        except Exception as e:
            self.logger.error(f"Error updating recommendation parameters: {str(e)}")
            return False

    def get_current_user(self) -> Optional[User]:
        """Get currently authenticated user"""
        if 'auth_token' not in st.session_state:
            return None

        user_id = self._verify_token(st.session_state.auth_token)
        if not user_id:
            del st.session_state.auth_token
            return None

        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute(
                    "SELECT * FROM users WHERE id = ?",
                    (user_id,)
                ).fetchone()
                
                if result:
                    return User(
                        id=result[0],
                        email=result[1],
                        created_at=datetime.fromisoformat(result[3]),
                        last_login=datetime.fromisoformat(result[4]) if result[4] else None,
                        watchlist=eval(result[5]) if result[5] else [],
                        preferences=eval(result[6]) if result[6] else {},
                        recommendation_params=eval(result[7]) if result[7] else User.recommendation_params.default_factory()
                    )
                return None
        except Exception as e:
            st.error(f"Error getting current user: {str(e)}")
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