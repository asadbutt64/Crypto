import streamlit as st
import pandas as pd
import time
from utils.indicators import TechnicalIndicators
from components.chart import render_price_chart, render_indicator_charts
from components.signals import render_trade_signals

def render_dashboard():
    """Render the main dashboard content"""
    # Get selected cryptocurrency and timeframe from session state
    symbol = st.session_state.selected_crypto
    timeframe = st.session_state.timeframe
    indicators = st.session_state.indicators
    
    # Check API client connection status
    if not st.session_state.api_client.connected:
        if st.session_state.api_client.geo_restricted:
            st.error("Binance API access is restricted from your location")
            st.warning("""
            ### API Access Error
            
            The Binance API is unavailable from your current location due to geographic restrictions.
            
            **Solutions:**
            1. Provide your own Binance API keys in the sidebar
            2. Use a VPN to access from a supported region
            
            API keys can be obtained from your Binance account under API Management.
            """)
        else:
            st.error(f"Failed to connect to Binance API: {st.session_state.api_client.error_message}")
            st.warning("""
            ### Connection Issue
            
            Unable to connect to the Binance API. This could be due to:
            - Network connectivity issues
            - Invalid API credentials
            - Binance API service disruption
            
            Please check your connection and API settings in the sidebar.
            """)
            
        # Show a sample data visualization message
        st.info("The dashboard will display market data and signals once connected to the Binance API.")
        return
    
    # Create placeholder for price chart
    chart_placeholder = st.empty()
    
    # Display loading message while fetching data
    with chart_placeholder.container():
        with st.spinner(f"Loading {symbol} data..."):
            try:
                # Fetch klines data
                df = st.session_state.api_client.get_klines(symbol, timeframe, limit=500)
                
                if df.empty:
                    st.error(f"Failed to fetch data for {symbol}. Please try another cryptocurrency or check your connection.")
                    return
            except Exception as e:
                st.error(f"Error fetching data: {str(e)}")
                st.info("Please check your connection and API settings in the sidebar.")
                return
    
    # Create dashboard tabs
    tab1, tab2 = st.tabs(["Chart & Analysis", "Trading Signals"])
    
    with tab1:
        # Create columns for chart and info
        chart_col, info_col = st.columns([3, 1])
        
        with chart_col:
            # Render price chart with indicators
            df_with_indicators = render_price_chart(df, indicators, symbol, timeframe)
            
            # Render additional indicator charts
            render_indicator_charts(df_with_indicators, indicators)
        
        with info_col:
            # Display current price card
            try:
                current_price = st.session_state.api_client.get_current_price(symbol)
                
                if current_price:
                    # Calculate price change
                    price_change = current_price - df['close'].iloc[-2]
                    price_change_pct = price_change / df['close'].iloc[-2] * 100
                    
                    # Display current price and change
                    price_color = "green" if price_change >= 0 else "red"
                    
                    st.markdown(f"## Current Price")
                    st.markdown(f"<h2 style='color: {price_color};'>${current_price:.4f}</h2>", unsafe_allow_html=True)
                    
                    # Display price change
                    change_text = "+" if price_change >= 0 else ""
                    st.markdown(f"<p style='color: {price_color};'>{change_text}{price_change:.4f} ({change_text}{price_change_pct:.2f}%)</p>", unsafe_allow_html=True)
                else:
                    st.markdown(f"## Current Price")
                    st.markdown("Price data unavailable")
            except Exception as e:
                st.markdown(f"## Current Price")
                st.markdown("Price data unavailable")
            
            # Display trading pair and timeframe info
            st.markdown("---")
            st.markdown(f"**Trading Pair**: {symbol}")
            st.markdown(f"**Timeframe**: {timeframe}")
            
            # Show active indicators
            st.markdown("---")
            st.markdown("**Active Indicators**:")
            active_indicators = [k for k, v in indicators.items() if v]
            if active_indicators:
                for ind in active_indicators:
                    st.markdown(f"- {ind}")
            else:
                st.markdown("No indicators selected")
                
            # Show pattern detection (if available)
            st.markdown("---")
            st.markdown("**Pattern Detection**:")
            
            # Simple candlestick pattern detection
            try:
                last_candles = df.iloc[-5:].copy()
                
                # Check for bullish engulfing
                if (last_candles['open'].iloc[-2] > last_candles['close'].iloc[-2] and  # Prior red candle
                    last_candles['open'].iloc[-1] < last_candles['close'].iloc[-1] and  # Current green candle
                    last_candles['open'].iloc[-1] <= last_candles['close'].iloc[-2] and  # Current open below prior close
                    last_candles['close'].iloc[-1] > last_candles['open'].iloc[-2]):     # Current close above prior open
                    
                    st.markdown("🟢 **Bullish Engulfing Pattern**")
                # Check for bearish engulfing
                elif (last_candles['open'].iloc[-2] < last_candles['close'].iloc[-2] and  # Prior green candle
                      last_candles['open'].iloc[-1] > last_candles['close'].iloc[-1] and  # Current red candle
                      last_candles['open'].iloc[-1] >= last_candles['close'].iloc[-2] and  # Current open above prior close
                      last_candles['close'].iloc[-1] < last_candles['open'].iloc[-2]):     # Current close below prior open
                    
                    st.markdown("🔴 **Bearish Engulfing Pattern**")
                # Check for doji
                elif abs(last_candles['open'].iloc[-1] - last_candles['close'].iloc[-1]) / (last_candles['high'].iloc[-1] - last_candles['low'].iloc[-1]) < 0.1:
                    st.markdown("⚪ **Doji Pattern** (Indecision)")
                # Check for hammer
                elif (last_candles['high'].iloc[-1] - max(last_candles['open'].iloc[-1], last_candles['close'].iloc[-1])) < (min(last_candles['open'].iloc[-1], last_candles['close'].iloc[-1]) - last_candles['low'].iloc[-1]) * 0.25:
                    st.markdown("🟢 **Hammer Pattern** (Potential Reversal)")
                else:
                    st.markdown("No significant patterns detected")
            except:
                st.markdown("Pattern detection unavailable")
    
    with tab2:
        # Render trading signals
        render_trade_signals(df_with_indicators, symbol, timeframe)
