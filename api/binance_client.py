import pandas as pd
import numpy as np
import os
from binance.client import Client
from datetime import datetime, timedelta
import time
import streamlit as st

class BinanceClient:
    def __init__(self):
        # If API keys are provided in environment variables, use them
        api_key = os.getenv("BINANCE_API_KEY", "")
        api_secret = os.getenv("BINANCE_API_SECRET", "")
        
        try:
            # Initialize client with or without API keys
            if api_key and api_secret:
                self.client = Client(api_key, api_secret)
                # Ping the server to test connection
                self.client.ping()
                self.authenticated = True
            else:
                # Use unauthenticated client for public API access only
                self.client = Client()
                self.authenticated = False
                
            # Test connection
            server_time = self.client.get_server_time()
            self.connected = True
            
        except Exception as e:
            self.connected = False
            print(f"Failed to connect to Binance API: {e}")
            
    @st.cache_data(ttl=60)  # Cache for 60 seconds
    def get_available_symbols(self):
        """Get available trading pairs"""
        try:
            exchange_info = self.client.get_exchange_info()
            symbols = [s['symbol'] for s in exchange_info['symbols'] if s['quoteAsset'] == 'USDT']
            return sorted(symbols)
        except Exception as e:
            print(f"Error fetching symbols: {e}")
            return ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT", "XRPUSDT"]
    
    @st.cache_data(ttl=15)  # Cache for 15 seconds
    def get_klines(self, symbol, interval, limit=500):
        """Get klines/candlestick data"""
        try:
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            # Create DataFrame with OHLCV data
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convert numeric columns
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 
                             'quote_asset_volume', 'taker_buy_base_asset_volume', 
                             'taker_buy_quote_asset_volume']
            
            df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric)
            
            # Convert timestamps to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
        except Exception as e:
            print(f"Error fetching klines for {symbol}: {e}")
            return pd.DataFrame()
    
    @st.cache_data(ttl=5)  # Cache for 5 seconds
    def get_ticker(self, symbol):
        """Get current price ticker"""
        try:
            ticker = self.client.get_ticker(symbol=symbol)
            return ticker
        except Exception as e:
            print(f"Error fetching ticker for {symbol}: {e}")
            return None
            
    @st.cache_data(ttl=15)  # Cache for 15 seconds
    def get_depth(self, symbol, limit=500):
        """Get order book data"""
        try:
            depth = self.client.get_order_book(symbol=symbol, limit=limit)
            return depth
        except Exception as e:
            print(f"Error fetching order book for {symbol}: {e}")
            return None

    def get_current_price(self, symbol):
        """Get only the current price for a symbol"""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            print(f"Error fetching current price for {symbol}: {e}")
            return None
    
    @st.cache_data(ttl=60*5)  # Cache for 5 minutes
    def get_24h_stats(self, symbol):
        """Get 24-hour statistics"""
        try:
            stats = self.client.get_ticker(symbol=symbol)
            return {
                'price_change': float(stats['priceChange']),
                'price_change_percent': float(stats['priceChangePercent']),
                'high': float(stats['highPrice']),
                'low': float(stats['lowPrice']),
                'volume': float(stats['volume']),
                'quote_volume': float(stats['quoteVolume'])
            }
        except Exception as e:
            print(f"Error fetching 24h stats for {symbol}: {e}")
            return None
