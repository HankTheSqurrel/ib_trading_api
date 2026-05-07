from typing import Optional, List, Dict, Any
from ib_insync import IB, Contract, Ticker
import pandas as pd

# Optional import for Yahoo Finance delayed data
try:
    import yfinance as yf
except ImportError:
    yf = None  # Will be handled at runtime

def get_realtime_quote(ib: IB, contract: Contract, timeout: float = 15.0) -> Dict[str, Any]:
    """
    Get real-time quote for a contract.
    
    Args:
        ib: IB instance
        contract: Contract to quote
        timeout: Wait timeout in seconds (default 15s for futures)
    
    Returns:
        Dict with bid, ask, last, high, low, volume, etc.
        Note: May return delayed data if no market data subscription.
    """
    import time
    
    # Qualify contract first
    qualified = ib.qualifyContracts(contract)
    if qualified:
        contract = qualified[0]
    
    # Request market data (generic tickers for futures)
    ticker = ib.reqMktData(contract, "", False, False)
    
    # Wait for data with polling (futures take longer)
    start = time.time()
    while time.time() - start < timeout:
        if ticker.bid is not None and ticker.bid > 0:
            break
        time.sleep(0.2)
    
    # Check if data is delayed
    is_delayed = hasattr(ticker, 'delayed') and ticker.delayed
    
    return {
        "bid": ticker.bid,
        "ask": ticker.ask,
        "last": ticker.last,
        "high": ticker.high,
        "low": ticker.low,
        "close": ticker.close,
        "volume": ticker.volume,
        "bid_size": ticker.bidSize,
        "ask_size": ticker.askSize,
        "last_size": ticker.lastSize,
        "model_greeks": ticker.modelGreeks if hasattr(ticker, 'modelGreeks') else None,
        "delayed": is_delayed
    }

def get_historical_data(
    ib: IB,
    contract: Contract,
    duration: str = "1 D",  # e.g., "1 D", "1 W", "1 M", "1 Y"
    bar_size: str = "1 min",  # e.g., "1 min", "5 mins", "1 hour", "1 day"
    what_to_show: str = "TRADES",
    use_rth: bool = True
) -> pd.DataFrame:
    """
    Get historical data for a contract.
    
    Args:
        ib: IB instance
        contract: Contract to get data for
        duration: How much data to get (e.g., "1 D", "1 W", "1 M")
        bar_size: Bar size (e.g., "1 min", "5 mins", "1 hour")
        what_to_show: What data to show (TRADES, BID, ASK, MIDPOINT, etc.)
        use_rth: Use regular trading hours only
    
    Returns:
        DataFrame with OHLCV data
    """
    bars = ib.reqHistoricalData(
        contract,
        "",
        durationStr=duration,
        barSizeSetting=bar_size,
        whatToShow=what_to_show,
        useRTH=use_rth,
        formatDate=1
    )
    
    if bars is None or len(bars) == 0:
        return pd.DataFrame()
    
    return pd.DataFrame([{
        "date": bar.date,
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": bar.volume,
        "average": bar.average,
        "bar_count": bar.barCount
    } for bar in bars])

def subscribe_quote(ib: IB, contract: Contract, callback=None):
    """
    Subscribe to real-time quotes.
    
    Args:
        ib: IB instance
        contract: Contract to subscribe to
        callback: Optional callback function(ticker)
    
    Returns:
        Ticker object
    """
    ticker = ib.reqMktData(contract, "", False, False)
    
    if callback:
        ticker.updateEvent += callback
    
    return ticker

def unsubscribe_quote(ib: IB, ticker: Ticker):
    """Unsubscribe from real-time quotes"""
    ib.cancelMktData(ticker.contract)

def get_contract_details(ib: IB, contract: Contract) -> Optional[Dict[str, Any]]:
    """
    Get contract details.
    
    Args:
        ib: IB instance
        contract: Contract to get details for
    
    Returns:
        Dict with contract details
    """
    details = ib.reqContractDetails(contract)
    
    if not details:
        return None
    
    d = details[0]
    return {
        "symbol": d.contract.symbol,
        "sec_type": d.contract.secType,
        "exchange": d.contract.exchange,
        "currency": d.contract.currency,
        "expiry": d.contract.lastTradeDateOrContractMonth,
        "strike": d.contract.strike,
        "right": d.contract.right,
        "multiplier": d.contract.multiplier,
        "primary_exchange": d.contract.primaryExchange,
        "name": d.contract.name,
        "min_tick": d.minTick,
        "market_name": d.marketName,
        "valid_exchanges": d.validExchanges,
        "long_name": d.longName,
        "contract_month": d.contractMonth,
        "industry": d.industry,
        "category": d.category,
        "subcategory": d.subcategory,
        "time_zone": d.timeZoneId,
        "trading_hours": d.tradingHours,
        "liquid_hours": d.liquidHours
    }

# -------------------------------------------------
# Delayed data (Yahoo Finance) API
# -------------------------------------------------

# Yahoo Finance ticker mapping for futures

def get_yahoo_historical(symbol: str,
                         period: str = "5d",
                         interval: str = "5m") -> pd.DataFrame:
    """Fetch a multi‑row historical series from Yahoo Finance.
    
    Args:
        symbol: Ticker symbol (e.g., "MES=F" or any stock symbol).
        period: How far back to fetch (e.g., "5d", "1mo", "1y").
        interval: Bar size – Yahoo supports "1m", "2m", "5m", "15m", "30m",
                  "60m", "90m", "1h", "1d", etc.
    
    Returns:
        DataFrame with columns: date, open, high, low, close, volume.
        If no data is found, returns an empty DataFrame.
    """
    if yf is None:
        raise ImportError("yfinance is required for Yahoo historical data")
    # Convert futures symbols to Yahoo format automatically
    yahoo_sym = YAHOO_FUTURE_TICKERS.get(symbol.upper(), symbol)
    ticker = yf.Ticker(yahoo_sym)
    df = ticker.history(period=period, interval=interval)
    if df.empty:
        return pd.DataFrame()
    # Reset index to get a ‘date’ column and rename columns to match IB output
    df = df.reset_index().rename(columns={
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume"
    })
    return df[["date", "open", "high", "low", "close", "volume"]]

