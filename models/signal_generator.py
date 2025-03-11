import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import streamlit as st
import joblib
import os
from utils.indicators import TechnicalIndicators

class SignalGenerator:
    def __init__(self):
        """Initialize the signal generator"""
        self.model = None
        
    def _prepare_features(self, df):
        """
        Prepare features for the model
        
        Parameters:
        - df: DataFrame with OHLCV data and indicators
        
        Returns:
        - DataFrame with features
        """
        if df.empty:
            return pd.DataFrame()
            
        # Create a copy to avoid modifying the original
        df_features = df.copy()
        
        # Basic features
        df_features['returns'] = df_features['close'].pct_change()
        df_features['log_returns'] = np.log(df_features['close'] / df_features['close'].shift(1))
        
        # Price relative to moving averages
        if 'ema9' in df_features.columns:
            df_features['close_over_ema9'] = df_features['close'] / df_features['ema9']
        if 'ema21' in df_features.columns:
            df_features['close_over_ema21'] = df_features['close'] / df_features['ema21']
        if 'ema50' in df_features.columns:
            df_features['close_over_ema50'] = df_features['close'] / df_features['ema50']
            
        # Volume features
        df_features['volume_change'] = df_features['volume'].pct_change()
        df_features['volume_ma5'] = df_features['volume'].rolling(5).mean()
        df_features['relative_volume'] = df_features['volume'] / df_features['volume_ma5']
        
        # Bollinger Band features
        if all(x in df_features.columns for x in ['bb_upper', 'bb_lower', 'bb_middle']):
            df_features['bb_width'] = (df_features['bb_upper'] - df_features['bb_lower']) / df_features['bb_middle']
            df_features['bb_position'] = (df_features['close'] - df_features['bb_lower']) / (df_features['bb_upper'] - df_features['bb_lower'])
        
        # RSI features
        if 'rsi' in df_features.columns:
            df_features['rsi_change'] = df_features['rsi'].diff()
            df_features['rsi_ma3'] = df_features['rsi'].rolling(3).mean()
        
        # MACD features
        if all(x in df_features.columns for x in ['macd', 'macd_signal']):
            df_features['macd_diff'] = df_features['macd'] - df_features['macd_signal']
            df_features['macd_diff_change'] = df_features['macd_diff'].diff()
        
        # Clean up
        df_features = df_features.dropna()
        
        return df_features
    
    def generate_signals(self, df, confidence_threshold=0.6):
        """
        Generate trading signals using technical indicators
        
        Parameters:
        - df: DataFrame with OHLCV data and indicators
        - confidence_threshold: Minimum confidence to generate a signal
        
        Returns:
        - DataFrame with signals
        """
        if df.empty:
            return pd.DataFrame()
            
        # Generate signals based on technical indicators
        signals = pd.DataFrame(index=df.index)
        signals['timestamp'] = df['timestamp']
        signals['price'] = df['close']
        signals['signal'] = 0  # 0 = no signal, 1 = buy, -1 = sell
        signals['confidence'] = 0.0
        signals['reason'] = ""
        
        # EMA crossover signals
        if 'ema9' in df.columns and 'ema21' in df.columns:
            # Buy signal: EMA9 crosses above EMA21
            ema_cross_up = (df['ema9'].shift(1) <= df['ema21'].shift(1)) & (df['ema9'] > df['ema21'])
            # Sell signal: EMA9 crosses below EMA21
            ema_cross_down = (df['ema9'].shift(1) >= df['ema21'].shift(1)) & (df['ema9'] < df['ema21'])
            
            # Set signals with base confidence
            buy_confidence = 0.6
            sell_confidence = 0.6
            
            # Add additional confidence if price is above/below longer-term EMAs
            if 'ema50' in df.columns:
                buy_confidence += np.where(df['close'] > df['ema50'], 0.1, 0)
                sell_confidence += np.where(df['close'] < df['ema50'], 0.1, 0)
            
            # Apply EMA crossover signals
            signals.loc[ema_cross_up, 'signal'] = 1
            signals.loc[ema_cross_up, 'confidence'] = buy_confidence
            signals.loc[ema_cross_up, 'reason'] = "EMA9 crossed above EMA21"
            
            signals.loc[ema_cross_down, 'signal'] = -1
            signals.loc[ema_cross_down, 'confidence'] = sell_confidence
            signals.loc[ema_cross_down, 'reason'] = "EMA9 crossed below EMA21"
        
        # RSI signals
        if 'rsi' in df.columns:
            # Buy signal: RSI crosses above 30 (oversold)
            rsi_buy = (df['rsi'].shift(1) <= 30) & (df['rsi'] > 30)
            # Sell signal: RSI crosses below 70 (overbought)
            rsi_sell = (df['rsi'].shift(1) >= 70) & (df['rsi'] < 70)
            
            # Apply RSI signals if they're more confident than existing ones
            signals.loc[rsi_buy & (signals['confidence'] < 0.65), 'signal'] = 1
            signals.loc[rsi_buy & (signals['confidence'] < 0.65), 'confidence'] = 0.65
            signals.loc[rsi_buy & (signals['confidence'] < 0.65), 'reason'] = "RSI crossed above 30 (oversold)"
            
            signals.loc[rsi_sell & (signals['confidence'] < 0.65), 'signal'] = -1
            signals.loc[rsi_sell & (signals['confidence'] < 0.65), 'confidence'] = 0.65
            signals.loc[rsi_sell & (signals['confidence'] < 0.65), 'reason'] = "RSI crossed below 70 (overbought)"
        
        # MACD signals
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            # Buy signal: MACD crosses above signal line
            macd_cross_up = (df['macd'].shift(1) <= df['macd_signal'].shift(1)) & (df['macd'] > df['macd_signal'])
            # Sell signal: MACD crosses below signal line
            macd_cross_down = (df['macd'].shift(1) >= df['macd_signal'].shift(1)) & (df['macd'] < df['macd_signal'])
            
            # Base confidence
            macd_confidence = 0.7
            
            # Apply MACD signals if they're more confident than existing ones
            signals.loc[macd_cross_up & (signals['confidence'] < macd_confidence), 'signal'] = 1
            signals.loc[macd_cross_up & (signals['confidence'] < macd_confidence), 'confidence'] = macd_confidence
            signals.loc[macd_cross_up & (signals['confidence'] < macd_confidence), 'reason'] = "MACD crossed above signal line"
            
            signals.loc[macd_cross_down & (signals['confidence'] < macd_confidence), 'signal'] = -1
            signals.loc[macd_cross_down & (signals['confidence'] < macd_confidence), 'confidence'] = macd_confidence
            signals.loc[macd_cross_down & (signals['confidence'] < macd_confidence), 'reason'] = "MACD crossed below signal line"
        
        # Bollinger Band signals
        if all(x in df.columns for x in ['bb_upper', 'bb_lower', 'bb_middle']):
            # Buy signal: Price crosses below lower band and then back above it
            bb_buy = (df['close'].shift(1) <= df['bb_lower'].shift(1)) & (df['close'] > df['bb_lower'])
            # Sell signal: Price crosses above upper band and then back below it
            bb_sell = (df['close'].shift(1) >= df['bb_upper'].shift(1)) & (df['close'] < df['bb_upper'])
            
            # Base confidence
            bb_confidence = 0.75
            
            # Apply BB signals if they're more confident than existing ones
            signals.loc[bb_buy & (signals['confidence'] < bb_confidence), 'signal'] = 1
            signals.loc[bb_buy & (signals['confidence'] < bb_confidence), 'confidence'] = bb_confidence
            signals.loc[bb_buy & (signals['confidence'] < bb_confidence), 'reason'] = "Price bounced from lower Bollinger Band"
            
            signals.loc[bb_sell & (signals['confidence'] < bb_confidence), 'signal'] = -1
            signals.loc[bb_sell & (signals['confidence'] < bb_confidence), 'confidence'] = bb_confidence
            signals.loc[bb_sell & (signals['confidence'] < bb_confidence), 'reason'] = "Price rejected from upper Bollinger Band"
        
        # Combine signals (if multiple indicators confirm, increase confidence)
        # This is a simplified approach - in a real system, would use ML model
        
        # Apply threshold
        signals.loc[signals['confidence'] < confidence_threshold, 'signal'] = 0
        signals.loc[signals['confidence'] < confidence_threshold, 'reason'] = ""
        
        # Get recent signals (last 10 candles)
        recent_signals = signals.iloc[-10:].copy()
        
        # Remove signals with zero confidence
        recent_signals = recent_signals[recent_signals['confidence'] >= confidence_threshold]
        
        return recent_signals
    
    def predict_price_levels(self, df, symbol, timeframe):
        """
        Predict optimal entry and exit price levels
        
        Parameters:
        - df: DataFrame with OHLCV data
        - symbol: Trading pair symbol
        - timeframe: Chart timeframe
        
        Returns:
        - Dictionary with entry and exit levels
        """
        if df.empty or len(df) < 20:
            return {
                'entry': None,
                'exit': None,
                'stop_loss': None
            }
        
        # Get latest price
        current_price = df['close'].iloc[-1]
        
        # Calculate recent volatility using ATR
        atr = TechnicalIndicators.ATR(df['high'], df['low'], df['close'], timeperiod=14).iloc[-1]
        
        # Calculate support and resistance levels
        levels = TechnicalIndicators.detect_support_resistance(df)
        
        # Calculate Fibonacci levels
        fib_levels = TechnicalIndicators.fibonacci_retracement(df)
        
        # Get recent signals
        signals = self.generate_signals(df)
        recent_buy_signals = signals[signals['signal'] == 1]
        recent_sell_signals = signals[signals['signal'] == -1]
        
        # Determine entry level
        entry_level = None
        exit_level = None
        stop_loss = None
        
        # If we have a recent buy signal, use that price as entry
        if not recent_buy_signals.empty:
            entry_level = recent_buy_signals.iloc[-1]['price']
            # Set exit at the next resistance level or a fixed percentage
            if 'resistance' in levels and levels['resistance']:
                # Find closest resistance above entry
                resistances_above = [r for r in levels['resistance'] if r > entry_level]
                if resistances_above:
                    exit_level = min(resistances_above)
                else:
                    exit_level = entry_level * 1.02  # 2% profit target
            else:
                exit_level = entry_level * 1.02  # 2% profit target
                
            # Set stop loss at the closest support level or using ATR
            if 'support' in levels and levels['support']:
                supports_below = [s for s in levels['support'] if s < entry_level]
                if supports_below:
                    stop_loss = max(supports_below)
                else:
                    stop_loss = entry_level - 2 * atr
            else:
                stop_loss = entry_level - 2 * atr
        
        # If we have a recent sell signal, use that price as entry for short
        elif not recent_sell_signals.empty:
            entry_level = recent_sell_signals.iloc[-1]['price']
            # Set exit at the next support level or a fixed percentage
            if 'support' in levels and levels['support']:
                # Find closest support below entry
                supports_below = [s for s in levels['support'] if s < entry_level]
                if supports_below:
                    exit_level = max(supports_below)
                else:
                    exit_level = entry_level * 0.98  # 2% profit target for short
            else:
                exit_level = entry_level * 0.98  # 2% profit target for short
                
            # Set stop loss at the closest resistance level or using ATR
            if 'resistance' in levels and levels['resistance']:
                resistances_above = [r for r in levels['resistance'] if r > entry_level]
                if resistances_above:
                    stop_loss = min(resistances_above)
                else:
                    stop_loss = entry_level + 2 * atr
            else:
                stop_loss = entry_level + 2 * atr
        
        # If no signal, predict based on current market conditions
        else:
            # Get the most recent price
            entry_level = current_price
            
            # Check if price is near a support or resistance level
            if 'support' in levels and levels['support']:
                nearest_support = min(levels['support'], key=lambda x: abs(x - current_price))
                if abs(nearest_support - current_price) / current_price < 0.01:  # Within 1%
                    # Price is near support, potential buy
                    entry_level = nearest_support
                    stop_loss = entry_level - 2 * atr
                    exit_level = entry_level + 3 * atr  # Risk:reward 1:1.5
            
            elif 'resistance' in levels and levels['resistance']:
                nearest_resistance = min(levels['resistance'], key=lambda x: abs(x - current_price))
                if abs(nearest_resistance - current_price) / current_price < 0.01:  # Within 1%
                    # Price is near resistance, potential sell
                    entry_level = nearest_resistance
                    stop_loss = entry_level + 2 * atr
                    exit_level = entry_level - 3 * atr  # Risk:reward 1:1.5
            
            # If no clear setup, use current price and ATR
            if stop_loss is None:
                # Default to ATR-based levels
                if df['close'].iloc[-1] > df['close'].iloc[-2]:  # Uptrend
                    entry_level = current_price
                    stop_loss = entry_level - 2 * atr
                    exit_level = entry_level + 2 * atr
                else:  # Downtrend
                    entry_level = current_price
                    stop_loss = entry_level + 2 * atr
                    exit_level = entry_level - 2 * atr
        
        # Calculate risk-reward ratio
        if entry_level and exit_level and stop_loss:
            risk = abs(entry_level - stop_loss)
            reward = abs(entry_level - exit_level)
            risk_reward = reward / risk if risk > 0 else 0
        else:
            risk_reward = 0
        
        return {
            'entry': round(entry_level, 8) if entry_level else None,
            'exit': round(exit_level, 8) if exit_level else None,
            'stop_loss': round(stop_loss, 8) if stop_loss else None,
            'risk_reward': round(risk_reward, 2),
            'confidence': self._calculate_setup_confidence(df, entry_level, exit_level, stop_loss)
        }
    
    def _calculate_setup_confidence(self, df, entry, exit, stop_loss):
        """Calculate confidence score for a trading setup"""
        if df.empty or entry is None or exit is None or stop_loss is None:
            return 0.0
            
        # Base confidence
        confidence = 0.5
        
        # Latest price
        current_price = df['close'].iloc[-1]
        
        # Check trend alignment
        if 'ema9' in df.columns and 'ema21' in df.columns:
            # Uptrend (EMA9 > EMA21)
            is_uptrend = df['ema9'].iloc[-1] > df['ema21'].iloc[-1]
            # Downtrend (EMA9 < EMA21)
            is_downtrend = df['ema9'].iloc[-1] < df['ema21'].iloc[-1]
            
            # For long position (entry < exit)
            if entry < exit and is_uptrend:
                confidence += 0.1
            # For short position (entry > exit)
            elif entry > exit and is_downtrend:
                confidence += 0.1
        
        # Check RSI conditions
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            
            # For long position
            if entry < exit:
                # Positive: RSI < 30 (oversold)
                if rsi < 30:
                    confidence += 0.1
                # Negative: RSI > 70 (overbought)
                elif rsi > 70:
                    confidence -= 0.1
            # For short position
            else:
                # Positive: RSI > 70 (overbought)
                if rsi > 70:
                    confidence += 0.1
                # Negative: RSI < 30 (oversold)
                elif rsi < 30:
                    confidence -= 0.1
        
        # Check MACD conditions
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            macd = df['macd'].iloc[-1]
            signal = df['macd_signal'].iloc[-1]
            
            # For long position
            if entry < exit:
                # Positive: MACD > Signal Line
                if macd > signal:
                    confidence += 0.1
                # Negative: MACD < Signal Line
                else:
                    confidence -= 0.1
            # For short position
            else:
                # Positive: MACD < Signal Line
                if macd < signal:
                    confidence += 0.1
                # Negative: MACD > Signal Line
                else:
                    confidence -= 0.1
        
        # Check Bollinger Band conditions
        if all(x in df.columns for x in ['bb_upper', 'bb_lower', 'bb_middle']):
            price = df['close'].iloc[-1]
            upper = df['bb_upper'].iloc[-1]
            lower = df['bb_lower'].iloc[-1]
            
            # For long position
            if entry < exit:
                # Positive: Price near or below lower band
                if price <= lower * 1.01:
                    confidence += 0.1
                # Negative: Price near or above upper band
                elif price >= upper * 0.99:
                    confidence -= 0.1
            # For short position
            else:
                # Positive: Price near or above upper band
                if price >= upper * 0.99:
                    confidence += 0.1
                # Negative: Price near or below lower band
                elif price <= lower * 1.01:
                    confidence -= 0.1
        
        # Calculate risk-reward ratio factor
        risk = abs(entry - stop_loss)
        reward = abs(entry - exit)
        if risk > 0:
            risk_reward = reward / risk
            # Favor setups with good risk-reward
            if risk_reward >= 2.0:
                confidence += 0.1
            elif risk_reward >= 1.5:
                confidence += 0.05
            elif risk_reward < 1.0:
                confidence -= 0.1
        
        # Ensure confidence is between 0 and 1
        confidence = max(0.0, min(1.0, confidence))
        
        return round(confidence, 2)
