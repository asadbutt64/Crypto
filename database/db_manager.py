import os
import sqlalchemy as sa
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
import streamlit as st
import pandas as pd

# Create a base class for declarative models
Base = declarative_base()

# Define models
class PriceData(Base):
    """Model for storing historical price data"""
    __tablename__ = 'price_data'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), index=True, nullable=False)
    timeframe = Column(String(10), index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Composite index on symbol, timeframe, timestamp for faster lookups
    __table_args__ = (
        sa.UniqueConstraint('symbol', 'timeframe', 'timestamp', name='unique_price_point'),
    )

class TradingSignal(Base):
    """Model for storing generated trading signals"""
    __tablename__ = 'trading_signals'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), index=True, nullable=False)
    timeframe = Column(String(10), index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    signal_type = Column(String(10), nullable=False)  # 'buy', 'sell', 'neutral'
    price = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    entry_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    indicators = Column(JSON, nullable=True)  # Store indicator values as JSON
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    closed = Column(Boolean, default=False)
    closed_at = Column(DateTime, nullable=True)
    profit_loss = Column(Float, nullable=True)  # In percentage

class BacktestResult(Base):
    """Model for storing backtesting results"""
    __tablename__ = 'backtest_results'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    symbol = Column(String(20), index=True, nullable=False)
    timeframe = Column(String(10), index=True, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    parameters = Column(JSON, nullable=False)  # Strategy parameters
    total_trades = Column(Integer, nullable=False)
    win_rate = Column(Float, nullable=False)
    profit_loss = Column(Float, nullable=False)  # Total P&L in percentage
    max_drawdown = Column(Float, nullable=False)
    sharpe_ratio = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    notes = Column(Text, nullable=True)

class DBManager:
    """Database connection and operations manager"""
    
    def __init__(self):
        """Initialize the database connection"""
        self.setup_connection()
        
    def setup_connection(self):
        """Set up database connection using environment variables"""
        self.database_url = os.environ.get('DATABASE_URL')
        if not self.database_url:
            # Construct from individual components if DATABASE_URL not set
            db_user = os.environ.get('PGUSER')
            db_password = os.environ.get('PGPASSWORD')
            db_host = os.environ.get('PGHOST')
            db_port = os.environ.get('PGPORT')
            db_name = os.environ.get('PGDATABASE')
            
            if all([db_user, db_password, db_host, db_port, db_name]):
                self.database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            else:
                raise ValueError("Database connection information missing from environment variables")
        
        # Create engine and initialize tables
        self.engine = create_engine(self.database_url)
        self.create_tables()
        
        # Create a session factory
        self.Session = sessionmaker(bind=self.engine)
    
    def create_tables(self):
        """Create all defined tables if they don't exist"""
        Base.metadata.create_all(self.engine)
    
    def get_session(self):
        """Get a new database session"""
        return self.Session()
    
    # Price data operations
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def get_price_data(_self, symbol, timeframe, limit=500):
        """
        Get historical price data from database
        
        Parameters:
        - symbol: Trading pair symbol
        - timeframe: Chart timeframe
        - limit: Maximum number of records to return
        
        Returns:
        - DataFrame with OHLCV data
        """
        session = _self.get_session()
        try:
            query = session.query(PriceData).filter(
                PriceData.symbol == symbol,
                PriceData.timeframe == timeframe
            ).order_by(PriceData.timestamp.desc()).limit(limit)
            
            results = query.all()
            if not results:
                return pd.DataFrame()
            
            # Convert to DataFrame
            data = {
                'timestamp': [r.timestamp for r in results],
                'open': [r.open for r in results],
                'high': [r.high for r in results],
                'low': [r.low for r in results],
                'close': [r.close for r in results],
                'volume': [r.volume for r in results]
            }
            df = pd.DataFrame(data)
            df.sort_values('timestamp', inplace=True)
            return df
        finally:
            session.close()
    
    def save_price_data(self, df, symbol, timeframe):
        """
        Save price data to database
        
        Parameters:
        - df: DataFrame with OHLCV data
        - symbol: Trading pair symbol
        - timeframe: Chart timeframe
        
        Returns:
        - Number of records inserted
        """
        if df.empty:
            return 0
        
        session = self.get_session()
        try:
            count = 0
            for _, row in df.iterrows():
                timestamp = row.get('timestamp') or row.get('open_time')
                if isinstance(timestamp, (int, float)):
                    # Convert milliseconds to datetime if necessary
                    timestamp = datetime.datetime.fromtimestamp(timestamp / 1000)
                
                # Check if this price point already exists
                existing = session.query(PriceData).filter(
                    PriceData.symbol == symbol,
                    PriceData.timeframe == timeframe,
                    PriceData.timestamp == timestamp
                ).first()
                
                if not existing:
                    price_data = PriceData(
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=timestamp,
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=float(row['volume'])
                    )
                    session.add(price_data)
                    count += 1
            
            session.commit()
            return count
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    # Trading signal operations
    def save_trading_signal(self, signal_data):
        """
        Save a trading signal to database
        
        Parameters:
        - signal_data: Dictionary with signal information
        
        Returns:
        - Created signal object
        """
        session = self.get_session()
        try:
            signal = TradingSignal(**signal_data)
            session.add(signal)
            session.commit()
            return signal
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def get_trading_signals(_self, symbol, timeframe, limit=50, include_closed=False):
        """
        Get trading signals from database
        
        Parameters:
        - symbol: Trading pair symbol
        - timeframe: Chart timeframe
        - limit: Maximum number of records to return
        - include_closed: Whether to include closed signals
        
        Returns:
        - DataFrame with signals
        """
        session = _self.get_session()
        try:
            query = session.query(TradingSignal).filter(
                TradingSignal.symbol == symbol,
                TradingSignal.timeframe == timeframe
            )
            
            if not include_closed:
                query = query.filter(TradingSignal.closed == False)
                
            query = query.order_by(TradingSignal.timestamp.desc()).limit(limit)
            results = query.all()
            
            if not results:
                return pd.DataFrame()
            
            # Convert to DataFrame
            data = {col.name: [getattr(r, col.name) for r in results] 
                   for col in TradingSignal.__table__.columns}
            return pd.DataFrame(data)
        finally:
            session.close()
    
    def close_signal(self, signal_id, exit_price, profit_loss):
        """
        Mark a signal as closed with the result
        
        Parameters:
        - signal_id: ID of the signal to close
        - exit_price: Price at which the position was closed
        - profit_loss: Profit or loss percentage
        
        Returns:
        - True if successful, False otherwise
        """
        session = self.get_session()
        try:
            signal = session.query(TradingSignal).filter(TradingSignal.id == signal_id).first()
            if not signal:
                return False
            
            signal.closed = True
            signal.closed_at = datetime.datetime.utcnow()
            signal.profit_loss = profit_loss
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    # Backtest operations
    def save_backtest_result(self, backtest_data):
        """
        Save backtest results to database
        
        Parameters:
        - backtest_data: Dictionary with backtest information
        
        Returns:
        - Created backtest object
        """
        session = self.get_session()
        try:
            backtest = BacktestResult(**backtest_data)
            session.add(backtest)
            session.commit()
            return backtest
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def get_backtest_results(_self, symbol=None, limit=20):
        """
        Get backtest results from database
        
        Parameters:
        - symbol: Optional symbol filter
        - limit: Maximum number of records to return
        
        Returns:
        - DataFrame with backtest results
        """
        session = _self.get_session()
        try:
            query = session.query(BacktestResult)
            
            if symbol:
                query = query.filter(BacktestResult.symbol == symbol)
                
            query = query.order_by(BacktestResult.created_at.desc()).limit(limit)
            results = query.all()
            
            if not results:
                return pd.DataFrame()
            
            # Convert to DataFrame
            data = {col.name: [getattr(r, col.name) for r in results] 
                   for col in BacktestResult.__table__.columns}
            return pd.DataFrame(data)
        finally:
            session.close()

# Singleton instance for database access
db_manager = DBManager()