"""
Debug page for viewing configuration and environment settings.
File: app/pages/debug.py
"""

import os
import streamlit as st
from app.config import config

def render_debug_page():
    """Render the debug information page"""
    st.title("Configuration Debug")
    
    st.subheader("Environment Variables")
    
    # Display configuration in a nice format
    st.write("Current Configuration:")
    config_dict = {
        "Environment": config.ENVIRONMENT,
        "Debug Mode": config.DEBUG,
        "Market Data Provider": config.MARKET_DATA_PROVIDER,
        "Cache Directory": config.CACHE_DIR
    }
    
    # Display as a table
    st.table([{"Setting": k, "Value": str(v)} for k, v in config_dict.items()])
    
    # Add some system information
    st.subheader("System Information")
    st.write(f"Working Directory: {os.getcwd()}")
    
    # Add more helpful debug information
    st.write(f"Python Path: {os.getenv('PYTHONPATH', 'Not Set')}")
    st.write(f"Cache Directory Exists: {os.path.exists(config.CACHE_DIR)}")

if __name__ == "__main__":
    render_debug_page()