# Yahoo Finance ticker mapping for futures
# Note: yfinance may need different ticker formats
YAHOO_FUTURE_TICKERS = {
    "MES": "MES=F",   # Micro E-mini S&P 500 (front month)
    "MNQ": "MNQ=F",   # Micro E-mini NASDAQ 100
    "MYM": "MYM=F",   # Micro Dow Jones
    "M6M": "M6M=F",   # Micro E-mini EUR/USD
    "ES": "ES=F",     # E-mini S&P 500
    "NQ": "NQ=F",     # E-mini NASDAQ 100
    "YM": "YM=F",     # E-mini Dow
}

# Alternative ticker formats to try if first fails
YAHOO_FUTURE_ALTERNATIVES = {
    "MES": ["MES=F", "MES1!", "MES.F"],
    "MNQ": ["MNQ=F", "MNQ1!", "MNQ.F"],
    "MYM": ["MYM=F", "MYM1!", "MYM.F"],
    "ES": ["ES=F", "ES1!", "ES.F"],
}

def get_delayed_quote(symbol: str) -> Dict[str, Any]:
    """Legacy wrapper – returns only the latest bar (used by older code)."""
    # This function is kept for backward compatibility; it simply returns the most recent
    # delayed quote from Yahoo Finance.  For full historical series see `get_yahoo_historical`.
    # The implementation below delegates to `get_yahoo_historical` and picks the last row.
    df = get_yahoo_historical(symbol, period="5d", interval="5m")
    if df.empty:
        raise ValueError(f"No data found for {symbol} via Yahoo Finance")
    latest = df.iloc[-1]
    return {
        "symbol": symbol,
        "bid": float(latest.get('close')),
        "ask": float(latest.get('close')),
        "last": float(latest.get('close')),
        "high": float(latest.get('high')) if pd.notna(latest.get('high')) else None,
        "low": float(latest.get('low')) if pd.notna(latest.get('low')) else None,
        "volume": int(latest.get('volume')) if pd.notna(latest.get('volume')) else 0,
        "timestamp": str(latest.get('date')),
    }
    """Fetch delayed quote data for a ticker symbol using Yahoo Finance.
    
    Automatically converts futures symbols to Yahoo format:
    - MES -> MES=F
    - MNQ -> MNQ=F
    - MYM -> MYM=F
    - M6M -> M6M=F
    
    For stocks: use symbol directly (e.g., "AAPL", "MSFT")

    This uses the `yfinance` library which provides delayed (typically ~15‑minute)
    market data for free. The function returns a dictionary compatible with the
    format of `get_realtime_quote` so callers can treat both sources uniformly.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MSFT") or futures (e.g., "MES").

    Returns:
        Dict with keys: bid, ask, last, high, low, volume, and timestamp.
        If data is unavailable, returns an empty dict.
    """
    if yf is None:
        raise ImportError("yfinance package is required for delayed Yahoo data. Install it via requirements.txt.")
    
    # Convert futures symbol to Yahoo format
    yahoo_symbol = YAHOO_FUTURE_TICKERS.get(symbol.upper(), symbol)
    
    # Try multiple ticker formats for futures
    symbols_to_try = YAHOO_FUTURE_ALTERNATIVES.get(symbol.upper(), [yahoo_symbol])
    
    data = None
    last_error = None
    for sym in symbols_to_try:
        try:
            ticker = yf.Ticker(sym)
            data = ticker.history(period="5d", interval="5m")  # 5 days, 5-minute bars
            if data is not None and not data.empty:
                yahoo_symbol = sym
                break
        except Exception as e:
            last_error = str(e)
            continue
    
    if data is None or data.empty:
        raise ValueError(f"No data found for {symbol} (tried: {symbols_to_try})")
    
    # Get latest bar
    latest = data.iloc[-1]
    return {
        "symbol": yahoo_symbol,
        "bid": float(latest.get('Close')),
        "ask": float(latest.get('Close')),
        "last": float(latest.get('Close')),
        "high": float(latest.get('High')) if pd.notna(latest.get('High')) else None,
        "low": float(latest.get('Low')) if pd.notna(latest.get('Low')) else None,
        "volume": int(latest.get('Volume')) if pd.notna(latest.get('Volume')) else 0,
        "timestamp": latest.name.isoformat() if hasattr(latest.name, 'isoformat') else str(latest.name),
    }

def get_quote(symbol: str, source: str = "yahoo", ib: Optional[IB] = None, contract: Optional[Contract] = None, timeout: float = 5.0) -> Dict[str, Any]:
    """Unified quote getter supporting delayed Yahoo data and IB realtime.

    Args:
        symbol: Ticker symbol (e.g., "AAPL").
        source: "yahoo" for delayed data, "ib" for IB realtime.
        ib: IB instance required when source == "ib".
        contract: IB Contract required when source == "ib".
        timeout: Timeout for IB realtime calls.

    Returns:
        Quote dictionary.
    """
    if source == "ib":
        if ib is None or contract is None:
            raise ValueError("IB instance and Contract must be provided for IB realtime source")
        return get_realtime_quote(ib, contract, timeout)
    return get_delayed_quote(symbol)
