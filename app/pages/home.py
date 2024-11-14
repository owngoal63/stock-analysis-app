"""
Home page view with modern Streamlit styling and US stock suggestions.
File: app/pages/home.py
"""

import streamlit as st

def render_home_page():
    """Render the home page"""
    
    # Main welcome section
    st.title("Welcome to Your MACD Trading Assistant")
    st.markdown("""
    Hey there! This app helps you make smarter trading decisions using MACD (Moving Average Convergence Divergence) 
    analysis - don't worry if that sounds complex, we'll explain everything along the way.
    """)
    
    # Popular Stocks Section
    st.markdown("### 🔥 Popular US Stocks to Get Started")
    
    # Create three columns for different stock categories
    tech_col, retail_col, finance_col = st.columns(3)
    
    with tech_col:
        st.markdown("""
        **Tech**
        ```
        AAPL - Apple Inc.
        MSFT - Microsoft
        GOOGL - Alphabet
        META - Meta
        NVDA - NVIDIA
        AMD - AMD
        ```
        """)
        
    with retail_col:
        st.markdown("""
        **Consumer & Retail**
        ```
        WMT - Walmart
        COST - Costco
        AMZN - Amazon
        DIS - Disney
        NKE - Nike
        SBUX - Starbucks
        ```
        """)
        
    with finance_col:
        st.markdown("""
        **Financial**
        ```
        JPM - JP Morgan
        BAC - Bank of America
        GS - Goldman Sachs
        V - Visa
        MA - Mastercard
        BLK - BlackRock
        ```
        """)
    
    # Add some spacing
    st.write("")
    
    # Create two columns for features and navigation
    col1, col2 = st.columns(2)
    
    # What You Can Do Here section
    with col1:
        st.markdown("### 📈 What You Can Do Here")
        st.markdown("""
        - Track your favorite US stocks
        - Get buy/sell signals based on MACD analysis
        - Test trading strategies without risking real money
        - Learn technical analysis as you go
        """)
    
    # Quick Navigation Guide
    with col2:
        st.markdown("### 🧭 Quick Navigation Guide")
        st.markdown("""
        - **Stock Analysis:** Look up any stock and see its MACD signals
        - **Watchlist:** Keep track of your favorite stocks
        - **Parameters:** Customize your trading signals
        - **Simulation:** Test your strategy with virtual money
        - **Education:** Learn about MACD and technical analysis
        """)
    
    # Add some spacing
    st.write("")
    
    # Pro Tips section in a blue container
    with st.container():
        st.markdown("""
        <div style='background-color: #f0f5ff; padding: 20px; border-radius: 10px; border: 1px solid #cce0ff;'>
        <h3 style='color: #1e3a8a;'>🎯 Pro Tips for Getting Started</h3>
        <ol style='color: #1e3a8a;'>
            <li>Start by adding 2-3 stocks from the suggestions above to your watchlist</li>
            <li>Check out the Education section if MACD is new to you</li>
            <li>Try the simulator before trading with real money</li>
            <li>Use the Parameters page to adjust how sensitive your trading signals are</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)
    
    # Add some spacing
    st.write("")
    
    # Feature details in expandable sections
    with st.expander("🔍 About Stock Analysis"):
        st.markdown("""
        - Look up any US stock's performance
        - View MACD indicators and signals
        - Get clear buy/sell recommendations
        - Analyze price trends with interactive charts
        """)
        
    with st.expander("📊 About Portfolio Simulation"):
        st.markdown("""
        - Test your trading strategy with virtual money
        - Backtest using historical data
        - See how different MACD settings affect returns
        - Track performance metrics and trade history
        """)
        
    with st.expander("📚 About Learning Resources"):
        st.markdown("""
        - Learn MACD basics and advanced concepts
        - Understand how signals are generated
        - Get practical trading tips
        - Access beginner-friendly explanations
        """)
    
    # Quick Tip about stock symbols
    st.info("""
    💡 **Quick Tip:** Enter stock symbols exactly as shown above (e.g., 'AAPL' for Apple).
    This app uses Yahoo Finance data and supports US stocks traded on major exchanges (NYSE and NASDAQ).
    """)
    
    # Footer note
    st.markdown("""
    ---
    *Remember: This tool is designed to assist your trading decisions, not make them for you. 
    Always do your own research and never trade more than you can afford to lose.*
    """)

if __name__ == "__main__":
    render_home_page()