"""
Main Streamlit application entry point.
File: app/main.py
"""

import streamlit as st
from app.auth.auth_handler import check_authentication
from app.components.sidebar import render_sidebar
from app.services.market_data import MarketDataService
from app.services.technical_analysis import TechnicalAnalysisService
from app.services.ai_insights import AIInsightService
from app.utils.data_processing import setup_cache
from app.pages.debug import render_debug_page
from app.config import config

def initialize_services():
    """Initialize all required services"""
    # TODO: Initialize service instances with proper configuration
    pass

def setup_streamlit_config():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="Stock Analysis App",
        page_icon="📈",
        layout="wide"
    )

def main():
    """Main application entry point"""
    setup_streamlit_config()
    
    # TODO: Implement authentication check
    if not check_authentication():
        st.error("Please log in to continue")
        return

    # Initialize services
    initialize_services()

    # Render sidebar
    render_sidebar()

    # Main content area
    st.title("Stock Analysis Dashboard")
    
    # Add debug page when in development
    if config.DEBUG:
        if st.sidebar.button("Show Configuration"):
            render_debug_page()

if __name__ == "__main__":
    main()