"""
Stock data model definition.
File: app/models/stock.py
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

@dataclass
class Stock:
    symbol: str
    company_name: str
    last_price: float
    last_updated: datetime
    technical_indicators: Dict
    ai_insights: Optional[str] = None