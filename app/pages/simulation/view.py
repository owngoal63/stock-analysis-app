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
    
    # Portfolio value line
    fig.add_trace(
        go.Scatter(
            x=results.portfolio_values.index,
            y=results.portfolio_values.values,
            name="Total Value",
            line=dict(color="darkblue", width=2)
        ),
        row=1, col=1
    )
    
    # Add daily returns on secondary y-axis
    fig.add_trace(
        go.Scatter(
            x=results.daily_returns.index,
            y=results.daily_returns.values * 100,
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
            x=results.cash_values.index,
            y=results.cash_values.values,
            name="Cash",
            fill='tozeroy',
            line=dict(color="lightgreen")
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=results.positions_values.index,
            y=results.positions_values.values,
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

def create_transactions_table(transactions):
    """Create formatted transactions table with British date format"""
    if not transactions:
        return pd.DataFrame()
        
    records = []
    for t in transactions:
        records.append({
            'Date': t.date.strftime('%d/%m/%Y'),  # Changed to British format
            'Symbol': t.symbol,
            'Type': t.transaction_type.value,
            'Signal': t.signal_type.value,
            'Shares': t.shares,
            'Price': f"£{t.price:.2f}",
            'Fees': f"£{t.fees:.2f}",
            'Total': f"£{t.total_amount:.2f}"
        })
    
    # Create DataFrame and sort by date
    df = pd.DataFrame(records)
    
    # Convert Date column to datetime for proper sorting
    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
    
    # Sort by date descending (most recent first)
    df = df.sort_values('Date', ascending=False)
    
    # Convert back to British format string
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
    
    # Run simulation button
    if st.button("Run Simulation", type="primary"):
        try:
            with st.spinner("Running simulation..."):
                # Create progress bar
                progress_bar = st.progress(0)
                
                # Initialize simulation engine
                engine = SimulationEngine(market_data, technical_analysis, parameters)
                
                # Run simulation with progress updates
                results = engine.run_simulation(
                    watchlist,
                    progress_callback=progress_bar.progress
                )
                
                if results:
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
                    transactions_df = create_transactions_table(results.transactions)
                    if not transactions_df.empty:
                        st.dataframe(
                            transactions_df,
                            hide_index=True,
                            use_container_width=True
                        )
                    else:
                        st.info("No transactions were executed during the simulation")
                    
                else:
                    st.error("Simulation failed. Please check the parameters and try again.")
                
        except Exception as e:
            st.error(f"Error running simulation: {str(e)}")
            st.exception(e)

if __name__ == "__main__":
    render_simulation_view()