"""
User model definition.
File: app/models/user.py
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class User:
    id: str
    email: str
    created_at: datetime
    watchlist: List[str]
    preferences: dict
    last_login: Optional[datetime] = None