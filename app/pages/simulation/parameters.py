"""
Simulation parameters configuration page.
File: app/pages/simulation/parameters.py
"""

import streamlit as st
from datetime import datetime, timedelta

from app.auth.auth_handler import AuthHandler
from app.services.simulation.parameters_service import SimulationParametersService
from app.services.simulation.models.parameters import SimulationParameters

def render_simulation_parameters_page():
    """Render the simulation parameters configuration page"""
    st.title("Portfolio Simulation Parameters")
    
    # Initialize services
    auth_handler = AuthHandler()
    params_service = SimulationParametersService(auth_handler)
    
    # Get current user and parameters
    current_user = auth_handler.get_current_user()
    if not current_user:
        st.error("Please log in to access simulation parameters")
        return
        
    parameters = params_service.get_parameters(current_user.id)
    
    # Create form for parameter editing
    with st.form("simulation_parameters"):
        st.subheader("Basic Settings")
        
        # Simulation period with British date format
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date (DD/MM/YYYY)",
                value=parameters.start_date.date(),
                max_value=datetime.now().date() - timedelta(days=1),
                help="Select the start date for the simulation",
                format="DD/MM/YYYY"  # Set British date format
            )
        
        # Initial capital
        with col2:
            initial_capital = st.number_input(
                "Initial Capital (£)",  # Changed to pounds symbol
                value=parameters.initial_capital,
                min_value=100.0,
                step=1000.0,
                help="Enter the initial capital for the simulation"
            )
        
        # Transaction fee
        transaction_fee = st.number_input(
            "Transaction Fee (%)",
            value=parameters.transaction_fee_percent,
            min_value=0.0,
            max_value=100.0,
            step=0.01,
            help="Fee applied to each buy/sell transaction"
        )
        
        st.subheader("Investment Rules")
        
        # Investment percentages
        col1, col2 = st.columns(2)
        with col1:
            strong_buy_percent = st.number_input(
                "Strong Buy Investment (%)",
                value=parameters.investment_rules['strong_buy_percent'],
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                help="Percentage of available cash to invest on Strong Buy signal"
            )
            
            buy_percent = st.number_input(
                "Buy Investment (%)",
                value=parameters.investment_rules['buy_percent'],
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                help="Percentage of available cash to invest on Buy signal"
            )
        
        with col2:
            sell_percent = st.number_input(
                "Sell Divestment (%)",
                value=parameters.investment_rules['sell_percent'],
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                help="Percentage of position to sell on Sell signal"
            )
            
            strong_sell_percent = st.number_input(
                "Strong Sell Divestment (%)",
                value=parameters.investment_rules['strong_sell_percent'],
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                help="Percentage of position to sell on Strong Sell signal"
            )
        
        st.subheader("Position Management")
        
        # Maximum position size
        max_position = st.number_input(
            "Maximum Single Position (%)",
            value=parameters.max_single_position_percent,
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            help="Maximum percentage of capital allowed in a single stock"
        )
        
        # Form submission
        col1, col2 = st.columns(2)
        with col1:
            reset = st.form_submit_button("Reset to Defaults")
        with col2:
            submit = st.form_submit_button("Save Parameters")
        
        if reset:
            # Reset to default values with current date
            default_params = SimulationParameters.get_default(
                start_date=datetime.combine(start_date, datetime.min.time())
            )
            if params_service.save_parameters(current_user.id, default_params):
                st.success("Parameters reset to defaults!")
                st.rerun()
            else:
                st.error("Error resetting parameters")
        
        if submit:
            # Create new parameters instance
            new_params = SimulationParameters(
                start_date=datetime.combine(start_date, datetime.min.time()),
                initial_capital=initial_capital,
                transaction_fee_percent=transaction_fee,
                investment_rules={
                    'strong_buy_percent': strong_buy_percent,
                    'buy_percent': buy_percent,
                    'sell_percent': sell_percent,
                    'strong_sell_percent': strong_sell_percent
                },
                max_single_position_percent=max_position
            )
            
            # Validate parameters
            if not new_params.is_valid:
                st.error(
                    "Invalid parameters: " + 
                    ", ".join(new_params.get_validation_errors())
                )
                return
            
            # Save parameters
            if params_service.save_parameters(current_user.id, new_params):
                st.success("Parameters saved successfully!")
            else:
                st.error("Error saving parameters")

if __name__ == "__main__":
    render_simulation_parameters_page()