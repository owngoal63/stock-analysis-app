"""
Modified view.py to use transaction sequence number for exact ordering, with debug statements removed.
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
    """Create portfolio value and composition chart with safeguards against non-numeric data"""
    try:
        # Create plotly figure
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add portfolio value line
        fig.add_trace(
            go.Scatter(
                x=results.portfolio_values.index,
                y=results.portfolio_values.values,
                name="Portfolio Value",
                line=dict(color="#1f77b4", width=2)
            ),
            secondary_y=False
        )
        
        # Add cash position line
        fig.add_trace(
            go.Scatter(
                x=results.cash_values.index,
                y=results.cash_values.values,
                name="Cash",
                line=dict(color="#2ca02c", width=2, dash="dot")
            ),
            secondary_y=False
        )
        
        # Add investments line
        fig.add_trace(
            go.Scatter(
                x=results.positions_values.index,
                y=results.positions_values.values,
                name="Investments",
                line=dict(color="#ff7f0e", width=2, dash="dot")
            ),
            secondary_y=False
        )
        
        # Add daily returns on secondary y-axis with error handling
        if hasattr(results, 'daily_returns') and not results.daily_returns.empty:
            # Convert to percentage and handle NaN values
            daily_returns_pct = results.daily_returns.fillna(0) * 100
            
            fig.add_trace(
                go.Bar(
                    x=daily_returns_pct.index,
                    y=daily_returns_pct.values,
                    name="Daily Return %",
                    marker_color=daily_returns_pct.apply(
                        lambda x: "green" if x >= 0 else "red"
                    ),
                    opacity=0.3
                ),
                secondary_y=True
            )
        
        # Update layout
        fig.update_layout(
            title="Portfolio Performance",
            xaxis_title="Date",
            yaxis_title="Value (£)",
            yaxis2_title="Daily Return (%)",
            legend=dict(x=0.01, y=0.99),
            hovermode="x unified"
        )
        
        # Update y-axis ranges
        fig.update_yaxes(
            title_text="Value (£)",
            secondary_y=False
        )
        fig.update_yaxes(
            title_text="Daily Return (%)",
            secondary_y=True,
            range=[-5, 5]  # Limit range for better visibility
        )
        
        return fig
        
    except Exception as e:
        # Create a simple fallback chart if anything goes wrong
        fallback_fig = go.Figure()
        fallback_fig.add_trace(go.Scatter(x=[0], y=[0], mode='markers'))
        fallback_fig.update_layout(
            title="Portfolio Performance (Error - See Console for Details)",
            xaxis_title="Date",
            yaxis_title="Value (£)"
        )
        
        return fallback_fig

def create_transactions_table(transaction_records):
    """Create formatted transactions table from pre-calculated transaction records"""
    if not transaction_records:
        return pd.DataFrame(columns=[
            'Date', 'Symbol', 'Type', 'Signal', 'Shares', 'Price', 
            'Fees', 'Total', 'Available Capital', 'Investment Value', 'Portfolio Total'
        ])
    
    # Convert TransactionRecord objects to dictionaries for DataFrame
    records = [tr.get_formatted_record() for tr in transaction_records]
    
    # Create DataFrame
    df = pd.DataFrame(records)
    
    # Check if DataFrame is empty before proceeding with further operations
    if len(df) == 0:
        return df
    
    # Sort by sequence number to ensure correct order of execution is preserved
    if 'Sequence' in df.columns:
        df = df.sort_values('Sequence', ascending=True)
        # Drop the sequence column from the display (we only needed it for sorting)
        df = df.drop(columns=['Sequence'])
    else:
        # Fallback to date sorting if sequence not available
        try:
            df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')
            df = df.sort_values('Date', ascending=True)
            df['Date'] = df['Date'].dt.strftime('%d/%m/%Y')
        except Exception as e:
            pass
    
    # Force Shares column to be integer type
    if 'Shares' in df.columns:
        # First ensure there are no NaN values
        df['Shares'] = df['Shares'].fillna(0)
        # Convert to integer
        df['Shares'] = df['Shares'].astype(int)
    
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

    # Function to handle simulation execution with sidebar state
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

    # Run simulation button with on_click handler
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
        
        # Create transaction table from pre-built transaction records, sorted by sequence number
        transactions_df = create_transactions_table(results.transaction_records)
        
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