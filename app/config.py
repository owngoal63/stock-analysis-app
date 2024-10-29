"""
Application configuration.
File: app/config.py
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class Config:
    # Environment Settings
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # Market Data Settings
    MARKET_DATA_PROVIDER: str = os.getenv("MARKET_DATA_PROVIDER", "yahoo")
    
    # Cache Settings
    CACHE_DIR: str = os.getenv("CACHE_DIR", "./data/cache")

# Create a global instance
config = Config()