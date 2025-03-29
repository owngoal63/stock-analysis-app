"""
Main Streamlit application entry point.
File: main.py
"""

import streamlit as st
from datetime import datetime, timedelta
import logging
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, Tuple

from app.auth.auth_handler import AuthHandler
from app.pages.login import render_login_page
from app.pages.home import render_home_page
from app.pages.stock_analysis import render_stock_analysis
from app.pages.watchlist import render_watchlist_page
from app.pages.education import render_education_page
from app.pages.debug import render_debug_page
from app.pages.parameters import render_parameters_page
from app.pages.simulation.parameters import render_simulation_parameters_page
from app.pages.simulation.view import render_simulation_view
from app.services.market_data import MarketDataService
from app.services.technical_analysis import TechnicalAnalysisService
from app.services.watchlist_analyzer import WatchlistAnalyzer
from app.config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
@st.cache_resource
def init_services():
    return (
        MarketDataService(cache_dir=config.CACHE_DIR),
        TechnicalAnalysisService()
    )

def display_analysis_results(results: list):
    """Display watchlist analysis results in a formatted table with type safety"""
    st.subheader("Watchlist Analysis")
    
    if not results:
        st.info("No analysis results available.")
        return
    
    # Get current user's parameters
    auth_handler = AuthHandler()
    current_user = auth_handler.get_current_user()
    params = current_user.recommendation_params
    
    # Filter out error results
    valid_results = [r for r in results if 'error' not in r]
    
    # Sort results by recommendation strength
    recommendation_order = {
        'Strong Buy': 0,
        'Buy': 1,
        'Neutral': 2,
        'Sell': 3,
        'Strong Sell': 4
    }
    
    # Ensure all results have the expected fields and correct types
    processed_results = []
    for r in valid_results:
        try:
            # Convert all numeric values to Python float/int
            processed_r = {
                'symbol': str(r.get('symbol', '')),
                'company_name': str(r.get('company_name', r.get('symbol', ''))),
                'recommendation': str(r.get('recommendation', 'Neutral')),
                'current_price': float(r.get('current_price', 0.0)),
                'price_change_pct': float(r.get('price_change_pct', 0.0)),
                'trend_strength': float(r.get('trend_strength', 0.0)),
            }
            processed_results.append(processed_r)
        except (ValueError, TypeError) as e:
            print(f"Error processing result {r.get('symbol', 'unknown')}: {str(e)}")
    
    sorted_results = sorted(
        processed_results,
        key=lambda x: recommendation_order.get(x['recommendation'], 99)
    )
    
    # Create columns for different recommendation levels
    strong_buy_col, buy_col, neutral_col, sell_col, strong_sell_col = st.columns(5)
    
    # Group results by recommendation
    groups = {
        'Strong Buy': [r for r in sorted_results if r['recommendation'] == 'Strong Buy'],
        'Buy': [r for r in sorted_results if r['recommendation'] == 'Buy'],
        'Neutral': [r for r in sorted_results if r['recommendation'] == 'Neutral'],
        'Sell': [r for r in sorted_results if r['recommendation'] == 'Sell'],
        'Strong Sell': [r for r in sorted_results if r['recommendation'] == 'Strong Sell']
    }
    
    # Display Strong Buy recommendations
    with strong_buy_col:
        st.markdown("### 🟢 Strong Buy")
        trend_strength_val = params['strong_buy']['trend_strength']
        st.markdown(f"*Min Strength: {trend_strength_val}*")
        for stock in groups['Strong Buy']:
            with st.container():
                symbol = stock['symbol']
                price = stock['current_price']
                change = stock['price_change_pct']
                strength = stock['trend_strength']
                
                # Use explicit format strings with Python primitives
                st.markdown(
                    f"""
                    **{symbol}**  
                    ${price:.2f} ({change:.1f}%)  
                    Strength: {strength:.2f}
                    """
                )
                st.markdown("---")
    
    # Display Buy recommendations
    with buy_col:
        st.markdown("### 🟢 Buy")
        trend_strength_val = params['buy']['trend_strength']
        st.markdown(f"*Min Strength: {trend_strength_val}*")
        for stock in groups['Buy']:
            with st.container():
                symbol = stock['symbol']
                price = stock['current_price']
                change = stock['price_change_pct']
                strength = stock['trend_strength']
                
                st.markdown(
                    f"""
                    **{symbol}**  
                    ${price:.2f} ({change:.1f}%)  
                    Strength: {strength:.2f}
                    """
                )
                st.markdown("---")
    
    # Display Neutral recommendations
    with neutral_col:
        st.markdown("### ⚪ Neutral")
        st.markdown("*No threshold*")
        for stock in groups['Neutral']:
            with st.container():
                symbol = stock['symbol']
                price = stock['current_price']
                change = stock['price_change_pct']
                strength = stock['trend_strength']
                
                st.markdown(
                    f"""
                    **{symbol}**  
                    ${price:.2f} ({change:.1f}%)  
                    Strength: {strength:.2f}
                    """
                )
                st.markdown("---")
    
    # Display Sell recommendations
    with sell_col:
        st.markdown("### 🔴 Sell")
        trend_strength_val = params['sell']['trend_strength']
        st.markdown(f"*Max Strength: {trend_strength_val}*")
        for stock in groups['Sell']:
            with st.container():
                symbol = stock['symbol']
                price = stock['current_price']
                change = stock['price_change_pct']
                strength = stock['trend_strength']
                
                st.markdown(
                    f"""
                    **{symbol}**  
                    ${price:.2f} ({change:.1f}%)  
                    Strength: {strength:.2f}
                    """
                )
                st.markdown("---")
    
    # Display Strong Sell recommendations
    with strong_sell_col:
        st.markdown("### 🔴 Strong Sell")
        trend_strength_val = params['strong_sell']['trend_strength']
        st.markdown(f"*Max Strength: {trend_strength_val}*")
        for stock in groups['Strong Sell']:
            with st.container():
                symbol = stock['symbol']
                price = stock['current_price']
                change = stock['price_change_pct']
                strength = stock['trend_strength']
                
                st.markdown(
                    f"""
                    **{symbol}**  
                    ${price:.2f} ({change:.1f}%)  
                    Strength: {strength:.2f}
                    """
                )
                st.markdown("---")
    
