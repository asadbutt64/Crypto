import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import streamlit as st
from utils.indicators import TechnicalIndicators

class ChartUtils:
    @staticmethod
    def create_price_chart(df, indicators, symbol, timeframe):
        """
        Create an interactive price chart with indicators
        
        Parameters:
        - df: DataFrame with OHLCV data and indicators
        - indicators: Dictionary of indicators to display
        - symbol: Trading pair symbol
        - timeframe: Chart timeframe
        
        Returns:
        - Plotly figure
        """
        if df.empty:
            # Return empty placeholder chart
            fig = go.Figure()
            fig.add_annotation(
                text="No data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=20, color="white")
            )
            return fig
        
        # Create figure with secondary y-axis
        fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.7, 0.3],
            subplot_titles=(f"{symbol} - {timeframe}", "Volume & MACD")
        )
        
        # Add candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=df['timestamp'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='Price',
                increasing_line_color='#26A69A', 
                decreasing_line_color='#EF5350'
            ),
            row=1, col=1
        )
        
        # Add EMAs
        ema_colors = {
            'ema9': '#E91E63',  # Pink
            'ema21': '#FFC107',  # Amber
            'ema50': '#03A9F4',  # Light Blue
            'ema200': '#9C27B0'  # Purple
        }
        
        for ema, color in ema_colors.items():
            if ema in df.columns and indicators.get(f"EMA {ema.replace('ema', '')}", False):
                fig.add_trace(
                    go.Scatter(
                        x=df['timestamp'],
                        y=df[ema],
                        mode='lines',
                        line=dict(width=1.5, color=color),
                        name=f"{ema.upper()}"
                    ),
                    row=1, col=1
                )
        
        # Add Bollinger Bands
        if 'bb_upper' in df.columns and 'bb_lower' in df.columns and 'bb_middle' in df.columns and indicators.get("Bollinger Bands", False):
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['bb_upper'],
                    mode='lines',
                    line=dict(width=1, color='rgba(173, 216, 230, 0.7)'),
                    name='BB Upper'
                ),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['bb_middle'],
                    mode='lines',
                    line=dict(width=1, color='rgba(173, 216, 230, 0.7)'),
                    name='BB Middle'
                ),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['bb_lower'],
                    mode='lines',
                    line=dict(width=1, color='rgba(173, 216, 230, 0.7)'),
                    fill='tonexty',
                    fillcolor='rgba(173, 216, 230, 0.1)',
                    name='BB Lower'
                ),
                row=1, col=1
            )
        
        # Add volume bars
        colors = [
            'red' if df['open'].iloc[i] > df['close'].iloc[i] else 'green' 
            for i in range(len(df))
        ]
        
        fig.add_trace(
            go.Bar(
                x=df['timestamp'],
                y=df['volume'],
                name='Volume',
                marker_color=colors,
                marker_line_width=0,
                opacity=0.7
            ),
            row=2, col=1
        )
        
        # Add MACD if available
        if 'macd' in df.columns and 'macd_signal' in df.columns and 'macd_hist' in df.columns and indicators.get("MACD", False):
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['macd'],
                    mode='lines',
                    line=dict(width=1.5, color='#2962FF'),
                    name='MACD'
                ),
                row=2, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['macd_signal'],
                    mode='lines',
                    line=dict(width=1.5, color='#FF6D00'),
                    name='Signal'
                ),
                row=2, col=1
            )
            
            # Add histogram
            colors = ['#EF5350' if val < 0 else '#26A69A' for val in df['macd_hist']]
            fig.add_trace(
                go.Bar(
                    x=df['timestamp'],
                    y=df['macd_hist'],
                    name='Histogram',
                    marker_color=colors,
                    marker_line_width=0,
                ),
                row=2, col=1
            )
        
        # Add RSI if requested
        if 'rsi' in df.columns and indicators.get("RSI", False):
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['rsi'],
                    mode='lines',
                    line=dict(width=1.5, color='#FF9800'),
                    name='RSI'
                ),
                row=2, col=1
            )
            
            # Add RSI reference lines at 30 and 70
            fig.add_shape(
                type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1],
                y0=30, y1=30, line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dash"),
                row=2, col=1
            )
            
            fig.add_shape(
                type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1],
                y0=70, y1=70, line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dash"),
                row=2, col=1
            )

        # Update layout for dark theme and better UX
        fig.update_layout(
            template='plotly_dark',
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=10)
            ),
            height=600,
            xaxis_rangeslider_visible=False,
            hovermode='x unified'
        )
        
        # Remove gridlines from x-axis 
        fig.update_xaxes(
            showgrid=False,
            zeroline=False,
            rangeslider_visible=False
        )
        
        # Update y-axes
        fig.update_yaxes(
            showgrid=True,
            zeroline=False,
            gridcolor='rgba(255,255,255,0.1)',
            row=1, col=1
        )
        
        fig.update_yaxes(
            showgrid=True,
            zeroline=False,
            gridcolor='rgba(255,255,255,0.1)',
            row=2, col=1
        )
        
        return fig
    
    @staticmethod
    def create_rsi_chart(df, timeperiods=[14]):
        """Create a separate RSI chart"""
        if df.empty or 'close' not in df.columns:
            # Return empty placeholder chart
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for RSI",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="white")
            )
            return fig
        
        fig = go.Figure()
        
        # Calculate RSI for each timeperiod
        colors = ['#FF9800', '#03A9F4', '#4CAF50']
        
        for i, period in enumerate(timeperiods):
            if i < len(colors):
                color = colors[i]
            else:
                color = colors[i % len(colors)]
                
            rsi = TechnicalIndicators.RSI(df['close'], timeperiod=period)
            
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=rsi,
                    mode='lines',
                    line=dict(width=1.5, color=color),
                    name=f'RSI ({period})'
                )
            )
        
        # Add reference lines at 30 and 70
        fig.add_shape(
            type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1],
            y0=30, y1=30, line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dash")
        )
        
        fig.add_shape(
            type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1],
            y0=50, y1=50, line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dash")
        )
        
        fig.add_shape(
            type="line", x0=df['timestamp'].iloc[0], x1=df['timestamp'].iloc[-1],
            y0=70, y1=70, line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dash")
        )
        
        # Update layout
        fig.update_layout(
            template='plotly_dark',
            plot_bgcolor='#121212',
            paper_bgcolor='#121212',
            title='RSI Indicator',
            yaxis_title='RSI Value',
            xaxis_title='Time',
            height=250,
            margin=dict(l=0, r=0, t=30, b=0),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode='x unified'
        )
        
        # Set y-axis range
        fig.update_yaxes(range=[0, 100])
        
        # Remove gridlines from x-axis
        fig.update_xaxes(
            showgrid=False,
            zeroline=False
        )
        
        return fig
