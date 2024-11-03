"""
Enhanced watchlist page with MACD analysis and recommendations.
File: app/pages/watchlist.py
"""

import streamlit as st
from datetime import datetime
from app.services.market_data import MarketDataService
from app.services.technical_analysis import TechnicalAnalysisService
from app.services.watchlist_analyzer import WatchlistAnalyzer
from app.auth.auth_handler import AuthHandler

def get_recommendation_color(recommendation: str) -> str:
    """Get color code for recommendation level"""
    colors = {
        'Strong Buy': '#00AA00',    # Dark Green
        'Buy': '#88CC88',          # Light Green
        'Neutral': '#CCCCCC',      # Gray
        'Sell': '#CC8888',         # Light Red
        'Strong Sell': '#AA0000'   # Dark Red
    }
    return colors.get(recommendation, '#CCCCCC')

def display_analysis_results(results: list):
    """Display watchlist analysis results in a formatted table"""
    st.subheader("Watchlist Analysis")
    
    if not results:
        st.info("No analysis results available.")
        return
    
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
    
    # Display detailed analysis expandable
    with st.expander("View Detailed Analysis"):
        for stock in sorted_results:
            st.markdown(
                f"""
                ### {stock['symbol']} - {stock['recommendation']}
                **Company:** {stock['company_name']}  
                **Sector:** {stock['sector']}  
                **Current Price:** ${stock['current_price']:.2f} ({stock['price_change_pct']:.1f}%)  
                **Trend Strength:** {stock['trend_strength']:.2f}  
                
                **Technical Indicators:**
                - MACD Line: {stock['macd_line']:.3f}
                - Signal Line: {stock['signal_line']:.3f}
                - Histogram: {stock['histogram']:.3f}
                
                **Analysis Date:** {stock['analysis_date']}
                ---
                """
            )
    
    # Display any errors
    error_stocks = [r for r in results if 'error' in r]
    if error_stocks:
        st.subheader("Analysis Errors")
        for stock in error_stocks:
            st.error(f"{stock['symbol']}: {stock['error']}")

def render_watchlist_page():
    """Render the watchlist management page"""
    try:
        st.title("My Watchlist")
        
        # Initialize services
        auth_handler = AuthHandler()
        market_data = MarketDataService()
        technical_analysis = TechnicalAnalysisService()
        watchlist_analyzer = WatchlistAnalyzer(market_data, technical_analysis)
        
        # Get current user
        current_user = auth_handler.get_current_user()
        if not current_user:
            st.error("Please log in to access your watchlist")
            return
            
        # Initialize watchlist in session state if not present
        if 'watchlist' not in st.session_state:
            st.session_state.watchlist = current_user.watchlist or []
            
        # Add stock section
        with st.container():
            st.subheader("Add Stock")
            col1, col2 = st.columns([3, 1])
            with col1:
                new_stock = st.text_input(
                    "Enter stock symbol:",
                    key="new_stock",
                    placeholder="e.g., AAPL"
                ).upper()
            with col2:
                if st.button("Add"):
                    if new_stock:
                        if new_stock not in st.session_state.watchlist:
                            try:
                                # Verify stock exists by trying to get its price
                                price = market_data.get_latest_price(new_stock)
                                st.session_state.watchlist.append(new_stock)
                                auth_handler.update_watchlist(
                                    current_user.id,
                                    st.session_state.watchlist
                                )
                                st.success(f"Added {new_stock} to watchlist!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error adding stock: {str(e)}")
                        else:
                            st.warning(f"{new_stock} is already in your watchlist!")
                    else:
                        st.warning("Please enter a stock symbol")
        
        # Display current watchlist
        st.subheader("Current Watchlist")
        if not st.session_state.watchlist:
            st.info("Your watchlist is empty. Add some stocks above!")
        else:
            # Add analysis button
            if st.button("Analyze Watchlist"):
                with st.spinner("Analyzing watchlist stocks..."):
                    analysis_results = watchlist_analyzer.analyze_watchlist(
                        st.session_state.watchlist
                    )
                    st.session_state.analysis_results = analysis_results
                    
            # Display analysis results if available
            if 'analysis_results' in st.session_state:
                display_analysis_results(st.session_state.analysis_results)
                
            # Display watchlist table
            for symbol in st.session_state.watchlist:
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{symbol}**")
                with col2:
                    try:
                        price = market_data.get_latest_price(symbol)
                        st.write(f"${price:.2f}")
                    except:
                        st.write("Price unavailable")
                with col3:
                    if st.button("Remove", key=f"remove_{symbol}"):
                        st.session_state.watchlist.remove(symbol)
                        auth_handler.update_watchlist(
                            current_user.id,
                            st.session_state.watchlist
                        )
                        # Clear analysis results when watchlist changes
                        if 'analysis_results' in st.session_state:
                            del st.session_state.analysis_results
                        st.success(f"Removed {symbol} from watchlist!")
                        st.rerun()
                        
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.write("Detailed error information:")
        st.exception(e)

if __name__ == "__main__":
    render_watchlist_page()