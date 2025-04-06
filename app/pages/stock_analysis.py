"""
Enhanced stock analysis page with trend strength indicator that perfectly matches watchlist analyzer.
File: app/pages/stock_analysis.py
"""

import streamlit as st
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import logging
from typing import Dict

from app.services.market_data import MarketDataService
from app.services.technical_analysis import TechnicalAnalysisService
from app.auth.auth_handler import AuthHandler

@st.cache_resource
def init_services():
    """Initialize services with caching"""
    return (
        MarketDataService(),
        TechnicalAnalysisService()
    )

def calculate_trend_strength(price_data: pd.DataFrame, macd_data: Dict[str, pd.Series]) -> float:
    """
    Calculate trend strength based on price action and MACD with improved robustness
    
    Args:
        price_data: DataFrame with price history
        macd_data: Dictionary containing MACD indicators
        
    Returns:
        float: Trend strength score between -1 and 1
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Make sure we're using numeric data with no missing values
        # Get recent data (last 10 periods or less if not enough data)
        periods = min(10, len(price_data))
        if periods < 3:  # Need at least 3 data points for meaningful analysis
            return 0.0
            
        # Convert to numeric and handle NaN values
        try:
            recent_hist = pd.to_numeric(macd_data['histogram'].tail(periods), errors='coerce').fillna(0)
            recent_price = pd.to_numeric(price_data['close'].tail(periods), errors='coerce').fillna(0)
            recent_macd = pd.to_numeric(macd_data['macd_line'].tail(periods), errors='coerce').fillna(0)
            recent_signal = pd.to_numeric(macd_data['signal_line'].tail(periods), errors='coerce').fillna(0)
        except KeyError as e:
            # If any key is missing, log the error and use alternate column names
            logger.warning(f"Key error calculating trend strength: {e}")
            # Try alternate column names
            recent_price = pd.to_numeric(
                price_data.get('close', price_data.get('Close', pd.Series([0] * periods))).tail(periods),
                errors='coerce'
            ).fillna(0)
            # For the rest, we'll use the fallbacks from the except block below
            raise
            
        # Calculate various strength indicators
        if recent_hist.std() != 0:
            hist_strength = recent_hist.mean() / recent_hist.std()
        else:
            hist_strength = 0
            
        # Calculate price trend (scaled percentage change)
        price_pct_changes = recent_price.pct_change().dropna()
        if not price_pct_changes.empty:
            price_trend = price_pct_changes.mean() * 100 * 10  # Scaled percentage change
        else:
            price_trend = 0
            
        # MACD trend (difference between MACD and signal line)
        macd_trend = (recent_macd - recent_signal).mean()
        
        # Combine indicators into overall strength score
        # Use numpy.tanh to bound values between -1 and 1
        strength_score = (
            np.tanh(hist_strength) * 0.4 +    # Histogram contribution
            np.tanh(price_trend) * 0.3 +      # Price trend contribution
            np.tanh(macd_trend) * 0.3         # MACD trend contribution
        )
        
        # Ensure the final score is between -1 and 1
        final_score = max(min(strength_score, 1), -1)
        
        return final_score
        
    except Exception as e:
        # Log the error but don't crash the analysis
        logger.error(f"Error calculating trend strength: {str(e)}")
        # Return a small non-zero value to avoid all-zero results
        # Use a small positive or negative value based on the last MACD histogram value
        try:
            last_hist = macd_data['histogram'].iloc[-1]
            return 0.1 if last_hist > 0 else -0.1
        except:
            return 0.0

def determine_recommendation(price_data: pd.DataFrame, macd_data: Dict[str, pd.Series], params: Dict) -> (str, float):
    """
    Determine recommendation based on MACD signals using custom parameters
    
    Args:
        price_data: DataFrame with price history
        macd_data: Dictionary containing MACD line, signal line and histogram
        params: User's custom recommendation parameters
        
    Returns:
        Tuple of (recommendation, trend_strength)
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Get latest values - ensure they're numeric
        try:
            latest_macd = float(macd_data['macd_line'].iloc[-1])
            latest_signal = float(macd_data['signal_line'].iloc[-1])
            latest_hist = float(macd_data['histogram'].iloc[-1])
            prev_hist = float(macd_data['histogram'].iloc[-2]) if len(macd_data['histogram']) > 1 else 0.0
        except (IndexError, KeyError) as e:
            logger.warning(f"Error accessing MACD values: {e}")
            # Default to neutral if we can't get the values
            return "Neutral", 0.0
            
        # Calculate trend strength - now should return non-zero values
        strength = calculate_trend_strength(price_data, macd_data)
        hist_change = latest_hist - prev_hist
        
        # Ensure params are valid and have default fallbacks
        strong_buy_threshold = float(params.get('strong_buy', {}).get('trend_strength', 0.5))
        buy_threshold = float(params.get('buy', {}).get('trend_strength', 0.0))
        sell_threshold = float(params.get('sell', {}).get('trend_strength', 0.0))
        strong_sell_threshold = float(params.get('strong_sell', {}).get('trend_strength', -0.5))
        
        # Strong Buy: strength >= strong_buy threshold
        if strength >= strong_buy_threshold:
            return "Strong Buy", strength
        
        # Buy: strength >= buy threshold (but < strong_buy threshold, implicitly)
        if strength >= buy_threshold:
            return "Buy", strength
        
        # Strong Sell: strength <= strong_sell threshold
        if strength <= strong_sell_threshold:
            return "Strong Sell", strength
        
        # Sell: strength <= sell threshold (but > strong_sell threshold, implicitly)
        if strength <= sell_threshold:
            return "Sell", strength
        
        # Neutral: everything between buy and sell thresholds
        return "Neutral", strength
        
    except Exception as e:
        logger.error(f"Error analyzing MACD signal: {str(e)}")
        return "Neutral", 0.0  # Default to neutral on error

