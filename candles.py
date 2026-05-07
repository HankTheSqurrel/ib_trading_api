"""
Candles - OHLCV data storage and ICT analysis tools
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import pandas as pd


@dataclass
class Candle:
    """Single OHLCV candle"""
    timestamp: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    
    @property
    def body(self) -> float:
        """Size of the candle body"""
        return abs(self.close - self.open)
    
    @property
    def is_bullish(self) -> bool:
        """Was this candle bullish?"""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """Was this candle bearish?"""
        return self.close < self.open
    
    @property
    def range(self) -> float:
        """Full range (high - low)"""
        return self.high - self.low


@dataclass
class CandleStore:
    """Store and analyze OHLCV candles"""
    symbol: str = ""
    timeframe: str = "5m"
    candles: List[Candle] = field(default_factory=list)
    
    def add_bars(self, df: pd.DataFrame) -> None:
        """Add bars from a DataFrame"""
        for _, row in df.iterrows():
            candle = Candle(
                timestamp=pd.to_datetime(row.get('date', row.get('datetime', row.name))),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=int(row.get('volume', 0))
            )
            self.candles.append(candle)
    
    def add_candle(self, candle: Candle) -> None:
        """Add a single candle"""
        self.candles.append(candle)
    
    @property
    def df(self) -> pd.DataFrame:
        """Get all candles as a DataFrame"""
        if not self.candles:
            return pd.DataFrame()
        
        return pd.DataFrame([{
            'timestamp': c.timestamp,
            'open': c.open,
            'high': c.high,
            'low': c.low,
            'close': c.close,
            'volume': c.volume,
            'body': c.body,
            'is_bullish': c.is_bullish,
            'range': c.range
        } for c in self.candles])
    
    @property
    def last_candle(self) -> Optional[Candle]:
        """Get the most recent candle"""
        return self.candles[-1] if self.candles else None
    
    @property
    def last_close(self) -> Optional[float]:
        """Get the most recent close price"""
        return self.last_candle.close if self.last_candle else None
    
    # ==================== ICT Analysis ====================
    
    def find_swing_highs(self, lookback: int = 5) -> List[Dict[str, Any]]:
        """Find swing highs (local maxima)"""
        swings = []
        for i in range(lookback, len(self.candles) - lookback):
            candle = self.candles[i]
            before_higher = any(self.candles[j].high >= candle.high for j in range(i - lookback, i))
            after_higher = any(self.candles[j].high >= candle.high for j in range(i + 1, i + lookback + 1))
            if not before_higher and not after_higher:
                swings.append({
                    'index': i,
                    'timestamp': candle.timestamp,
                    'price': candle.high,
                    'type': 'swing_high'
                })
        return swings
    
    def find_swing_lows(self, lookback: int = 5) -> List[Dict[str, Any]]:
        """Find swing lows (local minima)"""
        swings = []
        for i in range(lookback, len(self.candles) - lookback):
            candle = self.candles[i]
            before_lower = any(self.candles[j].low <= candle.low for j in range(i - lookback, i))
            after_lower = any(self.candles[j].low <= candle.low for j in range(i + 1, i + lookback + 1))
            if not before_lower and not after_lower:
                swings.append({
                    'index': i,
                    'timestamp': candle.timestamp,
                    'price': candle.low,
                    'type': 'swing_low'
                })
        return swings
    
    def find_fair_value_gaps(self, min_gap_pct: float = 0.0005) -> List[Dict[str, Any]]:
        """Find Fair Value Gaps (FVG)"""
        fvgs = []
        for i in range(2, len(self.candles)):
            c1 = self.candles[i - 2]
            c3 = self.candles[i]
            
            # Bullish FVG: c1 high < c3 low
            if c1.high < c3.low:
                gap_top = c3.low
                gap_bottom = c1.high
                size = gap_top - gap_bottom
                if size / c3.low > min_gap_pct:
                    fvgs.append({
                        'index': i,
                        'type': 'bullish',
                        'top': gap_top,
                        'bottom': gap_bottom,
                        'size': size,
                        'mid': (gap_top + gap_bottom) / 2
                    })
            
            # Bearish FVG: c1 low > c3 high
            if c1.low > c3.high:
                gap_top = c1.low
                gap_bottom = c3.high
                size = gap_top - gap_bottom
                if size / c3.high > min_gap_pct:
                    fvgs.append({
                        'index': i,
                        'type': 'bearish',
                        'top': gap_top,
                        'bottom': gap_bottom,
                        'size': size,
                        'mid': (gap_top + gap_bottom) / 2
                    })
        
        return fvgs
    
    def find_liquidity_zones(self, lookback: int = 20) -> Dict[str, List[float]]:
        """Find recent liquidity zones"""
        swing_highs = self.find_swing_highs(lookback=3)
        swing_lows = self.find_swing_lows(lookback=3)
        
        return {
            'resistance': [s['price'] for s in swing_highs[-lookback:]],
            'support': [s['price'] for s in swing_lows[-lookback:]]
        }
    
    def get_recent_trend(self, lookback: int = 20) -> str:
        """Determine recent trend"""
        if len(self.candles) < lookback:
            return 'insufficient_data'
        
        recent = self.candles[-lookback:]
        bullish_count = sum(1 for c in recent if c.is_bullish)
        bearish_count = sum(1 for c in recent if c.is_bearish)
        overall_change = (recent[-1].close - recent[0].open) / recent[0].open
        
        if bullish_count > bearish_count * 1.5 and overall_change > 0.01:
            return 'bullish'
        elif bearish_count > bullish_count * 1.5 and overall_change < -0.01:
            return 'bearish'
        return 'consolidating'
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary with ICT analysis"""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'candle_count': len(self.candles),
            'last_close': self.last_close,
            'trend': self.get_recent_trend(),
            'swing_highs': len(self.find_swing_highs()),
            'swing_lows': len(self.find_swing_lows()),
            'fvg_count': len(self.find_fair_value_gaps()),
            'liquidity': self.find_liquidity_zones()
        }


def create_store(symbol: str, timeframe: str = "5m") -> CandleStore:
    """Create a new CandleStore"""
    return CandleStore(symbol=symbol, timeframe=timeframe)


def load_from_dataframe(df: pd.DataFrame, symbol: str, timeframe: str = "5m") -> CandleStore:
    """Create a CandleStore from DataFrame"""
    store = CandleStore(symbol=symbol, timeframe=timeframe)
    store.add_bars(df)
    return store
