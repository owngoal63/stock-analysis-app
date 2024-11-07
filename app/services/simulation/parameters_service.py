"""
Service for managing simulation parameters.
File: app/services/simulation/parameters_service.py
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from app.auth.auth_handler import AuthHandler
from app.services.simulation.models.parameters import SimulationParameters

class SimulationParametersService:
    """Service for managing simulation parameters"""
    
    PREFERENCES_KEY = 'simulation_parameters'
    DATE_FORMAT = "%d/%m/%Y"  # British date format
    
    def __init__(self, auth_handler: AuthHandler):
        """Initialize with auth handler"""
        self.auth_handler = auth_handler
        self.logger = logging.getLogger(__name__)
    
    def get_parameters(self, user_id: str) -> SimulationParameters:
        """
        Get simulation parameters for user
        
        Args:
            user_id: User identifier
            
        Returns:
            SimulationParameters instance (default if none saved)
        """
        try:
            user = self.auth_handler.get_current_user()
            if not user:
                raise ValueError("User not found")
                
            # Get saved parameters from preferences
            saved_params = user.preferences.get(self.PREFERENCES_KEY, {})
            
            if saved_params:
                # Parse date using British format
                start_date = datetime.strptime(
                    saved_params['start_date'],
                    self.DATE_FORMAT
                )
                
                return SimulationParameters(
                    start_date=start_date,
                    initial_capital=float(saved_params['initial_capital']),
                    transaction_fee_percent=float(saved_params['transaction_fee_percent']),
                    investment_rules=saved_params['investment_rules'],
                    max_single_position_percent=float(saved_params['max_single_position_percent'])
                )
            else:
                # Return default parameters
                return SimulationParameters.get_default(
                    start_date=datetime.now() - timedelta(days=90)  # Default to 90 days
                )
                
        except Exception as e:
            self.logger.error(f"Error getting simulation parameters: {str(e)}")
            # Return default parameters on error
            return SimulationParameters.get_default(
                start_date=datetime.now() - timedelta(days=90)
            )
    
    def save_parameters(self, user_id: str, parameters: SimulationParameters) -> bool:
        """
        Save simulation parameters for user
        
        Args:
            user_id: User identifier
            parameters: SimulationParameters instance
            
        Returns:
            bool: True if save successful
        """
        try:
            if not parameters.is_valid:
                raise ValueError(
                    "Invalid parameters: " + ", ".join(parameters.get_validation_errors())
                )
            
            # Convert parameters to dict for storage, using British date format
            params_dict = {
                'start_date': parameters.start_date.strftime(self.DATE_FORMAT),
                'initial_capital': str(parameters.initial_capital),
                'transaction_fee_percent': str(parameters.transaction_fee_percent),
                'investment_rules': parameters.investment_rules,
                'max_single_position_percent': str(parameters.max_single_position_percent)
            }
            
            # Get current user preferences
            user = self.auth_handler.get_current_user()
            if not user:
                raise ValueError("User not found")
                
            # Update simulation parameters in preferences
            preferences = user.preferences
            preferences[self.PREFERENCES_KEY] = params_dict
            
            # Save updated preferences
            return self.auth_handler.update_user_preferences(user_id, preferences)
            
        except Exception as e:
            self.logger.error(f"Error saving simulation parameters: {str(e)}")
            return False