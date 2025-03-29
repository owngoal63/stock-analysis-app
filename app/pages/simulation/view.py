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
    """Create portfolio value and composition chart with safeguards against non-numeric data"""
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.7, 0.3],
        specs=[[{"secondary_y": True}],
               [{"secondary_y": False}]],
        subplot_titles=("Portfolio Value", "Asset Allocation"),
        vertical_spacing=0.12
    )
    
    # Check if results contain valid data before proceeding
    try:
        # Add initial capital point to the data
        initial_date = results.portfolio_values.index[0] - pd.Timedelta(days=1)
        
        # Ensure all data is numeric before concatenation
        initial_capital_series = pd.Series({initial_date: float(results.initial_capital)})
        
        # Convert portfolio values to numeric
        portfolio_values_numeric = pd.to_numeric(results.portfolio_values, errors='coerce')
        cash_values_numeric = pd.to_numeric(results.cash_values, errors='coerce')
        positions_values_numeric = pd.to_numeric(results.positions_values, errors='coerce')
        daily_returns_numeric = pd.to_numeric(results.daily_returns, errors='coerce')
        
        # Replace NaN values with 0
        portfolio_values_numeric = portfolio_values_numeric.fillna(0)
        cash_values_numeric = cash_values_numeric.fillna(0)
        positions_values_numeric = positions_values_numeric.fillna(0)
        daily_returns_numeric = daily_returns_numeric.fillna(0)
        
        # Combine series with initial values
        portfolio_values = pd.concat([
            initial_capital_series,
            portfolio_values_numeric
        ])
        
        cash_values = pd.concat([
            initial_capital_series,
            cash_values_numeric
        ])
        
        positions_values = pd.concat([
            pd.Series({initial_date: 0.0}),
            positions_values_numeric
        ])
        
        daily_returns = pd.concat([
            pd.Series({initial_date: 0.0}),
            daily_returns_numeric
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
        
    except Exception as e:
        # If there's an error, return a simple empty figure with an error message
        print(f"Error creating portfolio chart: {str(e)}")
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error creating chart: Could not process numeric data",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig

def create_transactions_table(transactions, initial_capital: float):
    """Create formatted transactions table with running totals"""
    if not transactions:
        return pd.DataFrame(columns=[
            'Date', 'Symbol', 'Type', 'Signal', 'Shares', 'Price', 
            'Fees', 'Total', 'Available Capital', 'Investment Value', 'Portfolio Total'
        ])
    
    # ZERO SHARE PREVENTION: Filter out any zero-share transactions before processing
    valid_transactions = []
    for t in transactions:
        try:
            shares = int(t.shares) if hasattr(t, 'shares') and t.shares is not None else 0
            if shares > 0:
                valid_transactions.append(t)
            else:
                print(f"Filtering out zero-share transaction: {t.date} {t.symbol} {getattr(t.transaction_type, 'value', '')}")
        except (ValueError, TypeError, AttributeError):
            # Skip transactions where shares can't be determined
            print(f"Skipping transaction with invalid shares attribute")
    
    if not valid_transactions:
        return pd.DataFrame(columns=[
            'Date', 'Symbol', 'Type', 'Signal', 'Shares', 'Price', 
            'Fees', 'Total', 'Available Capital', 'Investment Value', 'Portfolio Total'
        ])
    
    # Continue with the rest of the function using valid_transactions
    records = []
    running_investments = {}
    available_capital = initial_capital
    
    # Sort transactions chronologically
    sorted_transactions = sorted(valid_transactions, key=lambda x: x.date)
    
    for t in sorted_transactions:
        # Extract transaction attributes safely
        transaction_type = getattr(t.transaction_type, 'value', str(t.transaction_type))
        signal_type = getattr(t.signal_type, 'value', str(t.signal_type))
        
        # Safely convert shares to positive integer
        shares = int(t.shares) if hasattr(t, 'shares') and t.shares is not None else 0
        if shares <= 0:
            continue  # Skip this transaction if shares is 0 or negative
        
        if transaction_type == "Buy":
            shares_cost = shares * t.price
            fees = t.fees
            available_capital = available_capital - shares_cost - fees
            transaction_total = shares_cost + fees
            
            # Update position for bought stock
            if t.symbol not in running_investments:
                running_investments[t.symbol] = {'shares': 0, 'price': t.price}
            running_investments[t.symbol]['shares'] += shares
            running_investments[t.symbol]['price'] = t.price
            
        else:  # SELL
            # IMPORTANT: For sell transactions, we must use the shares from the transaction
            # directly, not calculated from position value
            sale_proceeds = shares * t.price
            fees = t.fees
            available_capital = available_capital + (sale_proceeds - fees)
            transaction_total = sale_proceeds - fees
            
            # Update position for sold stock
            if t.symbol in running_investments:
                running_investments[t.symbol]['shares'] -= shares
                running_investments[t.symbol]['price'] = t.price
                
                if running_investments[t.symbol]['shares'] <= 0:
                    del running_investments[t.symbol]
        
        # Calculate current investment value by summing value of all current positions
        # Safely calculate investment value
        current_investment_value = 0.0
        for sym, pos in running_investments.items():
            try:
                shares_val = float(pos['shares'])
                price_val = float(pos['price'])
                current_investment_value += shares_val * price_val
            except (ValueError, TypeError):
                # Skip this position if values can't be converted to float
                pass
        
        # Create record with explicit integer for Shares
        record = {
            'Date': t.date.strftime('%d/%m/%Y'),
            'Symbol': t.symbol,
            'Type': transaction_type,
            'Signal': signal_type,
            'Shares': shares,  # Explicitly converted integer value
            'Price': f"£{t.price:.2f}",
            'Fees': f"£{t.fees:.2f}",
            'Total': f"£{transaction_total:.2f}",
            'Available Capital': f"£{available_capital:.2f}",
            'Investment Value': f"£{current_investment_value:.2f}",
            'Portfolio Total': f"£{(available_capital + current_investment_value):.2f}"
        }
        
        records.append(record)
    
    # Create DataFrame with explicit dtypes to prevent conversion issues
    df = pd.DataFrame(records)
    
    # Check if DataFrame is empty before proceeding with further operations
    if len(df) == 0:
        return df
    
    # Force Shares column to be integer type - this is critical
    if 'Shares' in df.columns:
        # First ensure there are no NaN values
        df['Shares'] = df['Shares'].fillna(0)
        # Convert to integer
        df['Shares'] = df['Shares'].astype(int)
        
    # Format date column - safely handle conversion
    try:
        df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')
        df = df.sort_values('Date', ascending=True)
        df['Date'] = df['Date'].dt.strftime('%d/%m/%Y')
    except Exception as e:
        # If date conversion fails, just return the DataFrame as is
        print(f"Warning: Date conversion error - {str(e)}")
    
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