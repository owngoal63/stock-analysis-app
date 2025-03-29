"""
User model definition.
File: app/models/user.py
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime

@dataclass
class User:
    id: str
    email: str
    created_at: datetime
    watchlist: List[str]
    preferences: Dict
    recommendation_params: Dict = field(default_factory=lambda: {
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
    })
    last_login: Optional[datetime] = None
    
    def __post_init__(self):
        # Ensure watchlist is always a list
        if self.watchlist is None:
            self.watchlist = []
        elif isinstance(self.watchlist, str):
            try:
                self.watchlist = eval(self.watchlist)
            except:
                self.watchlist = []
        
        # Ensure preferences is always a dict
        if self.preferences is None:
            self.preferences = {}
        elif isinstance(self.preferences, str):
            try:
                self.preferences = eval(self.preferences)
            except:
                self.preferences = {}
                
        # Updated handling for recommendation_params
        default_params = {
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
        }
        
        # Improved handling of recommendation_params to properly parse JSON
        if self.recommendation_params is None:
            self.recommendation_params = default_params
        elif isinstance(self.recommendation_params, str):
            try:
                # Try to parse as JSON first (most reliable)
                import json
                self.recommendation_params = json.loads(self.recommendation_params.strip())
            except json.JSONDecodeError:
                try:
                    # Fall back to eval for backward compatibility
                    self.recommendation_params = eval(self.recommendation_params)
                except:
                    # Use defaults as final fallback
                    self.recommendation_params = default_params
                    
        # Ensure all required keys exist
        for key in default_params:
            if key not in self.recommendation_params:
                self.recommendation_params[key] = default_params[key]
            # Also ensure all required subkeys exist
            for subkey in default_params[key]:
                if subkey not in self.recommendation_params[key]:
                    self.recommendation_params[key][subkey] = default_params[key][subkey]