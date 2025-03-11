import pandas as pd
import numpy as np
import time
import datetime
from tradingview_ta import TA_Handler, Interval, Exchange
import streamlit as st

from database.db_manager import DBManager

class TradingViewClient:
    """Client for interacting with TradingView data"""
    
    def __init__(self):
        """Initialize the TradingView client"""
        self.db_manager = DBManager()
        
        # Available intervals mapping
        self.intervals = {
            "1m": Interval.INTERVAL_1_MINUTE,
            "5m": Interval.INTERVAL_5_MINUTES,
            "15m": Interval.INTERVAL_15_MINUTES,
            "30m": Interval.INTERVAL_30_MINUTES,
            "1h": Interval.INTERVAL_1_HOUR,
            "4h": Interval.INTERVAL_4_HOURS,
            "1d": Interval.INTERVAL_1_DAY,
            "1W": Interval.INTERVAL_1_WEEK,
            "1M": Interval.INTERVAL_1_MONTH
        }
        
        # Cache for data to avoid repeated API calls
        self.cache = {
            "symbols": None,
            "klines": {},
            "ticker": {},
            "stats": {}
        }
        
        # Cache expiry time (in seconds)
        self.cache_expiry = {
            "symbols": 3600,  # 1 hour
            "klines": 300,    # 5 minutes
            "ticker": 60,     # 1 minute
            "stats": 300      # 5 minutes
        }
        
        # Cache timestamps
        self.cache_timestamp = {
            "symbols": 0,
            "klines": {},
            "ticker": {},
            "stats": {}
        }
    
    def _format_symbol_for_tv(self, symbol):
        """Format a symbol for TradingView API (e.g., BTCUSDT -> BINANCE:BTCUSDT)"""
        # If already has exchange prefix, return as is
        if ":" in symbol:
            return symbol
        
        # Default to Binance if no exchange specified
        # This can be enhanced to support more exchanges based on user settings
        return f"BINANCE:{symbol}"
    
    def _parse_symbol_from_tv(self, tv_symbol):
        """Parse a raw symbol from TradingView format (e.g., BINANCE:BTCUSDT -> BTCUSDT)"""
        if ":" in tv_symbol:
            return tv_symbol.split(":")[1]
        return tv_symbol
    
    def _extract_exchange(self, symbol):
        """Extract the exchange from a formatted symbol (e.g., BINANCE:BTCUSDT -> BINANCE)"""
        if ":" in symbol:
            return symbol.split(":")[0]
        return "BINANCE"  # Default to Binance if no exchange specified
    
    def _cache_expired(self, cache_type, key=None):
        """Check if cache has expired"""
        now = time.time()
        
        if key:
            # For caches with keys (klines, ticker, stats)
            if key not in self.cache_timestamp.get(cache_type, {}):
                return True
            return now - self.cache_timestamp[cache_type][key] > self.cache_expiry[cache_type]
        else:
            # For caches without keys (symbols)
            return now - self.cache_timestamp[cache_type] > self.cache_expiry[cache_type]
    
    def _update_cache_timestamp(self, cache_type, key=None):
        """Update the cache timestamp"""
        now = time.time()
        
        if key:
            # For caches with keys (klines, ticker, stats)
            if cache_type not in self.cache_timestamp:
                self.cache_timestamp[cache_type] = {}
            self.cache_timestamp[cache_type][key] = now
        else:
            # For caches without keys (symbols)
            self.cache_timestamp[cache_type] = now
    
    def _get_available_symbols_internal(self):
        """Get available trading pairs (internal implementation)"""
        try:
            # This is a simplified approach - the TradingView TA library doesn't have
            # a direct method to get all available symbols
            # In a real implementation, you might want to use a more comprehensive approach
            
            # Commonly used cryptocurrency pairs on Binance
            common_cryptos = [
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
                "DOGEUSDT", "SOLUSDT", "MATICUSDT", "DOTUSDT", "LTCUSDT",
                "AVAXUSDT", "LINKUSDT", "UNIUSDT", "ATOMUSDT", "ETCUSDT"
            ]
            
            # Format with exchange prefix
            formatted_symbols = [f"BINANCE:{symbol}" for symbol in common_cryptos]
            
            return formatted_symbols
        except Exception as e:
            st.warning(f"Error getting available symbols from TradingView: {e}")
            return []
    
    def get_available_symbols(self):
        """Get available trading pairs (cached wrapper)"""
        if self.cache["symbols"] is None or self._cache_expired("symbols"):
            self.cache["symbols"] = self._get_available_symbols_internal()
            self._update_cache_timestamp("symbols")
        
        return self.cache["symbols"]
    
    def _get_klines_internal(self, symbol, interval, limit=500):
        """Get klines/candlestick data (internal implementation)"""
        try:
            # Format symbol for TradingView
            formatted_symbol = self._format_symbol_for_tv(symbol)
            exchange = self._extract_exchange(formatted_symbol)
            raw_symbol = self._parse_symbol_from_tv(formatted_symbol)
            
            # Map interval to TradingView interval
            if interval not in self.intervals:
                raise ValueError(f"Unsupported interval: {interval}")
            
            tv_interval = self.intervals[interval]
            
            # Initialize TA_Handler
            handler = TA_Handler(
                symbol=raw_symbol,
                exchange=exchange,
                screener="crypto",  # For cryptocurrencies
                interval=tv_interval,
                timeout=10
            )
            
            # Get analysis which includes current OHLCV data
            analysis = handler.get_analysis()
            
            # Unfortunately, TradingView TA doesn't directly provide historical data beyond
            # what's available in the current analysis
            # For a production app, you might want to use a different API or maintain
            # your own time series database
            
            # Extract current OHLCV data
            current_data = {
                "timestamp": datetime.datetime.now(),
                "open": analysis.indicators["open"],
                "high": analysis.indicators["high"],
                "low": analysis.indicators["low"],
                "close": analysis.indicators["close"],
                "volume": analysis.indicators["volume"]
            }
            
            # Create a DataFrame with the current data point
            df = pd.DataFrame([current_data])
            
            # Check if we have historical data in the database
            db_data = self.db_manager.get_price_data(symbol, interval, limit=limit-1)
            
            if not db_data.empty:
                # Combine database data with current data
                # Ensure the current data is newer than the most recent db data
                if df.iloc[0]["timestamp"] > db_data["timestamp"].max():
                    df = pd.concat([db_data, df]).reset_index(drop=True)
                else:
                    df = db_data
            
            # Sort by timestamp to ensure chronological order
            df = df.sort_values("timestamp").reset_index(drop=True)
            
            # Limit to requested number of candles
            if len(df) > limit:
                df = df.iloc[-limit:]
            
            # Save the current data point to the database
            self.db_manager.save_price_data(
                pd.DataFrame([current_data]), 
                symbol, 
                interval
            )
            
            return df
        except Exception as e:
            st.warning(f"Error getting klines from TradingView: {e}")
            
            # Try to get data from database as fallback
            db_data = self.db_manager.get_price_data(symbol, interval, limit=limit)
            if not db_data.empty:
                return db_data
            
            # If all else fails, return empty DataFrame with correct structure
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    
    def get_klines(self, symbol, interval, limit=500):
        """
        Get klines/candlestick data (cached wrapper)
        First tries to get from cache, then database, then falls back to API if needed
        """
        cache_key = f"{symbol}_{interval}_{limit}"
        
        if cache_key not in self.cache["klines"] or self._cache_expired("klines", cache_key):
            # Try to get from database first
            db_data = self.db_manager.get_price_data(symbol, interval, limit=limit)
            
            if not db_data.empty and len(db_data) >= limit:
                # If database has enough data, use it
                self.cache["klines"][cache_key] = db_data
            else:
                # Otherwise, get from API
                self.cache["klines"][cache_key] = self._get_klines_internal(symbol, interval, limit)
            
            self._update_cache_timestamp("klines", cache_key)
        
        return self.cache["klines"][cache_key]
    
    def _get_ticker_internal(self, symbol):
        """Get current price ticker (internal implementation)"""
        try:
            # Format symbol for TradingView
            formatted_symbol = self._format_symbol_for_tv(symbol)
            exchange = self._extract_exchange(formatted_symbol)
            raw_symbol = self._parse_symbol_from_tv(formatted_symbol)
            
            # Initialize TA_Handler
            handler = TA_Handler(
                symbol=raw_symbol,
                exchange=exchange,
                screener="crypto",  # For cryptocurrencies
                interval=Interval.INTERVAL_1_MINUTE,
                timeout=10
            )
            
            # Get analysis which includes current price data
            analysis = handler.get_analysis()
            
            return {
                "symbol": symbol,
                "price": analysis.indicators["close"],
                "timestamp": datetime.datetime.now()
            }
        except Exception as e:
            st.warning(f"Error getting ticker from TradingView: {e}")
            return None
    
    def get_ticker(self, symbol):
        """Get current price ticker (cached wrapper)"""
        if symbol not in self.cache["ticker"] or self._cache_expired("ticker", symbol):
            self.cache["ticker"][symbol] = self._get_ticker_internal(symbol)
            self._update_cache_timestamp("ticker", symbol)
        
        return self.cache["ticker"][symbol]
    
    def _get_24h_stats_internal(self, symbol):
        """Get 24-hour statistics (internal implementation)"""
        try:
            # Format symbol for TradingView
            formatted_symbol = self._format_symbol_for_tv(symbol)
            exchange = self._extract_exchange(formatted_symbol)
            raw_symbol = self._parse_symbol_from_tv(formatted_symbol)
            
            # Initialize TA_Handler
            handler = TA_Handler(
                symbol=raw_symbol,
                exchange=exchange,
                screener="crypto",  # For cryptocurrencies
                interval=Interval.INTERVAL_1_DAY,  # Use daily interval for 24h stats
                timeout=10
            )
            
            # Get analysis which includes some 24h data
            analysis = handler.get_analysis()
            
            # Extract relevant data
            # Note: TradingView TA doesn't provide all the stats that Binance does
            # This is a simplified version
            return {
                "symbol": symbol,
                "price_change": analysis.indicators["change"],
                "price_change_percent": analysis.indicators["change_abs"],
                "volume": analysis.indicators["volume"],
                "quote_volume": analysis.indicators["volume"] * analysis.indicators["close"],
                "last_price": analysis.indicators["close"],
                "high": analysis.indicators["high"],
                "low": analysis.indicators["low"]
            }
        except Exception as e:
            st.warning(f"Error getting 24h stats from TradingView: {e}")
            return None
    
    def get_24h_stats(self, symbol):
        """Get 24-hour statistics (cached wrapper)"""
        if symbol not in self.cache["stats"] or self._cache_expired("stats", symbol):
            self.cache["stats"][symbol] = self._get_24h_stats_internal(symbol)
            self._update_cache_timestamp("stats", symbol)
        
        return self.cache["stats"][symbol]
    
    def get_current_price(self, symbol):
        """Get only the current price for a symbol (convenience wrapper)"""
        ticker = self.get_ticker(symbol)
        if ticker:
            return ticker["price"]
        return None