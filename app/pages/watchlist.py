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

        def add_stock(symbol: str):
            """Handle adding a stock to watchlist"""
            try:
                if symbol:
                    if symbol not in st.session_state.watchlist:
                        # Verify stock exists by trying to get its price
                        price = market_data.get_latest_price(symbol)
                        st.session_state.watchlist.append(symbol)
                        auth_handler.update_watchlist(
                            current_user.id,
                            st.session_state.watchlist
                        )
                        st.session_state.add_status = f"Added {symbol} to watchlist!"
                    else:
                        st.session_state.add_status = f"{symbol} is already in your watchlist!"
                else:
                    st.session_state.add_status = "Please enter a stock symbol"
                
                # Keep sidebar collapsed
                st.session_state.nav_clicked = True
                
            except Exception as e:
                st.session_state.add_status = f"Error adding stock: {str(e)}"
                st.session_state.nav_clicked = True

        def remove_stock(symbol: str):
            """Handle removing a stock from watchlist"""
            st.session_state.watchlist.remove(symbol)
            auth_handler.update_watchlist(
                current_user.id,
                st.session_state.watchlist
            )
            st.session_state.remove_status = f"Removed {symbol} from watchlist!"
            # Keep sidebar collapsed
            st.session_state.nav_clicked = True
            
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
                if st.button("Add", key="add_button", on_click=add_stock, args=(new_stock,)):
                    pass  # Logic handled in callback

            # Display add status message if present
            if 'add_status' in st.session_state:
                if "Error" in st.session_state.add_status:
                    st.error(st.session_state.add_status)
                elif "already in" in st.session_state.add_status:
                    st.warning(st.session_state.add_status)
                else:
                    st.success(st.session_state.add_status)
                st.session_state.pop('add_status')
        
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
                    if st.button("Remove", key=f"remove_{symbol}", on_click=remove_stock, args=(symbol,)):
                        pass  # Logic handled in callback

            # Display remove status message if present
            if 'remove_status' in st.session_state:
                st.success(st.session_state.remove_status)
                st.session_state.pop('remove_status')
                        
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.write("Detailed error information:")
        st.exception(e)
        # Keep sidebar collapsed even on error
        st.session_state.nav_clicked = True

if __name__ == "__main__":
    render_watchlist_page()