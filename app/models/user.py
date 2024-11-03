"""
User model definition.
File: app/models/user.py
"""

from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime

@dataclass
class User:
    id: str
    email: str
    created_at: datetime
    watchlist: List[str]
    preferences: Dict
    last_login: Optional[datetime] = None
    
    def __post_init__(self):
        # Ensure watchlist is always a list
        if self.watchlist is None:
            self.watchlist = []
        elif isinstance(self.watchlist, str):
            # Handle case where watchlist is stored as string in database
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