"""
Simulation parameters model definition.
File: app/services/simulation/models/parameters.py
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict

@dataclass
class SimulationParameters:
    """Parameters for portfolio simulation"""
    
    # Simulation control
    start_date: datetime
    initial_capital: float
    transaction_fee_percent: float = 0.1  # Default 0.1%
    
    # Investment rules (as percentages)
    investment_rules: Dict[str, float] = field(default_factory=lambda: {
        'strong_buy_percent': 20.0,  # 20% of available cash
        'buy_percent': 10.0,         # 10% of available cash
        'sell_percent': 50.0,        # 50% of position
        'strong_sell_percent': 100.0  # 100% of position
    })
    
    # Position management
    max_single_position_percent: float = 20.0  # Maximum 20% in single stock
    
    @property
    def is_valid(self) -> bool:
        """Validate parameter values"""
        try:
            # All percentages should be between 0 and 100
            valid_percentages = all(
                0 <= v <= 100 for v in [
                    self.transaction_fee_percent,
                    self.max_single_position_percent,
                    *self.investment_rules.values()
                ]
            )
            
            # Initial capital should be positive
            valid_capital = self.initial_capital > 0
            
            # Start date should be in the past
            valid_date = self.start_date < datetime.now()
            
            return all([valid_percentages, valid_capital, valid_date])
            
        except Exception:
            return False
    
    def get_validation_errors(self) -> list[str]:
        """Get list of validation errors"""
        errors = []
        
        if self.initial_capital <= 0:
            errors.append("Initial capital must be greater than 0")
        
        if self.start_date >= datetime.now():
            errors.append("Start date must be in the past")
            
        for name, value in {
            'Transaction fee': self.transaction_fee_percent,
            'Maximum position': self.max_single_position_percent,
            **{f"Investment rule '{k}'": v for k, v in self.investment_rules.items()}
        }.items():
            if not 0 <= value <= 100:
                errors.append(f"{name} must be between 0 and 100 percent")
                
        return errors
    
    @classmethod
    def get_default(cls, start_date: datetime) -> 'SimulationParameters':
        """Get default parameters instance"""
        return cls(
            start_date=start_date,
            initial_capital=10000.0,  # Start with $10,000
            transaction_fee_percent=0.1,  # 0.1% fee
            investment_rules={
                'strong_buy_percent': 20.0,
                'buy_percent': 10.0,
                'sell_percent': 50.0,
                'strong_sell_percent': 100.0
            },
            max_single_position_percent=20.0
        )