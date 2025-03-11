import streamlit as st
import pandas as pd
from api.tradingview_client import TradingViewClient
from utils.config import get_api_keys, set_api_keys, is_authenticated

def render_sidebar():
    """Render the sidebar with settings"""
    with st.sidebar:
        st.header("Market Settings")
        
        # API Configuration Section (No API keys needed for TradingView)
        with st.expander("API Information", expanded=False):
            st.markdown("**TradingView API Information**")
            st.markdown("""
            This application uses the TradingView API to fetch market data. No authentication is required
            as we're using the public API endpoints.
            
            Features include:
            - Real-time price data
            - Technical indicators
            - Market analytics
            """)
            
            # TradingView link 
            st.markdown("[Visit TradingView](https://www.tradingview.com/)")
            
        # Display connection status
        if hasattr(st.session_state, 'api_client') and st.session_state.api_client:
            try:
                # Try to fetch a test symbol to check connection
                test_symbol = "BTCUSDT"
                ticker = st.session_state.api_client.get_ticker(test_symbol)
                if ticker:
                    st.success("Connected to TradingView API")
                    st.info("Using public API access")
                else:
                    st.error("Failed to connect to TradingView API")
                    st.info("Please check your internet connection or try again later")
            except Exception as e:
                st.error(f"Error connecting to TradingView API: {e}")
                st.info("Using cached data where available")
        
        # Get available symbols
        try:
            # Get symbols from TradingView client
            available_symbols = st.session_state.api_client.get_available_symbols()
            if not available_symbols:
                # Fallback to common symbols if not available
                available_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT", "XRPUSDT"]
        except Exception as e:
            # Fallback to common symbols on error
            st.warning(f"Unable to fetch available trading pairs: {str(e)}")
            available_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT", "XRPUSDT"]
        
        # Cryptocurrency selection
        st.subheader("Select Cryptocurrency")
        selected_crypto = st.selectbox(
            "Trading Pair",
            available_symbols,
            index=available_symbols.index(st.session_state.selected_crypto) if st.session_state.selected_crypto in available_symbols else 0
        )
        
        if selected_crypto != st.session_state.selected_crypto:
            st.session_state.selected_crypto = selected_crypto
            st.rerun()
        
        # Timeframe selection
        st.subheader("Select Timeframe")
        timeframe_options = {
            "1m": "1 Minute",
            "3m": "3 Minutes",
            "5m": "5 Minutes",
            "15m": "15 Minutes",
            "30m": "30 Minutes",
            "1h": "1 Hour",
            "4h": "4 Hours",
            "1d": "1 Day"
        }
        selected_timeframe = st.selectbox(
            "Chart Timeframe",
            list(timeframe_options.keys()),
            format_func=lambda x: timeframe_options[x],
            index=list(timeframe_options.keys()).index(st.session_state.timeframe) if st.session_state.timeframe in timeframe_options else 0
        )
        
        if selected_timeframe != st.session_state.timeframe:
            st.session_state.timeframe = selected_timeframe
            st.rerun()
        
        # Technical indicators section
        st.subheader("Technical Indicators")
        
        # Create a checkbox for each indicator
        indicators = {
            "EMA 9": "EMA 9",
            "EMA 21": "EMA 21",
            "EMA 50": "EMA 50",
            "EMA 200": "EMA 200",
            "Bollinger Bands": "Bollinger Bands (20,2)",
            "RSI": "RSI (14)",
            "MACD": "MACD (12,26,9)",
            "Volume": "Volume"
        }
        
        indicator_states = {}
        for key, label in indicators.items():
            indicator_states[key] = st.checkbox(
                label,
                value=st.session_state.indicators.get(key, False)
            )
        
        # Update session state if indicators changed
        if indicator_states != st.session_state.indicators:
            st.session_state.indicators = indicator_states
            st.rerun()
        
        # Auto-refresh option
        st.subheader("Data Settings")
        auto_refresh = st.checkbox("Auto-refresh data", value=st.session_state.auto_refresh)
        if auto_refresh != st.session_state.auto_refresh:
            st.session_state.auto_refresh = auto_refresh
        
        if auto_refresh:
            refresh_interval = st.slider(
                "Refresh interval (seconds)",
                min_value=5,
                max_value=60,
                value=st.session_state.refresh_interval,
                step=5
            )
            if refresh_interval != st.session_state.refresh_interval:
                st.session_state.refresh_interval = refresh_interval
        
        # Manually refresh button
        if st.button("Refresh Data Now"):
            st.session_state.last_update = 0  # Force refresh
            st.rerun()
            
        # Display app info
        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        **CryptoScalp AI** provides real-time analytics and trading signals for cryptocurrency scalping.
        
        - Data provided by TradingView API
        - View technical indicators
        - Get AI-powered trading signals
        - Store signals in PostgreSQL database
        """)
