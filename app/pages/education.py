"""
Educational content page view.
File: app/pages/education.py
"""

import streamlit as st

def render_education_page():
    """Render the education page with explanations of technical analysis concepts"""
    # Initialize show_examples in session state if not present
    if 'show_examples' not in st.session_state:
        st.session_state.show_examples = False
        
    def toggle_examples():
        st.session_state.show_examples = not st.session_state.show_examples
        st.session_state.nav_clicked = True

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

    st.header("Understanding the Trading Simulation")
    
    with st.expander("How Trading Decisions Are Made", expanded=True):
        st.markdown("""
        ### Trading Timeline and Price Usage
        
        The simulation follows realistic trading practices by using only information that would be available at the time of making a trading decision.
        
        #### Price Data Used For Trading
        - **Trading Decisions**: Uses the previous day's closing price (t-1)
        - **Trade Execution**: Executes at the previous day's closing price (t-1)
        - **Portfolio Valuation**: Uses current day's closing price (t) to track portfolio value
        
        #### Why Use Yesterday's Closing Price?
        1. **Realistic Trading**: In real trading, you can't use today's closing price because:
           - You don't know today's closing price until after the market closes
           - By then, you can't trade until the next day
        2. **Available Information**: Yesterday's closing price represents the most recent complete data point available for decision making
        3. **MACD Calculation**: Technical indicators like MACD are already based on historical price data
        
        #### Example Timeline:
        ```
        Monday Close: $100  →  Tuesday Morning: Make trading decision using $100
                            →  Tuesday Close: $102  →  Update portfolio value using $102
                                                   →  Wednesday Morning: Make trading decision using $102
        ```
        
        ### Trading Decision Process
        1. Each morning, the system:
           - Takes yesterday's closing price
           - Calculates technical indicators (MACD, etc.)
           - Generates buy/sell signals
           - Executes trades at yesterday's closing price
        
        2. Each evening, the system:
           - Updates portfolio values using current day's closing price
           - Records daily performance metrics
           - Prepares for next day's trading decisions
        
        ### Portfolio Value Tracking
        - Your portfolio value is always calculated using the most recent closing prices
        - This means your position values will change with market movements
        - Transaction history shows the actual prices used for trades
        """)
    
    with st.expander("Portfolio Simulation Parameters"):
        st.markdown("""
        ### Understanding Simulation Parameters
        
        #### Initial Capital
        - The starting amount of cash in your portfolio
        - All position size calculations are based on this initial amount
        
        #### Transaction Fees
        - Applied to both buy and sell transactions
        - Calculated as a percentage of the transaction value
        - Deducted from available cash on buys
        - Deducted from proceeds on sells
        
        #### Investment Rules
        1. **Strong Buy**: Invests a larger percentage of available cash
        2. **Buy**: Invests a moderate percentage of available cash
        3. **Sell**: Sells a portion of the existing position
        4. **Strong Sell**: Sells a larger portion or entire position
        
        #### Position Size Limits
        - Maximum position size as a percentage of total portfolio value
        - Helps maintain diversification
        - Prevents overconcentration in any single stock
        """)
    
    with st.expander("Common Questions"):
        st.markdown("""
        ### Frequently Asked Questions
        
        **Q: Why might my trade not execute at today's price?**  
        A: The simulation uses yesterday's closing price for trades to maintain realism. You can't trade at today's closing price because you don't know it until after markets close.
        
        **Q: Why does my portfolio value change even when I haven't traded?**  
        A: Portfolio value is updated using current market prices, even though trades execute at previous day's prices. This reflects real market movements.
        
        **Q: How are position sizes calculated?**  
        A: Position sizes are calculated based on:
        - Your available cash
        - The investment rule percentages
        - The maximum position size limit
        - The previous day's closing price
        
        **Q: How accurate is this compared to real trading?**  
        A: The simulation aims for realism by:
        - Using only historically available information
        - Including transaction fees
        - Enforcing realistic trading rules
        - However, it doesn't account for factors like:
          - Bid-ask spreads
          - Market impact
          - Partial fills
          - Intraday price movements
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

    # At the bottom of the page, for the "Show More Examples" button:
    # if st.button("Show More Examples"):
    #     # Set the same state that nav clicks use to keep sidebar collapsed
    #     st.session_state.nav_clicked = True
        
    #     # Add more examples to session state
    #     if 'show_examples' not in st.session_state:
    #         st.session_state.show_examples = True
    #     else:
    #         st.session_state.show_examples = not st.session_state.show_examples
            
    #     st.rerun()

    # Use on_click handler instead of direct button logic
    st.button(
        "Show More Examples" if not st.session_state.show_examples else "Hide Examples",
        on_click=toggle_examples,
        key="toggle_examples_button"  # Added unique key
    )

    # Show additional examples if enabled
    if st.session_state.show_examples:
        st.header("Additional Examples")
        st.write("""
        Here are some practical examples of MACD signals:

        1. Strong Uptrend Example:
           * MACD line clearly above signal line
           * Histogram bars growing
           * Both lines above zero line

        2. Weak Trend Example:
           * MACD and signal lines close together
           * Small histogram bars
           * Lines crossing frequently
        """)

if __name__ == "__main__":
    render_education_page()