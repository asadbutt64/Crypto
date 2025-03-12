import streamlit as st
import pandas as pd
import time
from api.tradingview_client import TradingViewClient
from components.sidebar import render_sidebar
from components.dashboard import render_dashboard
from utils.config import get_api_keys, is_authenticated
from utils.indicators import TechnicalIndicators
from models.signal_generator import SignalGenerator
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
# Track the API keys to detect changes
if 'last_api_keys' not in st.session_state:
    st.session_state.last_api_keys = get_api_keys()

# Check if API keys have changed and recreate client if needed
current_api_keys = get_api_keys()
api_keys_changed = (st.session_state.last_api_keys != current_api_keys)

if 'api_client' not in st.session_state or api_keys_changed:
    # Initialize or reinitialize TradingView API client
    st.session_state.api_client = TradingViewClient()
    # Update the last known API keys
    st.session_state.last_api_keys = current_api_keys.copy()

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
        st.rerun()
        
# AI Trading Recommendations
st.markdown("---")
st.markdown("<h2 style='text-align: center;'>AI Trading Recommendations</h2>", unsafe_allow_html=True)

# Create a function to generate trading recommendations for different timeframes
def get_ai_recommendations():
    recommendations = {}
    timeframes = ["1m", "5m", "15m", "30m", "1h", "4h"]
    
    symbol = st.session_state.selected_crypto
    
    for tf in timeframes:
        try:
            # Try to get data for this timeframe
            df = st.session_state.api_client.get_klines(symbol, tf, limit=100)
            if df.empty:
                recommendations[tf] = {"signal": "NEUTRAL", "entry": None, "exit": None, "stop_loss": None, "confidence": 0}
                continue
                
            # Add indicators
            df_with_indicators = TechnicalIndicators.add_indicators(df)
            
            # Generate signals using SignalGenerator
            signal_generator = SignalGenerator()
            price_levels = signal_generator.predict_price_levels(df_with_indicators, symbol, tf)
            
            if price_levels['entry'] is not None:
                is_long = price_levels['entry'] < price_levels['exit']
                signal_type = "BUY" if is_long else "SELL"
                
                recommendations[tf] = {
                    "signal": signal_type,
                    "entry": price_levels['entry'],
                    "exit": price_levels['exit'],
                    "stop_loss": price_levels['stop_loss'],
                    "confidence": price_levels['confidence'],
                    "risk_reward": price_levels['risk_reward']
                }
            else:
                recommendations[tf] = {"signal": "NEUTRAL", "entry": None, "exit": None, "stop_loss": None, "confidence": 0}
        except Exception as e:
            recommendations[tf] = {"signal": "ERROR", "entry": None, "exit": None, "stop_loss": None, "confidence": 0, "error": str(e)}
    
    return recommendations

# Get recommendations
recommendations = get_ai_recommendations()

# Create grid display for the recommendations
col1, col2 = st.columns(2)

with col1:
    st.markdown("### Short-term Timeframes")
    for tf in ["1m", "5m", "15m"]:
        rec = recommendations[tf]
        signal_color = "green" if rec["signal"] == "BUY" else "red" if rec["signal"] == "SELL" else "gray"
        
        st.markdown(f"#### {tf} Timeframe")
        st.markdown(f"**Signal**: <span style='color:{signal_color};'>{rec['signal']}</span>", unsafe_allow_html=True)
        
        if rec["entry"] is not None:
            confidence_pct = int(rec["confidence"] * 100)
            st.markdown(f"**Confidence**: {confidence_pct}%")
            st.markdown(f"**Entry Point**: ${rec['entry']:.4f}")
            st.markdown(f"**Take Profit**: ${rec['exit']:.4f}")
            st.markdown(f"**Stop Loss**: ${rec['stop_loss']:.4f}")
            st.markdown(f"**Risk:Reward**: 1:{rec['risk_reward']:.1f}")
        else:
            st.markdown("*No clear setup at this time*")
        
        st.markdown("---")

with col2:
    st.markdown("### Medium-term Timeframes")
    for tf in ["30m", "1h", "4h"]:
        rec = recommendations[tf]
        signal_color = "green" if rec["signal"] == "BUY" else "red" if rec["signal"] == "SELL" else "gray"
        
        st.markdown(f"#### {tf} Timeframe")
        st.markdown(f"**Signal**: <span style='color:{signal_color};'>{rec['signal']}</span>", unsafe_allow_html=True)
        
        if rec["entry"] is not None:
            confidence_pct = int(rec["confidence"] * 100)
            st.markdown(f"**Confidence**: {confidence_pct}%")
            st.markdown(f"**Entry Point**: ${rec['entry']:.4f}")
            st.markdown(f"**Take Profit**: ${rec['exit']:.4f}")
            st.markdown(f"**Stop Loss**: ${rec['stop_loss']:.4f}")
            st.markdown(f"**Risk:Reward**: 1:{rec['risk_reward']:.1f}")
        else:
            st.markdown("*No clear setup at this time*")
        
        st.markdown("---")

# Footer
st.markdown("---")
st.markdown("<p style='text-align: center;'>CryptoScalp AI | Real-time Analytics & Trading Signals | Data from TradingView</p>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 0.8em;'>Disclaimer: Trading cryptocurrencies involves risk. This tool provides analysis, not financial advice.</p>", unsafe_allow_html=True)
