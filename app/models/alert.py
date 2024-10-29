"""
Alert model definition.
File: app/models/alert.py
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Alert:
    id: str
    user_id: str
    symbol: str
    condition: str
    value: float
    created_at: datetime
    triggered_at: Optional[datetime] = None