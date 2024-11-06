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
                
        # Ensure recommendation_params is always a dict
        if self.recommendation_params is None:
            self.recommendation_params = self.__class__.recommendation_params.default_factory()
        elif isinstance(self.recommendation_params, str):
            try:
                self.recommendation_params = eval(self.recommendation_params)
            except:
                self.recommendation_params = self.__class__.recommendation_params.default_factory()