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
                        st.success(f"Removed {symbol} from watchlist!")
                        st.rerun()
                        
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.write("Detailed error information:")
        st.exception(e)

if __name__ == "__main__":
    render_watchlist_page()