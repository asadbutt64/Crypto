import streamlit as st
import pandas as pd
import numpy as np
from utils.chart_utils import ChartUtils
from utils.indicators import TechnicalIndicators
import plotly.graph_objects as go

def render_price_chart(df, indicators, symbol, timeframe):
    """Render the price chart component"""
    if df.empty:
        st.error("No data available for the selected cryptocurrency. Please try another pair or check your connection.")
        return

    # Calculate indicators
    df_with_indicators = TechnicalIndicators.add_indicators(df, indicators)
    
    # Create the chart
    fig = ChartUtils.create_price_chart(df_with_indicators, indicators, symbol, timeframe)
    
    # Display the chart
    st.plotly_chart(fig, use_container_width=True)
    
    # Return processed dataframe for other components
    return df_with_indicators

def render_indicator_charts(df, indicators):
    """Render separate charts for individual indicators"""
    if df.empty:
        return
    
    # Determine which indicator charts to display
    show_rsi = indicators.get("RSI", False)
    
    # Create columns for indicator charts
    if show_rsi:
        st.subheader("RSI Analysis")
        rsi_fig = go.Figure()
        
        # Add RSI line
        rsi_fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['rsi'],
                mode='lines',
                line=dict(width=1.5, color='#FF9800'),
                name='RSI (14)'
            )
        )
        
        # Add reference lines at 30, 50, and 70
        rsi_fig.add_shape(
            type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1],
            y0=30, y1=30, line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dash")
        )
        
        rsi_fig.add_shape(
            type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1],
            y0=50, y1=50, line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dash")
        )
        
        rsi_fig.add_shape(
            type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1],
            y0=70, y1=70, line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dash")
        )
        
        # Update layout
        rsi_fig.update_layout(
            template='plotly_dark',
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            yaxis_title='RSI Value',
            xaxis_title='Time',
            height=200,
            margin=dict(l=0, r=0, t=5, b=0),
            showlegend=False,
            hovermode='x unified'
        )
        
        # Set y-axis range
        rsi_fig.update_yaxes(range=[0, 100])
        
        # Remove gridlines from x-axis
        rsi_fig.update_xaxes(
            showgrid=False,
            zeroline=False
        )
        
        st.plotly_chart(rsi_fig, use_container_width=True)
        
        # Add RSI explanation
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Overbought (>70)", f"{df['rsi'].iloc[-1]:.1f}", 
                      delta="↑" if df['rsi'].iloc[-1] > 70 else None,
                      delta_color="inverse")
        with col2:
            st.metric("Neutral (30-70)", f"{df['rsi'].iloc[-1]:.1f}",
                     delta="—" if 30 <= df['rsi'].iloc[-1] <= 70 else None)
        with col3:
            st.metric("Oversold (<30)", f"{df['rsi'].iloc[-1]:.1f}",
                     delta="↓" if df['rsi'].iloc[-1] < 30 else None,
                     delta_color="inverse")
