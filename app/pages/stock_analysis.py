"""
Stock analysis page view.
File: app/pages/stock_analysis.py
"""

import streamlit as st
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from app.services.market_data import MarketDataService
from app.services.technical_analysis import TechnicalAnalysisService

@st.cache_resource
def init_services():
    """Initialize services with caching"""
    return (
        MarketDataService(),
        TechnicalAnalysisService()
    )

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
    """Render the stock analysis page"""
    st.title("Stock Analysis")
    
    # Initialize services
    market_data, technical_analysis = init_services()
    
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
                datetime.now() - timedelta(days=30)
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
                
                # Calculate MACD
                macd_data = technical_analysis.calculate_macd(
                    df,
                    fast_period=fast_period,
                    slow_period=slow_period,
                    signal_period=signal_period
                )
                
                # Results container
                st.write("")  # Add spacing
                with st.container():
                    # Company info
                    company_name = metadata.get('company_name', symbol)
                    st.subheader(f"{company_name} ({symbol})")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"Sector: {metadata.get('sector', 'N/A')}")
                    with col2:
                        st.write(f"Industry: {metadata.get('industry', 'N/A')}")
                
                # Metrics container
                with st.container():
                    # Display metrics in equal columns
                    col1, col2, col3, col4 = st.columns(4)
                    
                    # Display latest price
                    with col1:
                        latest_price = market_data.get_latest_price(symbol)
                        st.metric("Latest Price", f"${latest_price:.2f}")
                    
                    # Display MACD values for latest day
                    latest_macd = macd_data['macd_line'].iloc[-1]
                    latest_signal = macd_data['signal_line'].iloc[-1]
                    latest_hist = macd_data['histogram'].iloc[-1]
                    
                    with col2:
                        st.metric("MACD Line", f"{latest_macd:.3f}")
                    with col3:
                        st.metric("Signal Line", f"{latest_signal:.3f}")
                    with col4:
                        st.metric("MACD Histogram", f"{latest_hist:.3f}")
                
                # Chart container
                with st.container():
                    # Display combined chart
                    fig = plot_stock_with_macd(df, macd_data)
                    st.plotly_chart(fig, use_container_width=True)
                
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