def analyze_watchlist_page():
    """Render the watchlist analysis page"""
    st.title("Watchlist Analysis")
    
    # Initialize services
    market_data, technical_analysis = init_services()
    watchlist_analyzer = WatchlistAnalyzer(market_data, technical_analysis)
    auth_handler = AuthHandler()
    
    # Get current user and watchlist
    current_user = auth_handler.get_current_user()
    if not current_user or not current_user.watchlist:
        st.info("Your watchlist is empty. Please add stocks in the Maintain Watchlist page.")
        return
        
    with st.spinner("Analyzing watchlist stocks..."):
        analysis_results = watchlist_analyzer.analyze_watchlist(
            current_user.watchlist,
            current_user.recommendation_params  # Pass the user's parameters
        )
        display_analysis_results(analysis_results)



def main():
    """Main application entry point"""
    # Initialize session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Home"

    # Set page config
    st.set_page_config(
        page_title="Stock Analysis App",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="collapsed" if st.session_state.get('nav_clicked', False) else "expanded",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': None
        }
    )
    
    # Initialize authentication
    auth_handler = AuthHandler()
    
    # Check authentication
    if not auth_handler.check_authentication():
        render_login_page()
        return
    
    # Get current user
    current_user = auth_handler.get_current_user()
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    
    # User info in sidebar
    st.sidebar.write(f"Welcome, {current_user.email}")
    if st.sidebar.button("Logout"):
        auth_handler.logout_user()
        st.rerun()
    
    # Navigation buttons in sidebar
    pages = {
        "Home": "Home",  # Add Home as first option
        "Stock Analysis": "Stock Analysis",
        "Maintain Watchlist": "Maintain Watchlist",
        "Analyze Watchlist": "Analyze Watchlist",
        "Parameters": "Parameters",
        "Education": "Education",
        "Simulation Parameters": "Simulation Parameters",
        "Run Simulation": "Portfolio Simulation",
        "Debug": "Debug"
    }
    
    # Create a button for each page
    for page_key, page_name in pages.items():
        if st.sidebar.button(page_name, key=f"nav_{page_key}"):
            st.session_state.current_page = page_key
            st.session_state.nav_clicked = True
            st.rerun()
    
    # Clear nav_clicked after page reload
    if st.session_state.get('nav_clicked', False):
        st.session_state.nav_clicked = False
    
    # Quick navigation dropdown
    page_options = list(pages.keys())
    selected_page = st.sidebar.selectbox(
        "Quick Navigation",
        page_options,
        index=page_options.index(st.session_state.current_page)
    )
    
    # Update current page if changed through dropdown
    if selected_page != st.session_state.current_page:
        st.session_state.current_page = selected_page
        st.session_state.nav_clicked = True
        st.rerun()
    
    # Render the current page
    if st.session_state.current_page == "Home":
        render_home_page()
    elif st.session_state.current_page == "Stock Analysis":
        render_stock_analysis()
    elif st.session_state.current_page == "Maintain Watchlist":
        render_watchlist_page()
    elif st.session_state.current_page == "Analyze Watchlist":
        analyze_watchlist_page()
    elif st.session_state.current_page == "Parameters": 
        render_parameters_page()
    elif st.session_state.current_page == "Education":
        render_education_page()
    elif st.session_state.current_page == "Simulation Parameters":
        render_simulation_parameters_page()
    elif st.session_state.current_page == "Run Simulation":
        render_simulation_view()
    elif st.session_state.current_page == "Debug":
        render_debug_page()

if __name__ == "__main__":
    main()