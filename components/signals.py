import streamlit as st
import pandas as pd
import numpy as np
from models.signal_generator import SignalGenerator
from utils.indicators import TechnicalIndicators
import time
import datetime
from database import db_manager

def render_trade_signals(df, symbol, timeframe):
    """Render the trade signals component"""
    if df.empty:
        st.warning("No data available for generating signals.")
        return

    # Create signal generator
    signal_generator = SignalGenerator()
    
    # Get recent signals from model
    signals = signal_generator.generate_signals(df)
    
    # Save new signals to database if there are any
    if not signals.empty:
        try:
            for i, signal in signals.iterrows():
                # Prepare signal data for database
                signal_data = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'timestamp': signal['timestamp'],
                    'signal_type': 'buy' if signal['signal'] == 1 else 'sell' if signal['signal'] == -1 else 'neutral',
                    'price': float(signal['price']),
                    'confidence': float(signal['confidence']),
                    'entry_price': float(signal['price']),
                    'stop_loss': None,  # These would be filled in from price_levels after prediction
                    'take_profit': None,
                    'indicators': {
                        'macd': signal.get('macd', None),
                        'rsi': signal.get('rsi', None),
                        'ema_cross': signal.get('ema_cross', None)
                    } if 'macd' in signal or 'rsi' in signal or 'ema_cross' in signal else None,
                    'notes': signal['reason']
                }
                
                # Save to database
                db_manager.save_trading_signal(signal_data)
        except Exception as e:
            st.error(f"Error saving signals to database: {e}")
    
    # Try to get existing signals from database
    try:
        db_signals = db_manager.get_trading_signals(symbol, timeframe, limit=10)
        if not db_signals.empty:
            # Combine with model-generated signals
            # This could be enhanced to avoid duplicates, etc.
            if not signals.empty:
                # We could do a more complex comparison here to avoid duplication
                pass
            else:
                # If no new signals were generated, use database signals
                # (need to convert to same format as model-generated signals)
                signals_list = []
                for _, row in db_signals.iterrows():
                    signals_list.append({
                        'timestamp': row['timestamp'],
                        'signal': 1 if row['signal_type'] == 'buy' else -1 if row['signal_type'] == 'sell' else 0,
                        'price': row['price'],
                        'confidence': row['confidence'],
                        'reason': row['notes'] or 'Historical signal from database'
                    })
                if signals_list:
                    signals = pd.DataFrame(signals_list)
    except Exception as e:
        st.warning(f"Couldn't retrieve signals from database: {e}")
    
    # Predict price levels
    price_levels = signal_generator.predict_price_levels(df, symbol, timeframe)
    
    # If we have price levels and signals, update the stop loss and take profit in the database
    if price_levels['entry'] is not None and not signals.empty:
        try:
            # Get the most recent signal from the database
            recent_signals = db_manager.get_trading_signals(symbol, timeframe, limit=1)
            if not recent_signals.empty:
                signal_id = recent_signals.iloc[0]['id']
                
                # Update the signal with price levels
                session = db_manager.get_session()
                try:
                    signal = session.query(db_manager.TradingSignal).filter_by(id=signal_id).first()
                    if signal:
                        signal.stop_loss = float(price_levels['stop_loss'])
                        signal.take_profit = float(price_levels['exit'])
                        session.commit()
                except Exception as e:
                    session.rollback()
                    st.warning(f"Could not update price levels in database: {e}")
                finally:
                    session.close()
        except Exception as e:
            st.warning(f"Error updating price levels: {e}")
    
    # Get latest price
    current_price = df['close'].iloc[-1]
    
    # Prepare confidence color
    def get_confidence_color(conf):
        if conf >= 0.75:
            return "green"
        elif conf >= 0.6:
            return "orange"
        else:
            return "red"
    
    # Display current price and 24h stats
    st.subheader("Market Overview")
    
    # Create columns for metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Current Price",
            f"${current_price:.4f}",
            delta=f"{(df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100:.2f}%",
            delta_color="normal" if df['close'].iloc[-1] >= df['close'].iloc[-2] else "inverse"
        )
    
    # Get 24h stats if available
    try:
        stats_24h = st.session_state.api_client.get_24h_stats(symbol)
        with col2:
            if stats_24h:
                st.metric(
                    "24h Change",
                    f"{stats_24h['price_change_percent']}%",
                    delta=f"${stats_24h['price_change']:.4f}",
                    delta_color="normal" if stats_24h['price_change'] >= 0 else "inverse"
                )
            else:
                st.metric("24h Change", "N/A", "")
        
        with col3:
            if stats_24h:
                st.metric(
                    "24h Volume",
                    f"${stats_24h['quote_volume']:,.0f}",
                    ""
                )
            else:
                st.metric("24h Volume", "N/A", "")
    except:
        with col2:
            st.metric("24h Change", "N/A", "")
        with col3:
            st.metric("24h Volume", "N/A", "")
    
    # Display price levels
    st.subheader("AI-Powered Trading Signals")
    
    # Create columns for trading signals
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Price Levels")
        
        if price_levels['entry'] is not None:
            # Determine if long or short position
            is_long = price_levels['entry'] < price_levels['exit']
            position_type = "LONG 📈" if is_long else "SHORT 📉"
            
            # Display trade type with confidence score
            st.markdown(f"#### {position_type} - Confidence: {price_levels['confidence'] * 100:.0f}%")
            
            # Create a table with price levels
            data = pd.DataFrame({
                "Level": ["Entry", "Take Profit", "Stop Loss"],
                "Price": [
                    f"${price_levels['entry']:.4f}",
                    f"${price_levels['exit']:.4f}",
                    f"${price_levels['stop_loss']:.4f}"
                ],
                "Distance": [
                    "Current Price",
                    f"{abs(price_levels['exit'] - price_levels['entry']) / price_levels['entry'] * 100:.2f}%",
                    f"{abs(price_levels['stop_loss'] - price_levels['entry']) / price_levels['entry'] * 100:.2f}%"
                ]
            })
            
            # Display the table
            st.table(data)
            
            # Display risk-reward ratio
            st.markdown(f"**Risk-Reward Ratio**: {price_levels['risk_reward']}:1")
        else:
            st.info("No clear trading setup available at this time.")
            st.markdown("Check back after more price action develops.")
    
    with col2:
        st.markdown("### Recent Signals")
        
        if signals.empty:
            st.info("No signals generated in the recent candles.")
            st.markdown("The system is waiting for clearer market conditions.")
        else:
            # Display recent signals
            for i, signal in signals.iterrows():
                # Format signal data
                signal_type = "BUY 🟢" if signal['signal'] == 1 else "SELL 🔴" if signal['signal'] == -1 else "NEUTRAL ⚪"
                signal_price = f"${signal['price']:.4f}"
                signal_time = signal['timestamp'].strftime("%Y-%m-%d %H:%M")
                signal_confidence = f"{signal['confidence'] * 100:.0f}%"
                signal_reason = signal['reason']
                
                # Create signal card
                with st.container():
                    st.markdown(f"**{signal_type}** - {signal_time}")
                    st.markdown(f"Price: {signal_price} | Confidence: {signal_confidence}")
                    st.markdown(f"*{signal_reason}*")
                    st.markdown("---")
    
    # Add market insights from technical indicators
    st.subheader("Market Insights")
    
    # Detect support and resistance levels
    levels = TechnicalIndicators.detect_support_resistance(df)
    
    # Calculate Fibonacci retracement levels
    fib_levels = TechnicalIndicators.fibonacci_retracement(df)
    
    # Create columns for insights
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Support & Resistance")
        
        if levels and 'support' in levels and levels['support']:
            supports = [f"${level:.4f}" for level in levels['support']]
            st.markdown(f"**Support Levels**: {', '.join(supports)}")
        else:
            st.markdown("**Support Levels**: No clear levels detected")
        
        if levels and 'resistance' in levels and levels['resistance']:
            resistances = [f"${level:.4f}" for level in levels['resistance']]
            st.markdown(f"**Resistance Levels**: {', '.join(resistances)}")
        else:
            st.markdown("**Resistance Levels**: No clear levels detected")
    
    with col2:
        st.markdown("### Fibonacci Retracement")
        
        if fib_levels:
            for level, price in fib_levels.items():
                st.markdown(f"**{level}**: ${price:.4f}")
        else:
            st.markdown("Fibonacci levels could not be calculated with current data.")
    
    # Display trend analysis
    st.subheader("Trend Analysis")
    
    # Check if indicators are available
    has_ema = 'ema9' in df.columns and 'ema21' in df.columns
    has_macd = 'macd' in df.columns and 'macd_signal' in df.columns
    has_rsi = 'rsi' in df.columns
    
    # Create columns for trend metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if has_ema:
            # EMA trend
            ema_trend = "Bullish" if df['ema9'].iloc[-1] > df['ema21'].iloc[-1] else "Bearish"
            ema_color = "green" if ema_trend == "Bullish" else "red"
            
            st.markdown(f"### EMA Trend")
            st.markdown(f"<h4 style='color: {ema_color};'>{ema_trend}</h4>", unsafe_allow_html=True)
            
            ema_cross = "No recent crossover"
            if df['ema9'].iloc[-2] <= df['ema21'].iloc[-2] and df['ema9'].iloc[-1] > df['ema21'].iloc[-1]:
                ema_cross = "Bullish crossover (EMA9 crossed above EMA21)"
            elif df['ema9'].iloc[-2] >= df['ema21'].iloc[-2] and df['ema9'].iloc[-1] < df['ema21'].iloc[-1]:
                ema_cross = "Bearish crossover (EMA9 crossed below EMA21)"
            
            st.markdown(f"*{ema_cross}*")
        else:
            st.markdown("### EMA Trend")
            st.markdown("*Enable EMA indicators to see trend analysis*")
    
    with col2:
        if has_macd:
            # MACD trend
            macd_trend = "Bullish" if df['macd'].iloc[-1] > df['macd_signal'].iloc[-1] else "Bearish"
            macd_color = "green" if macd_trend == "Bullish" else "red"
            
            st.markdown(f"### MACD")
            st.markdown(f"<h4 style='color: {macd_color};'>{macd_trend}</h4>", unsafe_allow_html=True)
            
            macd_cross = "No recent crossover"
            if df['macd'].iloc[-2] <= df['macd_signal'].iloc[-2] and df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]:
                macd_cross = "Bullish crossover (MACD crossed above Signal)"
            elif df['macd'].iloc[-2] >= df['macd_signal'].iloc[-2] and df['macd'].iloc[-1] < df['macd_signal'].iloc[-1]:
                macd_cross = "Bearish crossover (MACD crossed below Signal)"
            
            st.markdown(f"*{macd_cross}*")
        else:
            st.markdown("### MACD")
            st.markdown("*Enable MACD indicator to see trend analysis*")
    
    with col3:
        if has_rsi:
            # RSI condition
            rsi_value = df['rsi'].iloc[-1]
            
            if rsi_value >= 70:
                rsi_condition = "Overbought"
                rsi_color = "red"
            elif rsi_value <= 30:
                rsi_condition = "Oversold"
                rsi_color = "green"
            else:
                rsi_condition = "Neutral"
                rsi_color = "white"
            
            st.markdown(f"### RSI")
            st.markdown(f"<h4 style='color: {rsi_color};'>{rsi_condition} ({rsi_value:.1f})</h4>", unsafe_allow_html=True)
            
            # RSI trend
            rsi_trend = "Increasing" if df['rsi'].iloc[-1] > df['rsi'].iloc[-2] else "Decreasing"
            
            st.markdown(f"*RSI is {rsi_trend}*")
        else:
            st.markdown("### RSI")
            st.markdown("*Enable RSI indicator to see trend analysis*")
    
    # Add last updated timestamp
    st.markdown("---")
    st.markdown(f"*Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}*")
