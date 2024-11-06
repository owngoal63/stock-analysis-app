"""
Recommendation parameters configuration page.
File: app/pages/parameters.py
"""

import streamlit as st
from app.auth.auth_handler import AuthHandler
from app.models.user import User

def render_parameters_page():
    """Render the recommendation parameters configuration page"""
    st.title("Recommendation Parameters")
    
    auth_handler = AuthHandler()
    current_user = auth_handler.get_current_user()
    
    if not current_user:
        st.error("Please log in to access parameters")
        return
        
    st.write("""
    Configure the parameters that determine stock recommendations. 
    These values affect how stocks are classified into different recommendation categories.
    """)
    
    # Get current parameters
    params = current_user.recommendation_params
    
    # Create form for editing parameters
    with st.form("recommendation_params"):
        st.subheader("Strong Buy Thresholds")
        strong_buy_strength = st.number_input(
            "Minimum Trend Strength",
            value=float(params['strong_buy']['trend_strength']),
            min_value=-1.0,
            max_value=1.0,
            step=0.1,
            help="Minimum trend strength for Strong Buy recommendation (between -1 and 1)"
        )
        strong_buy_macd = st.number_input(
            "Minimum MACD Value",
            value=float(params['strong_buy']['macd_threshold']),
            step=0.001,
            help="Minimum MACD value for Strong Buy recommendation"
        )
        strong_buy_hist = st.number_input(
            "Minimum Histogram Change",
            value=float(params['strong_buy']['histogram_change']),
            step=0.001,
            help="Minimum histogram change for Strong Buy recommendation"
        )
        
        st.subheader("Buy Thresholds")
        buy_strength = st.number_input(
            "Minimum Trend Strength",
            value=float(params['buy']['trend_strength']),
            min_value=-1.0,
            max_value=1.0,
            step=0.1,
            help="Minimum trend strength for Buy recommendation (between -1 and 1)"
        )
        buy_macd = st.number_input(
            "Minimum MACD Value",
            value=float(params['buy']['macd_threshold']),
            step=0.001,
            help="Minimum MACD value for Buy recommendation"
        )
        buy_hist = st.number_input(
            "Minimum Histogram Change",
            value=float(params['buy']['histogram_change']),
            step=0.001,
            help="Minimum histogram change for Buy recommendation"
        )
        
        st.subheader("Sell Thresholds")
        sell_strength = st.number_input(
            "Maximum Trend Strength",
            value=float(params['sell']['trend_strength']),
            min_value=-1.0,
            max_value=1.0,
            step=0.1,
            help="Maximum trend strength for Sell recommendation (between -1 and 1)"
        )
        sell_macd = st.number_input(
            "Maximum MACD Value",
            value=float(params['sell']['macd_threshold']),
            step=0.001,
            help="Maximum MACD value for Sell recommendation"
        )
        sell_hist = st.number_input(
            "Maximum Histogram Change",
            value=float(params['sell']['histogram_change']),
            step=0.001,
            help="Maximum histogram change for Sell recommendation"
        )
        
        st.subheader("Strong Sell Thresholds")
        strong_sell_strength = st.number_input(
            "Maximum Trend Strength",
            value=float(params['strong_sell']['trend_strength']),
            min_value=-1.0,
            max_value=1.0,
            step=0.1,
            help="Maximum trend strength for Strong Sell recommendation (between -1 and 1)"
        )
        strong_sell_macd = st.number_input(
            "Maximum MACD Value",
            value=float(params['strong_sell']['macd_threshold']),
            step=0.001,
            help="Maximum MACD value for Strong Sell recommendation"
        )
        strong_sell_hist = st.number_input(
            "Maximum Histogram Change",
            value=float(params['strong_sell']['histogram_change']),
            step=0.001,
            help="Maximum histogram change for Strong Sell recommendation"
        )
        
        # Add reset to defaults button and save button
        col1, col2 = st.columns(2)
        with col1:
            reset = st.form_submit_button("Reset to Defaults")
        with col2:
            submit = st.form_submit_button("Save Parameters")
            
        if reset:
            # Reset to default values
            auth_handler.update_recommendation_params(
                current_user.id,
                User.recommendation_params.default_factory()
            )
            st.success("Parameters reset to defaults!")
            st.rerun()
            
        if submit:
            # Update parameters
            new_params = {
                'strong_buy': {
                    'trend_strength': strong_buy_strength,
                    'macd_threshold': strong_buy_macd,
                    'histogram_change': strong_buy_hist
                },
                'buy': {
                    'trend_strength': buy_strength,
                    'macd_threshold': buy_macd,
                    'histogram_change': buy_hist
                },
                'sell': {
                    'trend_strength': sell_strength,
                    'macd_threshold': sell_macd,
                    'histogram_change': sell_hist
                },
                'strong_sell': {
                    'trend_strength': strong_sell_strength,
                    'macd_threshold': strong_sell_macd,
                    'histogram_change': strong_sell_hist
                }
            }
            
            # Validate parameters
            if (strong_buy_strength < buy_strength or
                buy_strength < sell_strength or
                sell_strength < strong_sell_strength):
                st.error("Invalid threshold values. Please ensure Strong Buy > Buy > Sell > Strong Sell")
                return
                
            # Save parameters
            if auth_handler.update_recommendation_params(current_user.id, new_params):
                st.success("Parameters saved successfully!")
                st.rerun()
            else:
                st.error("Error saving parameters. Please try again.")