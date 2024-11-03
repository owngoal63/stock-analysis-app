"""
Application configuration.
File: app/config.py
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

@dataclass
class Config:
    # Environment Settings
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # Authentication Settings
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    
    # Market Data Settings
    MARKET_DATA_PROVIDER: str = os.getenv("MARKET_DATA_PROVIDER", "yahoo")
    
    # Cache Settings
    CACHE_DIR: str = os.getenv("CACHE_DIR", "./data/cache")
    
    def __post_init__(self):
        # Ensure cache directory exists
        Path(self.CACHE_DIR).mkdir(parents=True, exist_ok=True)

# Create a global instance
config = Config()