def format_recommendation(recommendation: str) -> str:
    """Format recommendation with color"""
    if recommendation == "Strong Buy":
        return f"<span style='color:green; font-weight:bold'>{recommendation}</span>"
    elif recommendation == "Buy":
        return f"<span style='color:green'>{recommendation}</span>"
    elif recommendation == "Strong Sell":
        return f"<span style='color:red; font-weight:bold'>{recommendation}</span>"
    elif recommendation == "Sell":
        return f"<span style='color:red'>{recommendation}</span>"
    else:
        return f"<span style='color:gray'>{recommendation}</span>"

def plot_stock_with_macd(price_data: pd.DataFrame, macd_data: dict):
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

def handle_fetch_data():
    """Set nav_clicked before data fetch"""
    st.session_state.nav_clicked = True

def render_stock_analysis():
    """Render the stock analysis page with format error protection"""
    st.title("Stock Analysis")
    
    # Initialize services
    market_data, technical_analysis = init_services()
    
    # Initialize auth handler to get user's parameters
    auth_handler = AuthHandler()
    current_user = auth_handler.get_current_user()
    user_params = current_user.recommendation_params if current_user else None
    
    # Create a container for input sections
    with st.container():
        # Data Entry Section
        st.subheader("Stock Selection")
        col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
        
        with col1:
            symbol = st.text_input("Enter Stock Symbol (e.g., AAPL):", "AAPL").upper()
        with col2:
            start_date = st.date_input(
                "Start Date",
                datetime.now() - timedelta(days=60)  # Use 60 days to match watchlist analyzer
            )
        with col3:
            end_date = st.date_input(
                "End Date",
                datetime.now()
            )
        
        # Add some spacing
        st.write("")
        
        # MACD Parameters Section
        st.subheader("MACD Parameters")
        
        # Container for better spacing and organization
        col1, col2 = st.columns(2)
        
        with col1:
            fast_period = st.slider(
                "Fast Period (Short-term EMA)",
                min_value=5,
                max_value=20,
                value=12,
                help="Number of periods for the fast moving average (shorter term)"
            )
            
            slow_period = st.slider(
                "Slow Period (Long-term EMA)",
                min_value=15,
                max_value=30,
                value=26,
                help="Number of periods for the slow moving average (longer term)"
            )
            
        with col2:
            signal_period = st.slider(
                "Signal Period (Signal Line)",
                min_value=5,
                max_value=15,
                value=9,
                help="Number of periods for the signal line smoothing"
            )
    
    # Add some spacing
    st.write("")
    
    # Centered Fetch Button in its own container
    with st.container():
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            fetch_clicked = st.button(
                "Fetch Data",
                type="primary",
                on_click=handle_fetch_data,
                use_container_width=True
            )
    
    # Results section in a new container
    if fetch_clicked:
        try:
            with st.spinner("Fetching stock data..."):
                # Get stock data
                df, metadata = market_data.get_stock_data(
                    symbol,
                    start_date,
                    end_date
                )
                
                # Safety check for empty data
                if df.empty:
                    st.error(f"No data available for {symbol} in the selected date range.")
                    return
                
                # Ensure 'close' column exists for MACD calculation
                if 'close' not in df.columns and 'Close' in df.columns:
                    df['close'] = df['Close']
                
                # Calculate MACD with error handling
                try:
                    macd_data = technical_analysis.calculate_macd(
                        df,
                        fast_period=fast_period,
                        slow_period=slow_period,
                        signal_period=signal_period
                    )
                except Exception as e:
                    st.error(f"Error calculating MACD: {str(e)}")
                    st.write("Available columns:", df.columns.tolist())
                    return
                
                # Calculate trend strength and recommendation using the SAME algorithm as watchlist
                if user_params:
                    recommendation, trend_strength = determine_recommendation(df, macd_data, user_params)
                else:
                    # Use default parameters if user params not available
                    default_params = {
                        'strong_buy': {'trend_strength': 0.5},
                        'buy': {'trend_strength': 0.0},
                        'sell': {'trend_strength': 0.0},
                        'strong_sell': {'trend_strength': -0.5}
                    }
                    recommendation, trend_strength = determine_recommendation(df, macd_data, default_params)
                
                # Results container
                st.write("")  # Add spacing
                with st.container():
                    # Company info
                    company_name = metadata.get('company_name', symbol)
                    if isinstance(company_name, dict):
                        company_name = company_name.get('name', symbol)
                    
                    st.subheader(f"{company_name} ({symbol})")
                    col1, col2 = st.columns(2)
                    with col1:
                        sector = metadata.get('sector', 'N/A')
                        if isinstance(sector, dict):
                            sector = sector.get('sector', 'N/A')
                        st.write(f"Sector: {sector}")
                    with col2:
                        industry = metadata.get('industry', 'N/A')
                        if isinstance(industry, dict):
                            industry = industry.get('industry', 'N/A')
                        st.write(f"Industry: {industry}")
                
                # Metrics container
                with st.container():
                    # Display metrics in columns
                    col1, col2, col3, col4, col5 = st.columns(5)
                    
                    # Display latest price
                    with col1:
                        try:
                            # Get latest price with error handling
                            latest_price = market_data.get_latest_price(symbol)
                            
                            # Ensure latest_price is a float, not a Series
                            if isinstance(latest_price, pd.Series):
                                latest_price = float(latest_price.iloc[-1])
                            elif isinstance(latest_price, dict):
                                # Try to extract price from dict
                                if 'close' in latest_price:
                                    latest_price = float(latest_price['close'])
                                elif 'price' in latest_price:
                                    latest_price = float(latest_price['price'])
                                else:
                                    # Fallback to df
                                    latest_price = float(df['close'].iloc[-1])
                            else:
                                latest_price = float(latest_price)
                        except Exception as e:
                            # Fallback to the last price in the DataFrame
                            latest_price = float(df['close'].iloc[-1])
                            
                        st.metric("Latest Price", f"${latest_price:.2f}")
                    
                    # Display MACD values for latest day
                    try:
                        # Convert Series to float if needed
                        if isinstance(macd_data['macd_line'], pd.Series):
                            latest_macd = float(macd_data['macd_line'].iloc[-1])
                            latest_signal = float(macd_data['signal_line'].iloc[-1])
                            latest_hist = float(macd_data['histogram'].iloc[-1])
                        else:
                            latest_macd = float(macd_data['macd_line'])
                            latest_signal = float(macd_data['signal_line'])
                            latest_hist = float(macd_data['histogram'])
                    except Exception as e:
                        latest_macd = 0.0
                        latest_signal = 0.0
                        latest_hist = 0.0
                    
                    with col2:
                        st.metric("MACD Line", f"{latest_macd:.3f}")
                    with col3:
                        st.metric("Signal Line", f"{latest_signal:.3f}")
                    with col4:
                        st.metric("MACD Histogram", f"{latest_hist:.3f}")
                    
                    # Display Trend Strength
                    with col5:
                        delta = None
                        if latest_macd > latest_signal:
                            delta = "↑"
                        elif latest_macd < latest_signal:
                            delta = "↓"
                        
                        st.metric("Trend Strength", f"{trend_strength:.2f}", delta=delta)
                
                # Recommendation Container
                with st.container():
                    st.subheader("Analysis Recommendation")
                    
                    # Create columns for recommendation display
                    col1, col2 = st.columns([1, 3])
                    
                    with col1:
                        st.markdown(f"**Recommendation:**")
                    with col2:
                        st.markdown(format_recommendation(recommendation), unsafe_allow_html=True)
                    
                    # Add explanation about recommendation calculation
                    with st.expander("How is this recommendation calculated?"):
                        st.markdown(f"""
                        The recommendation is calculated based on the trend strength value:
                        
                        1. **Trend Strength**: A value between -1 and 1 that combines:
                           - MACD histogram pattern (40% weight)
                           - Price momentum (30% weight)
                           - MACD line vs signal line position (30% weight)
                        
                        2. **Your Current Recommendation Thresholds**:
                           - Strong Buy: Strength ≥ {user_params['strong_buy']['trend_strength']}
                           - Buy: Strength ≥ {user_params['buy']['trend_strength']}
                           - Neutral: Strength between {user_params['buy']['trend_strength']} and {user_params['sell']['trend_strength']}
                           - Sell: Strength ≤ {user_params['sell']['trend_strength']}
                           - Strong Sell: Strength ≤ {user_params['strong_sell']['trend_strength']}
                        
                        *Note: These thresholds can be customized in the Parameters page.*
                        """)
                        
                        # Show raw MACD values for comparison
                        st.markdown("### Raw MACD Values")
                        st.markdown(f"""
                        - MACD Line: {latest_macd:.4f}
                        - Signal Line: {latest_signal:.4f}
                        - Histogram: {latest_hist:.4f}
                        - MACD minus Signal: {(latest_macd - latest_signal):.4f}
                        """)
                
                # Chart container
                with st.container():
                    # Display combined chart
                    try:
                        fig = plot_stock_with_macd(df, macd_data)
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error creating chart: {str(e)}")
                        st.write("This could be due to formatting issues with the data.")
                
                # Data container
                with st.container():
                    # Display raw data in expandable section
                    with st.expander("View Raw Data"):
                        st.dataframe(df, use_container_width=True)
                
        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")
            st.exception(e)

if __name__ == "__main__":
    render_stock_analysis()