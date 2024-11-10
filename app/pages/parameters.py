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
        
    # Get current parameters
    params = current_user.recommendation_params
    
    def save_parameters(params_dict):
        """Handle parameter saving with sidebar state"""
        success = auth_handler.update_recommendation_params(current_user.id, params_dict)
        # Keep sidebar collapsed
        st.session_state.nav_clicked = True
        # Store success/failure in session state for display after rerun
        st.session_state.save_status = "success" if success else "error"
    
    def reset_parameters():
        """Handle parameter reset with sidebar state"""
        success = auth_handler.update_recommendation_params(
            current_user.id,
            User.recommendation_params.default_factory()
        )
        # Keep sidebar collapsed
        st.session_state.nav_clicked = True
        # Store success/failure in session state for display after rerun
        st.session_state.save_status = "reset_success" if success else "reset_error"
    
    # Create form for editing parameters
    with st.form("recommendation_params", clear_on_submit=False):
        st.subheader("Strong Buy Thresholds")
        strong_buy_strength = st.number_input(
            "Minimum Trend Strength",
            value=float(params['strong_buy']['trend_strength']),
            min_value=-1.0,
            max_value=1.0,
            step=0.1,
            help="Minimum trend strength for Strong Buy recommendation (between -1 and 1)",
            key="strong_buy_strength"
        )
        strong_buy_macd = st.number_input(
            "Minimum MACD Value",
            value=float(params['strong_buy']['macd_threshold']),
            step=0.001,
            help="Minimum MACD value for Strong Buy recommendation",
            key="strong_buy_macd"
        )
        strong_buy_hist = st.number_input(
            "Minimum Histogram Change",
            value=float(params['strong_buy']['histogram_change']),
            step=0.001,
            help="Minimum histogram change for Strong Buy recommendation",
            key="strong_buy_hist"
        )
        
        st.subheader("Buy Thresholds")
        buy_strength = st.number_input(
            "Minimum Trend Strength",
            value=float(params['buy']['trend_strength']),
            min_value=-1.0,
            max_value=1.0,
            step=0.1,
            help="Minimum trend strength for Buy recommendation (between -1 and 1)",
            key="buy_strength"
        )
        buy_macd = st.number_input(
            "Minimum MACD Value",
            value=float(params['buy']['macd_threshold']),
            step=0.001,
            help="Minimum MACD value for Buy recommendation",
            key="buy_macd"
        )
        buy_hist = st.number_input(
            "Minimum Histogram Change",
            value=float(params['buy']['histogram_change']),
            step=0.001,
            help="Minimum histogram change for Buy recommendation",
            key="buy_hist"
        )
        
        st.subheader("Sell Thresholds")
        sell_strength = st.number_input(
            "Maximum Trend Strength",
            value=float(params['sell']['trend_strength']),
            min_value=-1.0,
            max_value=1.0,
            step=0.1,
            help="Maximum trend strength for Sell recommendation (between -1 and 1)",
            key="sell_strength"
        )
        sell_macd = st.number_input(
            "Maximum MACD Value",
            value=float(params['sell']['macd_threshold']),
            step=0.001,
            help="Maximum MACD value for Sell recommendation",
            key="sell_macd"
        )
        sell_hist = st.number_input(
            "Maximum Histogram Change",
            value=float(params['sell']['histogram_change']),
            step=0.001,
            help="Maximum histogram change for Sell recommendation",
            key="sell_hist"
        )
        
        st.subheader("Strong Sell Thresholds")
        strong_sell_strength = st.number_input(
            "Maximum Trend Strength",
            value=float(params['strong_sell']['trend_strength']),
            min_value=-1.0,
            max_value=1.0,
            step=0.1,
            help="Maximum trend strength for Strong Sell recommendation (between -1 and 1)",
            key="strong_sell_strength"
        )
        strong_sell_macd = st.number_input(
            "Maximum MACD Value",
            value=float(params['strong_sell']['macd_threshold']),
            step=0.001,
            help="Maximum MACD value for Strong Sell recommendation",
            key="strong_sell_macd"
        )
        strong_sell_hist = st.number_input(
            "Maximum Histogram Change",
            value=float(params['strong_sell']['histogram_change']),
            step=0.001,
            help="Maximum histogram change for Strong Sell recommendation",
            key="strong_sell_hist"
        )
        
        # Form submission buttons
        col1, col2 = st.columns(2)
        with col1:
            reset = st.form_submit_button("Reset to Defaults", on_click=reset_parameters)
        with col2:
            # Save button
            submit = st.form_submit_button(
                "Save Parameters",
                on_click=save_parameters,
                args=({
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
                },)
            )
    
    # Display status messages after form submission
    if st.session_state.get('save_status') == 'success':
        st.success("Parameters saved successfully!")
        st.session_state.pop('save_status')
    elif st.session_state.get('save_status') == 'error':
        st.error("Error saving parameters. Please try again.")
        st.session_state.pop('save_status')
    elif st.session_state.get('save_status') == 'reset_success':
        st.success("Parameters reset to defaults!")
        st.session_state.pop('save_status')
    elif st.session_state.get('save_status') == 'reset_error':
        st.error("Error resetting parameters.")
        st.session_state.pop('save_status')

if __name__ == "__main__":
    render_parameters_page()