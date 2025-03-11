import os
import streamlit as st
from typing import Dict, Any, Optional

def get_api_keys() -> Dict[str, Any]:
    """
    Get API keys from environment variables or user inputs
    """
    # Check if API keys are already stored in session state
    if 'binance_api_key' not in st.session_state or 'binance_api_secret' not in st.session_state:
        # Check environment variables first
        api_key = os.getenv("BINANCE_API_KEY", "")
        api_secret = os.getenv("BINANCE_API_SECRET", "")
        
        # Store in session state
        st.session_state['binance_api_key'] = api_key
        st.session_state['binance_api_secret'] = api_secret
    
    return {
        'binance_api_key': st.session_state['binance_api_key'],
        'binance_api_secret': st.session_state['binance_api_secret']
    }

def set_api_keys(api_key: str, api_secret: str) -> None:
    """
    Set API keys in session state
    """
    st.session_state['binance_api_key'] = api_key
    st.session_state['binance_api_secret'] = api_secret

def is_authenticated() -> bool:
    """
    Check if API keys are set
    """
    keys = get_api_keys()
    return bool(keys['binance_api_key'] and keys['binance_api_secret'])