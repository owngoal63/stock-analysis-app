"""
Educational content page view.
File: app/pages/education.py
"""

import streamlit as st

def render_education_page():
    """Render the education page with explanations of technical analysis concepts"""
    st.title("Learn Technical Analysis")
    
    # Introduction
    st.write("""
    Welcome to our educational guide! This page will help you understand the technical analysis tools 
    and calculations used in our app. We've kept the explanations simple and practical, focusing on 
    what you need to know as a casual trader.
    """)

    # MACD Section
    st.header("Understanding MACD (Moving Average Convergence Divergence)")
    st.write("""
    MACD is one of our main tools for analyzing price trends. Think of it as a way to spot momentum 
    in stock prices - whether they're gaining speed going up, or picking up speed going down.

    Here's how it works:
    1. We track two moving averages: a fast one (12 days) and a slow one (26 days)
    2. The MACD line is the difference between these averages
    3. The Signal line is a smoothed version of the MACD line (9-day average)
    4. The Histogram shows the difference between these two lines

    When the MACD line crosses above the Signal line, it might be a good time to buy.
    When it crosses below, it might be time to sell.
    """)

    # Trend Strength Section
    st.header("Trend Strength")
    st.write("""
    We measure how strong a price trend is on a scale from -1 to +1:
    * +1 means a very strong upward trend
    * 0 means no clear trend
    * -1 means a very strong downward trend

    This helps you understand not just which direction the price is moving, but how convincingly 
    it's moving that way.
    """)

    # Trading Signals Section
    st.header("Our Trading Signals Explained")
    st.write("""
    The app generates five types of trading signals:

    1. Strong Buy: 
       * Strong upward momentum
       * MACD line clearly above Signal line
       * Growing histogram

    2. Buy:
       * Moderate upward momentum
       * MACD line just crossed above Signal line

    3. Neutral:
       * No clear trend
       * MACD and Signal lines close together

    4. Sell:
       * Moderate downward momentum
       * MACD line just crossed below Signal line

    5. Strong Sell:
       * Strong downward momentum
       * MACD line clearly below Signal line
       * Shrinking histogram
    """)

    # Portfolio Simulation Section
    st.header("Portfolio Simulation Metrics")
    st.write("""
    When you run a portfolio simulation, we calculate several important measurements:

    * Total Return: Your overall profit or loss in pounds and percentage
    * Maximum Drawdown: The largest drop from a peak to a trough in your portfolio value
    * Win Rate: The percentage of profitable trades
    * Sharpe Ratio: How much return you're getting for the risk you're taking
    * Average Holding Period: How long you typically keep stocks before selling
    """)

    # Glossary
    st.header("Glossary of Terms")
    terms = {
        "Moving Average": 
            "The average price over a specific number of days, updated daily. Helps smooth out price movements.",
        
        "MACD": 
            "Moving Average Convergence Divergence - A tool that helps spot trends by comparing fast and slow moving averages.",
        
        "Signal Line": 
            "A smoothed version of the MACD line that helps identify trading opportunities.",
        
        "Histogram": 
            "Visual bars showing the difference between the MACD and Signal lines.",
        
        "Trend": 
            "The general direction that a stock price is moving - up, down, or sideways.",
        
        "Volume": 
            "The number of shares traded during a specific period.",
        
        "RSI (Relative Strength Index)": 
            "A measurement from 0 to 100 showing if a stock might be overbought (too expensive) or oversold (too cheap).",
        
        "Drawdown": 
            "The percentage drop from a peak to a low point in your portfolio value.",
        
        "Win Rate": 
            "The percentage of trades that made a profit.",
        
        "Sharpe Ratio": 
            "A measure of risk-adjusted returns. Higher is better, as it means more return for the risk taken.",
        
        "Portfolio": 
            "Your complete collection of stock investments.",
        
        "Position": 
            "The amount of a particular stock you own.",
        
        "Technical Analysis": 
            "Studying price patterns and indicators to make trading decisions.",
        
        "Momentum": 
            "The speed and strength of a price movement.",
        
        "Candlestick": 
            "A chart showing the opening, closing, high, and low prices for a specific period."
    }

    # Display glossary in a clean format
    for term, definition in sorted(terms.items()):
        st.markdown(f"**{term}**")
        st.write(f"{definition}")
        st.write("")

    # Additional Resources
    st.header("Want to Learn More?")
    st.write("""
    While this guide covers the basics of what our app offers, trading involves many more concepts 
    and considerations. We recommend:

    * Starting with small investments while learning
    * Always using stop-losses to protect your investment
    * Following financial news to understand market movements
    * Never investing more than you can afford to lose
    """)

if __name__ == "__main__":
    render_education_page()