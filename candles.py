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
    
    def find_inverse_fvgs(self, min_gap_pct: float = 0.0005) -> List[Dict[str, Any]]:
        """Find Inverse Fair Value Gaps - where price filled/traded through the FVG"""
        ifvgs = []
        for i in range(2, len(self.candles)):
            c1 = self.candles[i - 2]
            c3 = self.candles[i]
            
            # Check for original FVG then check if price filled it
            
            # Bullish FVG originally: c1 high < c3 low
            # IFVG: price traded BELOW that gap (filled it)
            if c1.high < c3.low:
                gap_top = c3.low
                gap_bottom = c1.high
                size = gap_top - gap_bottom
                
                if size / c3.low > min_gap_pct:
                    # Check if any candle AFTER c3 traded below the gap (filled it)
                    filled = any(c.low < gap_bottom for c in self.candles[i+1:i+5])
                    if filled:
                        ifvgs.append({
                            'index': i,
                            'type': 'bullish',
                            'top': gap_top,
                            'bottom': gap_bottom,
                            'size': size,
                            'mid': (gap_top + gap_bottom) / 2
                        })
            
            # Bearish FVG originally: c1 low > c3 high
            # IFVG: price traded ABOVE that gap (filled it)
            if c1.low > c3.high:
                gap_top = c1.low
                gap_bottom = c3.high
                size = gap_top - gap_bottom
                
                if size / c3.high > min_gap_pct:
                    # Check if any candle AFTER c3 traded above the gap (filled it)
                    filled = any(c.high > gap_top for c in self.candles[i+1:i+5])
                    if filled:
                        ifvgs.append({
                            'index': i,
                            'type': 'bearish',
                            'top': gap_top,
                            'bottom': gap_bottom,
                            'size': size,
                            'mid': (gap_top + gap_bottom) / 2
                        })
        
        return ifvgs
    
    def find_unfilled_fvgs(self, min_gap_pct: float = 0.0005) -> List[Dict[str, Any]]:
        """Find Fair Value Gaps that have NOT been filled yet"""
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
                    # Check if price FILLED it (traded below)
                    filled = any(c.low < gap_bottom for c in self.candles[i+1:i+5])
                    if not filled:
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
                    # Check if price FILLED it (traded above)
                    filled = any(c.high > gap_top for c in self.candles[i+1:i+5])
                    if not filled:
                        fvgs.append({
                            'index': i,
                            'type': 'bearish',
                            'top': gap_top,
                            'bottom': gap_bottom,
                            'size': size,
                            'mid': (gap_top + gap_bottom) / 2
                        })
        
        return fvgs
    
    def find_liquidity_zones(self, lookback: int = 20, max_breaches: int = 1) -> Dict[str, List[float]]:
        """Find recent liquidity zones - filtered by ICT logic (levels that haven't been breached)"""
        swing_highs = self.find_swing_highs(lookback=3)
        swing_lows = self.find_swing_lows(lookback=3)
        
        # Filter resistance: count how many times price traded ABOVE each level after it formed
        valid_resistance = []
        for sh in swing_highs[-lookback:]:
            price = sh['price']
            idx = sh['index']
            # Count candles that traded above this level AFTER it formed
            breaches = sum(1 for c in self.candles[idx+1:] if c.high > price)
            if breaches <= max_breaches:
                valid_resistance.append(price)
        
        # Filter support: count how many times price traded BELOW each level after it formed
        valid_support = []
        for sl in swing_lows[-lookback:]:
            price = sl['price']
            idx = sl['index']
            # Count candles that traded below this level AFTER it formed
            breaches = sum(1 for c in self.candles[idx+1:] if c.low < price)
            if breaches <= max_breaches:
                valid_support.append(price)
        
        return {
            'resistance': valid_resistance,
            'support': valid_support
        }
    
    def find_opening_range(self, minutes: int = 30) -> Optional[Dict[str, Any]]:
        """Find the Opening Range (OR) - high/low of first N minutes of TODAY's session"""
        if len(self.candles) < 2:
            return None
        
        # Get today's date from the most recent candle
        today = self.candles[-1].timestamp.date()
        
        # Filter to only today's candles
        today_candles = [c for c in self.candles if c.timestamp.date() == today]
        
        if len(today_candles) < 2:
            return None
        
        # Get the first N candles from today
        num_candles = min(minutes, len(today_candles))
        or_candles = today_candles[:num_candles]
        
        or_high = max(c.high for c in or_candles)
        or_low = min(c.low for c in or_candles)
        
        return {
            'high': or_high,
            'low': or_low,
            'range': or_high - or_low,
            'candles': num_candles,
            'start_time': or_candles[0].timestamp,
            'end_time': or_candles[-1].timestamp
        }
    
    def find_daily_high_low(self) -> Optional[Dict[str, Any]]:
        """Find the Daily High and Low for the current session"""
        if len(self.candles) < 1:
            return None
        
        # Get today's date from the most recent candle
        today = self.candles[-1].timestamp.date()
        
        # Filter candles to just today
        today_candles = [c for c in self.candles if c.timestamp.date() == today]
        
        if not today_candles:
            return None
        
        daily_high = max(c.high for c in today_candles)
        daily_low = min(c.low for c in today_candles)
        
        return {
            'high': daily_high,
            'low': daily_low,
            'range': daily_high - daily_low,
            'candles': len(today_candles),
            'first_candle': today_candles[0].timestamp,
            'last_candle': today_candles[-1].timestamp
        }
    
    def find_pivot_levels(self) -> Optional[Dict[str, float]]:
        """Calculate Daily Pivot levels based on previous day's HLC"""
        if len(self.candles) < 2:
            return None
        
        # Get today's date from the most recent candle
        today = self.candles[-1].timestamp.date()
        
        # Get yesterday's candles (the day before today)
        yesterday_candles = [c for c in self.candles if c.timestamp.date() < today]
        
        if not yesterday_candles:
            return None
        
        # Get the most recent day's candles (could be yesterday or earlier if market closed)
        unique_days = sorted(set(c.timestamp.date() for c in yesterday_candles))
        if len(unique_days) < 1:
            return None
        
        # Use the most recent complete day
        last_day = unique_days[-1]
        last_day_candles = [c for c in yesterday_candles if c.timestamp.date() == last_day]
        
        if not last_day_candles:
            return None
        
        high = max(c.high for c in last_day_candles)
        low = min(c.low for c in last_day_candles)
        close = last_day_candles[-1].close
        
        # Calculate pivot levels
        pivot = (high + low + close) / 3
        r1 = (2 * pivot) - low
        r2 = pivot + (high - low)
        r3 = high + 2 * (pivot - low)
        s1 = (2 * pivot) - high
        s2 = pivot - (high - low)
        s3 = low - 2 * (high - pivot)
        
        return {
            'pivot': pivot,
            'r1': r1,
            'r2': r2,
            'r3': r3,
            's1': s1,
            's2': s2,
            's3': s3,
            'high': high,
            'low': low,
            'close': close
        }
    
    def find_fibonacci_retracement(self) -> Optional[Dict[str, Any]]:
        """Find Fibonacci retracement for the most recent swing move (ICT style)"""
        if len(self.candles) < 10:
            return None
        
        # Find the most recent swing high and swing low
        swing_highs = self.find_swing_highs(lookback=5)
        swing_lows = self.find_swing_lows(lookback=5)
        
        if not swing_highs or not swing_lows:
            return None
        
        # Get the most recent swing high and low
        last_high = swing_highs[-1]
        last_low = swing_lows[-1]
        
        # Determine if it's an uptrend or downtrend
        if last_high['timestamp'] > last_low['timestamp']:
            # Uptrend: low to high
            start = last_low['price']
            end = last_high['price']
            move_type = 'uptrend'
        else:
            # Downtrend: high to low
            start = last_high['price']
            end = last_low['price']
            move_type = 'downtrend'
        
        move_range = abs(end - start)
        
        if move_range == 0:
            return None
        
        # Fibonacci levels
        fib_levels = {
            '0.0': start,
            '23.6': start + (move_range * 0.236),
            '38.2': start + (move_range * 0.382),
            '50.0': start + (move_range * 0.50),
            '61.8': start + (move_range * 0.618),
            '78.6': start + (move_range * 0.786),
            '100.0': end
        }
        
        return {
            'start': start,
            'end': end,
            'move_type': move_type,
            'levels': fib_levels
        }
    
    def find_extended_fibonacci(self) -> Optional[Dict[str, Any]]:
        """Find Extended Fibonacci levels for target projections (ICT style)"""
        if len(self.candles) < 10:
            return None
        
        # Find the most recent swing high and swing low
        swing_highs = self.find_swing_highs(lookback=5)
        swing_lows = self.find_swing_lows(lookback=5)
        
        if not swing_highs or not swing_lows:
            return None
        
        # Get the most recent swing high and low
        last_high = swing_highs[-1]
        last_low = swing_lows[-1]
        
        # Determine trend direction
        if last_high['timestamp'] > last_low['timestamp']:
            # Uptrend: low to high
            start = last_low['price']
            end = last_high['price']
            move_type = 'uptrend'
        else:
            # Downtrend: high to low
            start = last_high['price']
            end = last_low['price']
            move_type = 'downtrend'
        
        move_range = abs(end - start)
        
        if move_range == 0:
            return None
        
        # Extended Fibonacci levels for ICT
        # For bullish: 1.0 at bottom (start), 0 at top (end), negatives below are profit targets
        # For bearish: 1.0 at top (start), 0 at bottom (end), negatives above are profit targets
        if move_type == 'uptrend':
            # Bullish: 1.0 at start (low), 0 at end (high), negatives below are profit targets
            fib_extended = {
                '-1.0': start - move_range,
                '-0.62': start - (move_range * 0.62),
                '-0.27': start - (move_range * 0.27),
                '0.0': end,
                '0.25': end - (move_range * 0.25),
                '0.5': end - (move_range * 0.5),
                '0.618': end - (move_range * 0.382),
                '0.705': end - (move_range * 0.295),
                '0.79': end - (move_range * 0.21),
                '1.0': start
            }
        else:
            # Bearish: 1.0 at start (high), 0 at end (low), negatives above are profit targets
            fib_extended = {
                '-1.0': start + move_range,
                '-0.62': start + (move_range * 0.62),
                '-0.27': start + (move_range * 0.27),
                '0.0': end,
                '0.25': end + (move_range * 0.25),
                '0.5': end + (move_range * 0.5),
                '0.618': end + (move_range * 0.382),
                '0.705': end + (move_range * 0.295),
                '0.79': end + (move_range * 0.21),
                '1.0': start
            }
        
        return {
            'start': start,
            'end': end,
            'move_type': move_type,
            'levels': fib_extended
        }
    
    def find_entry_zone(self) -> Optional[Dict[str, Any]]:
        """Find entry zone based on ICT concepts - current price vs key levels"""
        if not self.candles or len(self.candles) < 1:
            return None
        
        current_price = self.candles[-1].close
        
        # Get key levels
        fibs = self.find_fibonacci_retracement()
        pivots = self.find_pivot_levels()
        fvgs = self.find_unfilled_fvgs()
        
        entry_levels = []
        
        # Fibonacci key levels
        if fibs and fibs.get('levels'):
            for level_name in ['38.2', '61.8', '50.0']:
                if level_name in fibs['levels']:
                    entry_levels.append({
                        'level': fibs['levels'][level_name],
                        'type': f'Fib {level_name}',
                        'source': 'fib'
                    })
        
        # Pivot levels
        if pivots:
            for level in ['s1', 'r1']:
                if pivots.get(level):
                    entry_levels.append({
                        'level': pivots[level],
                        'type': level.upper(),
                        'source': 'pivot'
                    })
        
        # FVG midpoints (last 2)
        if fvgs:
            for fvg in fvgs[-2:]:
                if fvg.get('mid'):
                    entry_levels.append({
                        'level': fvg['mid'],
                        'type': 'FVG Mid',
                        'source': 'fvg'
                    })
        
        # Find closest entry level to current price
        closest_entry = None
        min_dist = float('inf')
        for entry in entry_levels:
            dist = abs(current_price - entry['level'])
            if dist < min_dist:
                min_dist = dist
                closest_entry = entry
        
        # Determine direction: if entry is below current price = long/bullish, above = short/bearish
        direction = 'bullish'
        if closest_entry and closest_entry['level'] > current_price:
            direction = 'bearish'
        
        return {
            'current_price': current_price,
            'closest_entry': closest_entry,
            'all_entries': entry_levels,
            'direction': direction
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
