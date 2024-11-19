"""
Portfolio simulation view page.
File: app/pages/simulation/view.py
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import pandas as pd

from app.auth.auth_handler import AuthHandler
from app.services.market_data import MarketDataService
from app.services.technical_analysis import TechnicalAnalysisService
from app.services.simulation.parameters_service import SimulationParametersService
from app.services.simulation.simulation_engine import SimulationEngine
from app.services.simulation.models.trading import TransactionType, SignalType

def format_currency(value: float) -> str:
    """Format currency with £ symbol and 2 decimal places"""
    return f"£{value:,.2f}"

def create_portfolio_chart(results):
    """Create portfolio value and composition chart"""
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.7, 0.3],
        specs=[[{"secondary_y": True}],
               [{"secondary_y": False}]],
        subplot_titles=("Portfolio Value", "Asset Allocation"),
        vertical_spacing=0.12
    )
    
    # Add initial capital point to the data
    initial_date = results.portfolio_values.index[0] - pd.Timedelta(days=1)
    
    portfolio_values = pd.concat([
        pd.Series({initial_date: results.initial_capital}),
        results.portfolio_values
    ])
    
    cash_values = pd.concat([
        pd.Series({initial_date: results.initial_capital}),
        results.cash_values
    ])
    
    positions_values = pd.concat([
        pd.Series({initial_date: 0.0}),
        results.positions_values
    ])
    
    daily_returns = pd.concat([
        pd.Series({initial_date: 0.0}),
        results.daily_returns
    ])
    
    # Portfolio value line
    fig.add_trace(
        go.Scatter(
            x=portfolio_values.index,
            y=portfolio_values.values,
            name="Total Value",
            line=dict(color="darkblue", width=2)
        ),
        row=1, col=1
    )
    
    # Add daily returns on secondary y-axis
    fig.add_trace(
        go.Scatter(
            x=daily_returns.index,
            y=daily_returns.values * 100,
            name="Daily Returns %",
            line=dict(color="gray", width=1),
            opacity=0.5
        ),
        row=1, col=1,
        secondary_y=True
    )
    
    # Asset allocation stacked area
    fig.add_trace(
        go.Scatter(
            x=cash_values.index,
            y=cash_values.values,
            name="Cash",
            fill='tozeroy',
            line=dict(color="lightgreen")
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=positions_values.index,
            y=positions_values.values,
            name="Positions",
            fill='tonexty',
            line=dict(color="lightblue")
        ),
        row=2, col=1
    )
    
    # Update layout
    fig.update_layout(
        height=800,
        title_text="Portfolio Simulation Results",
        showlegend=True,
        hovermode='x unified'
    )
    
    # Update y-axes labels
    fig.update_yaxes(title_text="Portfolio Value (£)", row=1, col=1)
    fig.update_yaxes(title_text="Daily Returns (%)", row=1, col=1, secondary_y=True)
    fig.update_yaxes(title_text="Value (£)", row=2, col=1)
    
    return fig

def create_transactions_table(transactions, initial_capital: float):
    """Create formatted transactions table with running totals"""
    if not transactions:
        return pd.DataFrame()
        
    records = []
    running_investments = {}  # Track positions: {symbol: {'shares': count, 'price': current_price}}
    available_capital = initial_capital
    
    # Sort transactions chronologically
    sorted_transactions = sorted(transactions, key=lambda x: x.date)
    
    for t in sorted_transactions:
        if t.transaction_type == TransactionType.BUY:
            shares_cost = t.shares * t.price
            fees = t.fees
            available_capital = available_capital - shares_cost - fees
            transaction_total = shares_cost + fees
            
            # Update position for bought stock
            if t.symbol not in running_investments:
                running_investments[t.symbol] = {'shares': 0, 'price': t.price}
            running_investments[t.symbol]['shares'] += t.shares
            running_investments[t.symbol]['price'] = t.price  # Update to current price
            
        else:  # SELL
            sale_proceeds = t.shares * t.price
            fees = t.fees
            available_capital = available_capital + (sale_proceeds - fees)
            transaction_total = sale_proceeds - fees
            
            # Update position for sold stock
            if t.symbol in running_investments:
                running_investments[t.symbol]['shares'] -= t.shares
                running_investments[t.symbol]['price'] = t.price  # Update to current price
                if running_investments[t.symbol]['shares'] <= 0:
                    del running_investments[t.symbol]
        
        # Calculate current investment value by summing value of all current positions
        current_investment_value = sum(
            pos['shares'] * pos['price']
            for pos in running_investments.values()
        )
        
        records.append({
            'Date': t.date.strftime('%d/%m/%Y'),
            'Symbol': t.symbol,
            'Type': t.transaction_type.value,
            'Signal': t.signal_type.value,
            'Shares': t.shares,
            'Price': f"£{t.price:.2f}",
            'Fees': f"£{t.fees:.2f}",
            'Total': f"£{transaction_total:.2f}",
            'Available Capital': f"£{available_capital:.2f}",
            'Investment Value': f"£{current_investment_value:.2f}",
            'Portfolio Total': f"£{(available_capital + current_investment_value):.2f}"
        })
    
    df = pd.DataFrame(records)
    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
    df = df.sort_values('Date', ascending=True)
    df['Date'] = df['Date'].dt.strftime('%d/%m/%Y')
    
    return df



def render_simulation_view():
    """Render the simulation view page"""
    st.title("Portfolio Simulation")
    
    # Initialize services
    auth_handler = AuthHandler()
    market_data = MarketDataService()
    technical_analysis = TechnicalAnalysisService()
    params_service = SimulationParametersService(auth_handler)
    
    # Get current user
    current_user = auth_handler.get_current_user()
    if not current_user:
        st.error("Please log in to access the simulation")
        return
    
    # Get user's watchlist and parameters
    watchlist = current_user.watchlist
    if not watchlist:
        st.error("Please add stocks to your watchlist before running a simulation")
        return
    
    # Get simulation parameters
    parameters = params_service.get_parameters(current_user.id)
    
    # Display current parameters
    with st.expander("Current Simulation Parameters", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("Start Date:", parameters.start_date.strftime('%d/%m/%Y'))
            st.write("Initial Capital:", format_currency(parameters.initial_capital))
        with col2:
            st.write("Transaction Fee:", f"{parameters.transaction_fee_percent}%")
            st.write("Max Position Size:", f"{parameters.max_single_position_percent}%")
        with col3:
            st.write("Strong Buy:", f"{parameters.investment_rules['strong_buy_percent']}%")
            st.write("Strong Sell:", f"{parameters.investment_rules['strong_sell_percent']}%")
            
        st.write("To modify these parameters, use the 'Portfolio Simulation Parameters' page.")

    # NEW: Function to handle simulation execution with sidebar state
    def run_simulation():
        """Handle simulation execution and maintain sidebar state"""
        with st.spinner("Running simulation..."):
            try:
                # Initialize simulation engine
                engine = SimulationEngine(market_data, technical_analysis, parameters)
                
                # Create progress bar
                progress_bar = st.progress(0)
                
                # Run simulation with progress updates
                results = engine.run_simulation(
                    watchlist,
                    progress_callback=lambda p: progress_bar.progress(p)
                )
                
                if results:
                    # Store results in session state
                    st.session_state.simulation_results = results
                    # Keep sidebar collapsed
                    st.session_state.nav_clicked = True
                else:
                    st.error("Simulation failed. Please check the parameters and try again.")
                    
            except Exception as e:
                st.error(f"Error running simulation: {str(e)}")
                st.exception(e)
                
            # Always keep sidebar collapsed
            st.session_state.nav_clicked = True

    # CHANGED: Run simulation button with on_click handler
    if st.button("Run Simulation", type="primary", key="run_sim_button", on_click=run_simulation):
        pass  # Logic handled in on_click function
    
    # Display results if available
    if hasattr(st.session_state, 'simulation_results') and st.session_state.simulation_results:
        results = st.session_state.simulation_results
        
        # Display summary metrics
        st.subheader("Summary Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Return",
                format_currency(results.total_return),
                f"{results.total_return_percent:.1f}%"
            )
        
        with col2:
            st.metric(
                "Final Portfolio Value",
                format_currency(results.final_portfolio_value)
            )
        
        with col3:
            st.metric(
                "Maximum Drawdown",
                f"{results.max_drawdown:.1f}%"
            )
        
        with col4:
            st.metric(
                "Sharpe Ratio",
                f"{results.sharpe_ratio:.2f}"
            )
        
        # Display additional metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Number of Trades",
                results.number_of_trades
            )
        
        with col2:
            st.metric(
                "Win Rate",
                f"{results.win_rate:.1f}%"
            )
        
        with col3:
            st.metric(
                "Avg Holding Period",
                f"{results.avg_holding_period:.1f} days"
            )
        
        # Display portfolio chart
        st.plotly_chart(
            create_portfolio_chart(results),
            use_container_width=True
        )
        
        # Display transactions
        st.subheader("Transactions")
        transactions_df = create_transactions_table(
            results.transactions,
            results.initial_capital
        )
        if not transactions_df.empty:
            st.dataframe(
                transactions_df,
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No transactions were executed during the simulation")

if __name__ == "__main__":
    render_simulation_view()