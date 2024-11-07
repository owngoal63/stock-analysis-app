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
    """Display watchlist analysis results in a formatted table"""
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
    
    sorted_results = sorted(
        valid_results,
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
        st.markdown(f"*Min Strength: {params['strong_buy']['trend_strength']}*")
        for stock in groups['Strong Buy']:
            with st.container():
                st.markdown(
                    f"""
                    **{stock['symbol']}**  
                    ${stock['current_price']:.2f} ({stock['price_change_pct']:.1f}%)  
                    Strength: {stock['trend_strength']:.2f}
                    """
                )
                st.markdown("---")
    
    # Display Buy recommendations
    with buy_col:
        st.markdown("### 🟢 Buy")
        st.markdown(f"*Min Strength: {params['buy']['trend_strength']}*")
        for stock in groups['Buy']:
            with st.container():
                st.markdown(
                    f"""
                    **{stock['symbol']}**  
                    ${stock['current_price']:.2f} ({stock['price_change_pct']:.1f}%)  
                    Strength: {stock['trend_strength']:.2f}
                    """
                )
                st.markdown("---")
    
    # Display Neutral recommendations
    with neutral_col:
        st.markdown("### ⚪ Neutral")
        st.markdown("*No threshold*")
        for stock in groups['Neutral']:
            with st.container():
                st.markdown(
                    f"""
                    **{stock['symbol']}**  
                    ${stock['current_price']:.2f} ({stock['price_change_pct']:.1f}%)  
                    Strength: {stock['trend_strength']:.2f}
                    """
                )
                st.markdown("---")
    
    # Display Sell recommendations
    with sell_col:
        st.markdown("### 🔴 Sell")
        st.markdown(f"*Max Strength: {params['sell']['trend_strength']}*")
        for stock in groups['Sell']:
            with st.container():
                st.markdown(
                    f"""
                    **{stock['symbol']}**  
                    ${stock['current_price']:.2f} ({stock['price_change_pct']:.1f}%)  
                    Strength: {stock['trend_strength']:.2f}
                    """
                )
                st.markdown("---")
    
    # Display Strong Sell recommendations
    with strong_sell_col:
        st.markdown("### 🔴 Strong Sell")
        st.markdown(f"*Max Strength: {params['strong_sell']['trend_strength']}*")
        for stock in groups['Strong Sell']:
            with st.container():
                st.markdown(
                    f"""
                    **{stock['symbol']}**  
                    ${stock['current_price']:.2f} ({stock['price_change_pct']:.1f}%)  
                    Strength: {stock['trend_strength']:.2f}
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

def plot_stock_with_macd(price_data: pd.DataFrame, macd_data: Dict[str, pd.Series]):
    """Create a combined price and MACD plot"""
    # Create figure with secondary y-axis
    fig = make_subplots(rows=2, cols=1, 
                       row_heights=[0.7, 0.3],
                       vertical_spacing=0.05,
                       shared_xaxes=True)

    # Add candlestick
    fig.add_trace(
        go.Candlestick(
            x=price_data.index,
            open=price_data['open'],
            high=price_data['high'],
            low=price_data['low'],
            close=price_data['close'],
            name='Price'
        ),
        row=1, col=1
    )

    # Add MACD
    fig.add_trace(
        go.Scatter(
            x=price_data.index,
            y=macd_data['macd_line'],
            name='MACD Line',
            line=dict(color='blue')
        ),
        row=2, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=price_data.index,
            y=macd_data['signal_line'],
            name='Signal Line',
            line=dict(color='orange')
        ),
        row=2, col=1
    )

    # Add MACD histogram
    fig.add_trace(
        go.Bar(
            x=price_data.index,
            y=macd_data['histogram'],
            name='MACD Histogram',
            marker_color=macd_data['histogram'].apply(
                lambda x: 'green' if x >= 0 else 'red'
            )
        ),
        row=2, col=1
    )

    # Update layout
    fig.update_layout(
        title='Stock Price and MACD',
        xaxis_title='Date',
        yaxis_title='Price',
        yaxis2_title='MACD',
        height=800,
        showlegend=True,
        xaxis_rangeslider_visible=False
    )

    return fig

def render_stock_analysis():
    """Render the stock analysis page"""
    st.title("Stock Analysis")
    
    # Stock symbol input
    symbol = st.text_input("Enter Stock Symbol (e.g., AAPL):", "AAPL").upper()
    
    # Date range selection
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            datetime.now() - timedelta(days=30)
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            datetime.now()
        )
    
    # MACD Parameters
    st.sidebar.subheader("MACD Parameters")
    fast_period = st.sidebar.slider("Fast Period", 5, 20, 12)
    slow_period = st.sidebar.slider("Slow Period", 15, 30, 26)
    signal_period = st.sidebar.slider("Signal Period", 5, 15, 9)
    
    if st.button("Fetch Data"):
        try:
            market_data, technical_analysis = init_services()
            
            with st.spinner("Fetching stock data..."):
                # Get stock data
                df, metadata = market_data.get_stock_data(
                    symbol,
                    start_date,
                    end_date
                )
                
                # Calculate MACD
                macd_data = technical_analysis.calculate_macd(
                    df,
                    fast_period=fast_period,
                    slow_period=slow_period,
                    signal_period=signal_period
                )
                
                # Display company info
                company_name = metadata.get('company_name', symbol)
                st.subheader(f"{company_name} ({symbol})")
                st.write(f"Sector: {metadata.get('sector', 'N/A')}")
                st.write(f"Industry: {metadata.get('industry', 'N/A')}")
                
                # Display latest price
                latest_price = market_data.get_latest_price(symbol)
                st.metric("Latest Price", f"${latest_price:.2f}")
                
                # Display MACD values for latest day
                latest_macd = macd_data['macd_line'].iloc[-1]
                latest_signal = macd_data['signal_line'].iloc[-1]
                latest_hist = macd_data['histogram'].iloc[-1]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("MACD Line", f"{latest_macd:.3f}")
                with col2:
                    st.metric("Signal Line", f"{latest_signal:.3f}")
                with col3:
                    st.metric("MACD Histogram", f"{latest_hist:.3f}")
                
                # Display combined chart
                fig = plot_stock_with_macd(df, macd_data)
                st.plotly_chart(fig, use_container_width=True)
                
                # Display raw data in expandable section
                with st.expander("View Raw Data"):
                    st.dataframe(df)
                
        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")
            logger.error(f"Error in stock viewer: {str(e)}")

def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="Stock Analysis App",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="collapsed",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': None
        }
    )

    st.markdown("""
        <style>
            div[data-testid="stSidebarNav"] {display: none;}
        </style>
    """, unsafe_allow_html=True)
    
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
    
    # Initialize page in session state if not present
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Stock Analysis"
    
    # Navigation buttons in sidebar
    pages = {
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
        if st.sidebar.button(page_name):
            st.session_state.current_page = page_key
            st.rerun()
    
    # Dropdown navigation (will stay in sync with sidebar)
    page_options = list(pages.keys())
    selected_page = st.sidebar.selectbox(
        "Quick Navigation",
        page_options,
        index=page_options.index(st.session_state.current_page)
    )
    
    # Update current page if changed through dropdown
    if selected_page != st.session_state.current_page:
        st.session_state.current_page = selected_page
        st.rerun()
    
    # Render the current page
    if st.session_state.current_page == "Stock Analysis":
        render_stock_analysis()
    elif st.session_state.current_page == "Maintain Watchlist":
        render_watchlist_page()
    elif st.session_state.current_page == "Analyze Watchlist":
        analyze_watchlist_page()
    elif st.session_state.current_page == "Parameters": 
        render_parameters_page()
    elif st.session_state.current_page == "Education":
        render_education_page()
    elif st.session_state.current_page == "Run Simulation":
        render_simulation_view()
    elif st.session_state.current_page == "Simulation Parameters":
        render_simulation_parameters_page()  
    elif st.session_state.current_page == "Debug":
        render_debug_page()

if __name__ == "__main__":
    main()