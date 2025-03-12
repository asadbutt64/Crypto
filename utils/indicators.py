import pandas as pd
import numpy as np
import streamlit as st

class TechnicalIndicators:
    @staticmethod
    def EMA(series, timeperiod=14):
        """Calculate Exponential Moving Average"""
        return series.ewm(span=timeperiod, adjust=False).mean()
    
    @staticmethod
    def SMA(series, timeperiod=14):
        """Calculate Simple Moving Average"""
        return series.rolling(window=timeperiod).mean()
    
    @staticmethod
    def BBANDS(series, timeperiod=20, nbdevup=2, nbdevdn=2):
        """Calculate Bollinger Bands"""
        middle = TechnicalIndicators.SMA(series, timeperiod)
        std_dev = series.rolling(window=timeperiod).std()
        upper = middle + (std_dev * nbdevup)
        lower = middle - (std_dev * nbdevdn)
        return upper, middle, lower
    
    @staticmethod
    def RSI(series, timeperiod=14):
        """Calculate Relative Strength Index"""
        delta = series.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=timeperiod).mean()
        avg_loss = loss.rolling(window=timeperiod).mean()
        
        # For subsequent calculations
        for i in range(timeperiod, len(series)):
            avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (timeperiod-1) + gain.iloc[i]) / timeperiod
            avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (timeperiod-1) + loss.iloc[i]) / timeperiod
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def MACD(series, fastperiod=12, slowperiod=26, signalperiod=9):
        """Calculate MACD (Moving Average Convergence/Divergence)"""
        fast_ema = TechnicalIndicators.EMA(series, fastperiod)
        slow_ema = TechnicalIndicators.EMA(series, slowperiod)
        macd_line = fast_ema - slow_ema
        signal_line = TechnicalIndicators.EMA(macd_line, signalperiod)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def ATR(high, low, close, timeperiod=14):
        """Calculate Average True Range"""
        high = high.values
        low = low.values
        close = close.values
        
        # Calculate True Range
        tr1 = high[1:] - low[1:]
        tr2 = abs(high[1:] - close[:-1])
        tr3 = abs(low[1:] - close[:-1])
        
        # Use the max of the 3 true range calculations
        tr = pd.Series(np.zeros(len(high)))
        for i in range(1, len(high)):
            tr.iloc[i] = max(tr1[i-1], tr2[i-1], tr3[i-1])
        
        # Calculate ATR using simple moving average
        atr = tr.rolling(window=timeperiod).mean()
        return atr
    
    @staticmethod
    def ADX(high, low, close, timeperiod=14):
        """Calculate Average Directional Index"""
        # Calculate +DM and -DM
        high_diff = high.diff()
        low_diff = low.diff().multiply(-1)
        
        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
        
        # Use ATR calculation
        atr = TechnicalIndicators.ATR(high, low, close, timeperiod)
        
        # Calculate +DI and -DI
        plus_di = 100 * TechnicalIndicators.EMA(plus_dm, timeperiod) / atr
        minus_di = 100 * TechnicalIndicators.EMA(minus_dm, timeperiod) / atr
        
        # Calculate DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = TechnicalIndicators.EMA(dx, timeperiod)
        
        return adx
        
    @staticmethod
    def add_indicators(df, indicators=None):
        """
        Add technical indicators to the dataframe
        
        Parameters:
        - df: DataFrame with OHLCV data
        - indicators: Dictionary of indicators to add
        
        Returns:
        - DataFrame with indicators added
        """
        if df.empty:
            return df
            
        # Create a copy to avoid modifying the original
        df_with_indicators = df.copy()
        
        # Default indicators if none specified
        if indicators is None:
            indicators = {
                "EMA 9": True,
                "EMA 21": True,
                "EMA 50": True,
                "EMA 200": True,
                "Bollinger Bands": True,
                "RSI": True,
                "MACD": True,
                "Volume": True
            }
        
        # Calculate EMAs
        if indicators.get("EMA 9", False):
            df_with_indicators['ema9'] = TechnicalIndicators.EMA(df_with_indicators['close'], timeperiod=9)
        
        if indicators.get("EMA 21", False):
            df_with_indicators['ema21'] = TechnicalIndicators.EMA(df_with_indicators['close'], timeperiod=21)
        
        if indicators.get("EMA 50", False):
            df_with_indicators['ema50'] = TechnicalIndicators.EMA(df_with_indicators['close'], timeperiod=50)
        
        if indicators.get("EMA 200", False):
            df_with_indicators['ema200'] = TechnicalIndicators.EMA(df_with_indicators['close'], timeperiod=200)
        
        # Calculate Bollinger Bands
        if indicators.get("Bollinger Bands", False):
            df_with_indicators['bb_upper'], df_with_indicators['bb_middle'], df_with_indicators['bb_lower'] = TechnicalIndicators.BBANDS(
                df_with_indicators['close'], 
                timeperiod=20, 
                nbdevup=2, 
                nbdevdn=2
            )
        
        # Calculate RSI
        if indicators.get("RSI", False):
            df_with_indicators['rsi'] = TechnicalIndicators.RSI(df_with_indicators['close'], timeperiod=14)
        
        # Calculate MACD
        if indicators.get("MACD", False):
            df_with_indicators['macd'], df_with_indicators['macd_signal'], df_with_indicators['macd_hist'] = TechnicalIndicators.MACD(
                df_with_indicators['close'], 
                fastperiod=12, 
                slowperiod=26, 
                signalperiod=9
            )
        
        # Calculate ATR
        if indicators.get("ATR", False):
            df_with_indicators['atr'] = TechnicalIndicators.ATR(
                df_with_indicators['high'], 
                df_with_indicators['low'], 
                df_with_indicators['close'], 
                timeperiod=14
            )
        
        # Calculate ADX
        if indicators.get("ADX", False):
            df_with_indicators['adx'] = TechnicalIndicators.ADX(
                df_with_indicators['high'], 
                df_with_indicators['low'], 
                df_with_indicators['close'], 
                timeperiod=14
            )

        # Calculate VWAP (simplified implementation for daily data)
        if indicators.get("VWAP", False):
            df_with_indicators['vwap'] = TechnicalIndicators.calculate_vwap(df_with_indicators)
            
        return df_with_indicators
    
    @staticmethod
    def calculate_vwap(df):
        """Calculate VWAP (Volume Weighted Average Price)"""
        df = df.copy()
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['price_volume'] = df['typical_price'] * df['volume']
        df['cumulative_price_volume'] = df['price_volume'].cumsum()
        df['cumulative_volume'] = df['volume'].cumsum()
        vwap = df['cumulative_price_volume'] / df['cumulative_volume']
        return vwap
        
    @staticmethod
    def detect_support_resistance(df, window=5):
        """Detect support and resistance levels"""
        if df.empty or len(df) < window*2:
            return {}
            
        try:
            # Find local minima and maxima
            df = df.copy()
            df['min'] = df['low'].rolling(window=window, center=True).min()
            df['max'] = df['high'].rolling(window=window, center=True).max()
            
            support_levels = []
            resistance_levels = []
            
            # Identify support levels (local minima)
            for i in range(window, len(df)-window):
                if df['low'].iloc[i] == df['min'].iloc[i] and df['low'].iloc[i] < df['low'].iloc[i-1] and df['low'].iloc[i] < df['low'].iloc[i+1]:
                    support_levels.append((df.index[i], df['low'].iloc[i]))
            
            # Identify resistance levels (local maxima)
            for i in range(window, len(df)-window):
                if df['high'].iloc[i] == df['max'].iloc[i] and df['high'].iloc[i] > df['high'].iloc[i-1] and df['high'].iloc[i] > df['high'].iloc[i+1]:
                    resistance_levels.append((df.index[i], df['high'].iloc[i]))
            
            # Cluster similar levels
            def cluster_levels(levels, threshold_pct=0.005):
                if not levels:
                    return []
                    
                try:
                    clustered = []
                    levels.sort(key=lambda x: x[1])
                    current_cluster = [levels[0]]
                    
                    for i in range(1, len(levels)):
                        current_level = levels[i][1]
                        prev_level = current_cluster[-1][1]
                        
                        # If current level is within threshold% of previous level, add to cluster
                        if abs(current_level - prev_level) / prev_level < threshold_pct:
                            current_cluster.append(levels[i])
                        else:
                            # Calculate average of cluster
                            avg_time = sum(l[0].timestamp() for l in current_cluster) / len(current_cluster)
                            avg_price = sum(l[1] for l in current_cluster) / len(current_cluster)
                            clustered.append((pd.Timestamp(avg_time, unit='s'), avg_price))
                            
                            # Start new cluster
                            current_cluster = [levels[i]]
                    
                    # Add last cluster
                    if current_cluster:
                        avg_time = sum(l[0].timestamp() for l in current_cluster) / len(current_cluster)
                        avg_price = sum(l[1] for l in current_cluster) / len(current_cluster)
                        clustered.append((pd.Timestamp(avg_time, unit='s'), avg_price))
                        
                    return clustered
                except Exception as e:
                    # In case of any error in clustering, just return empty array
                    return []
            
            clustered_support = cluster_levels(support_levels)
            clustered_resistance = cluster_levels(resistance_levels)
            
            # Safely get recent levels (up to 3 each)
            recent_support = sorted(clustered_support, key=lambda x: x[0], reverse=True)[:3] if clustered_support else []
            recent_resistance = sorted(clustered_resistance, key=lambda x: x[0], reverse=True)[:3] if clustered_resistance else []
            
            return {
                'support': [level[1] for level in recent_support],
                'resistance': [level[1] for level in recent_resistance]
            }
        except Exception as e:
            # Return empty dictionary in case of any exception
            return {}
    
    @staticmethod
    def fibonacci_retracement(df, period=20):
        """Calculate Fibonacci retracement levels for recent swing high/low"""
        if df.empty or len(df) < period:
            return {}
            
        # Get recent period
        recent_data = df.iloc[-period:]
        
        # Find swing high and swing low
        swing_high = recent_data['high'].max()
        swing_low = recent_data['low'].min()
        
        # Calculate retracement levels
        diff = swing_high - swing_low
        
        levels = {
            '0.0': swing_low,
            '0.236': swing_low + 0.236 * diff,
            '0.382': swing_low + 0.382 * diff,
            '0.5': swing_low + 0.5 * diff,
            '0.618': swing_low + 0.618 * diff,
            '0.786': swing_low + 0.786 * diff,
            '1.0': swing_high
        }
        
        return levels
