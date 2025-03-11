import streamlit as st
import pandas as pd
import time
from api.binance_client import BinanceClient
from components.sidebar import render_sidebar
from components.dashboard import render_dashboard
import os

# Set page configuration
st.set_page_config(
    page_title="CryptoScalp AI - Trading Assistant",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
with open('assets/style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Initialize session state variables if they don't exist
if 'selected_crypto' not in st.session_state:
    st.session_state.selected_crypto = "BTCUSDT"
if 'timeframe' not in st.session_state:
    st.session_state.timeframe = "1m"
if 'indicators' not in st.session_state:
    st.session_state.indicators = {
        "EMA 9": True,
        "EMA 21": True,
        "EMA 50": False,
        "EMA 200": False,
        "Bollinger Bands": True,
        "RSI": True,
        "MACD": True,
        "Volume": True
    }
if 'api_client' not in st.session_state:
    # Initialize Binance API client
    st.session_state.api_client = BinanceClient()
if 'last_update' not in st.session_state:
    st.session_state.last_update = time.time()
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = True
if 'refresh_interval' not in st.session_state:
    st.session_state.refresh_interval = 15  # Default 15 seconds

# Application header
st.markdown("<h1 style='text-align: center;'>CryptoScalp AI - Trading Assistant</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>AI-powered cryptocurrency trading signals for short-term scalping (1-5 min)</p>", unsafe_allow_html=True)

# Render sidebar (cryptocurrency selection, timeframe, indicators)
render_sidebar()

# Main dashboard content
try:
    render_dashboard()
except Exception as e:
    st.error(f"Error: {e}")
    st.info("Please check your connection and try again.")

# Auto-refresh logic
if st.session_state.auto_refresh:
    time_since_update = time.time() - st.session_state.last_update
    if time_since_update >= st.session_state.refresh_interval:
        st.session_state.last_update = time.time()
        st.experimental_rerun()
        
# Footer
st.markdown("---")
st.markdown("<p style='text-align: center;'>CryptoScalp AI | Real-time Analytics & Trading Signals | Data from Binance</p>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 0.8em;'>Disclaimer: Trading cryptocurrencies involves risk. This tool provides analysis, not financial advice.</p>", unsafe_allow_html=True)
