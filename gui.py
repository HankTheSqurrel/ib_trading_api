"""
Simple Tkinter GUI for the IB Trading API and ICT analysis.

Features:
- Enter symbol and fetch data.
- Build a CandleStore and run ICT analysis.
- Auto-refresh chart every 1 second with latest data.
- Tabs for Info and Chart.

Run with:
    python gui.py
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk

FigureCanvasTkagg = None
try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg as FigureCanvasTkagg
except ImportError:
    try:
        from matplotlib.backends.backend_tkagg import FigureCanvasTkagg
    except ImportError:
        pass

from ib_trading_api import IBClient, get_historical_data
from ib_trading_api.candles import load_from_dataframe
from ib_insync import Future

# Global state for live updating
live_client = None
live_symbol = None
live_timeframe = None
live_contract = None
study_frame = None
study_fig = None
study_ax = None
study_canvas = None
fib_frame = None
fib_fig = None
fib_ax = None
fib_canvas = None
update_id = None


def fetch_and_analyze():
    global live_client, live_symbol, live_timeframe, live_contract
    global study_frame, study_fig, study_ax, study_canvas, fib_frame, fib_fig, fib_ax, fib_canvas, update_id
    
    try:
        symbol = symbol_var.get().strip()
        # Default to futures on CME
        sec_type = "FUT"
        exchange = "CME"
        expiry = ""
        timeframe = "5m"

        # Disconnect existing client if any
        if live_client and live_client.is_connected:
            live_client.disconnect()
            live_client.ib = None
        
        # Cancel any pending updates
        if update_id:
            root.after_cancel(update_id)
            update_id = None

        client = IBClient()
        if not client.connect_sync():
            output.insert(tk.END, "Failed to connect to IB.\n")
            return

        contract = client.create_contract(symbol, sec_type, exchange, "USD", expiry if expiry else None)

        qualified = client.ib.qualifyContracts(contract)
        if qualified:
            contract = qualified[0]

        df = get_historical_data(client.ib, contract, duration="5 D", bar_size="5 mins")

        # Fall back to Yahoo if IB returns no data
        if df.empty:
            try:
                from ib_trading_api.market_data import get_yahoo_historical
                df = get_yahoo_historical(symbol, period="5d", interval="5m")
                if df.empty:
                    raise ValueError("No data found via Yahoo Finance")
                output.insert(tk.END, f"Used delayed Yahoo data ({len(df)} bars).\n")
            except Exception as e:
                output.insert(tk.END, f"No historical data: {e}\n")
                return

        # Store globals for live updates
        live_client = client
        live_symbol = symbol
        live_timeframe = timeframe
        live_contract = contract

        # Load into CandleStore and run analysis
        store = load_from_dataframe(df, symbol=symbol, timeframe=timeframe)
        summary = store.get_summary()

        output.insert(tk.END, f"--- Summary for {symbol} ({timeframe}) ---\n")
        for k, v in summary.items():
            output.insert(tk.END, f"{k}: {v}\n")
        output.insert(tk.END, "\nSwing Highs:\n")
        for sh in store.find_swing_highs():
            output.insert(tk.END, f"  {sh['timestamp']} - {sh['price']}\n")
        output.insert(tk.END, "\nSwing Lows:\n")
        for sl in store.find_swing_lows():
            output.insert(tk.END, f"  {sl['timestamp']} - {sl['price']}\n")
        output.insert(tk.END, "\nFair Value Gaps:\n")
        for fvg in store.find_fair_value_gaps():
            output.insert(tk.END, f"  {fvg['type']} gap at {fvg['mid']:.2f} (size {fvg['size']:.2f})\n")
        output.insert(tk.END, "\nLiquidity Zones:\n")
        zones = store.find_liquidity_zones()
        output.insert(tk.END, f"  Support: {zones['support']}\n")
        output.insert(tk.END, f"  Resistance: {zones['resistance']}\n")
        
        output.insert(tk.END, "\n--- Live update: Refreshing every 1 second ---\n")
        
        # Switch to Study Chart tab
        notebook.select(study_tab)
        
        # Create the live charts on separate tabs
        create_live_chart(df, store)
        
    except Exception as e:
        messagebox.showerror("Error", str(e))


def create_live_chart(df, store):
    global study_frame, study_fig, study_ax, study_canvas, fib_frame, fib_fig, fib_ax, fib_canvas
    
    # Clear previous charts if exists
    for widget in study_tab.winfo_children():
        widget.destroy()
    for widget in fib_tab.winfo_children():
        widget.destroy()
    
    # --- Study Chart (main candlestick chart with ICT analysis) ---
    study_frame = ttk.Frame(study_tab)
    study_frame.pack(fill=tk.BOTH, expand=True)
    
    study_fig = Figure(figsize=(16, 6), dpi=100)
    study_ax = study_fig.add_subplot(111)
    
    # Get analysis data
    swing_highs = store.find_swing_highs()
    swing_lows = store.find_swing_lows()
    liquidity = store.find_liquidity_zones()
    opening_range = None
    if hasattr(store, 'find_opening_range'):
        opening_range = store.find_opening_range(minutes=30)
    daily_high_low = None
    if hasattr(store, 'find_daily_high_low'):
        daily_high_low = store.find_daily_high_low()
    ifvgs = store.find_inverse_fvgs()
    fvgs = store.find_unfilled_fvgs()
    pivots = store.find_pivot_levels()
    fibs = store.find_fibonacci_retracement()
    fibs_ext = store.find_extended_fibonacci()
    entry_zone = store.find_entry_zone()
    
    # Draw study chart
    draw_candles(study_ax, df, swing_highs, swing_lows, liquidity, opening_range, daily_high_low, ifvgs, fvgs, pivots, fibs, entry_zone)
    
    study_canvas = FigureCanvasTkagg(study_fig, master=study_frame)
    study_canvas.draw()
    study_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    toolbar = NavigationToolbar2Tk(study_canvas, study_frame)
    toolbar.update()
    
    # --- Fib Chart (Fibonacci extension) ---
    fib_frame = ttk.Frame(fib_tab)
    fib_frame.pack(fill=tk.BOTH, expand=True)
    
    fib_fig = Figure(figsize=(16, 6), dpi=100)
    fib_ax = fib_fig.add_subplot(111)
    
    # Draw fib chart
    draw_fib_chart(fib_ax, df, swing_highs, swing_lows, fibs_ext)
    
    fib_canvas = FigureCanvasTkagg(fib_fig, master=fib_frame)
    fib_canvas.draw()
    fib_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    toolbar2 = NavigationToolbar2Tk(fib_canvas, fib_frame)
    toolbar2.update()
    
    # Start the update loop
    schedule_update(df, store)


def draw_fib_chart(ax, df, swing_highs=None, swing_lows=None, fibs_ext=None):
    """Draw second chart with only Fibonacci extended levels"""
    import pandas as pd
    
    ax.clear()
    dates = pd.to_datetime(df['date'])
    
    # Plot candles (simpler - just wicks and bodies)
    for i, row in df.iterrows():
        date = dates.iloc[i]
        open_price = row['open']
        close_price = row['close']
        high = row['high']
        low = row['low']
        
        if close_price >= open_price:
            color = 'green'
            ax.plot([date, date], [low, high], color=color, linewidth=0.5)
            ax.plot([date, date], [open_price, close_price], color=color, linewidth=2)
        else:
            color = 'red'
            ax.plot([date, date], [low, high], color=color, linewidth=0.5)
            ax.plot([date, date], [open_price, close_price], color=color, linewidth=2)
    
    ax.set_xlabel('Date/Time')
    ax.set_ylabel('Price')
    
    # Add Bullish/Bearish label
    direction_label = ''
    if fibs_ext and fibs_ext.get('move_type'):
        direction_label = fibs_ext['move_type'].upper()
    label_color = 'green' if direction_label == 'UPTREND' else 'red'
    ax.set_title(f'{live_symbol} - Fibonacci Extension ({direction_label})', fontsize=12, color=label_color, fontweight='bold')
    ax.grid(True, alpha=0.3)
    plot_fig.autofmt_xdate()
    
    # Plot extended Fibonacci levels
    if fibs_ext and len(dates) > 0:
        fib_levels = fibs_ext.get('levels', {})
        
        fib_colors = {
            '-1.0': 'green',
            '-0.62': 'green',
            '-0.27': 'green',
            '0.0': 'green',
            '0.25': 'cyan',
            '0.5': 'purple',
            '0.618': 'yellow',
            '0.705': 'cyan',
            '0.79': 'yellow',
            '1.0': 'blue'
        }
        
        fib_line_styles = {
            '-1.0': '--',
            '-0.62': '--',
            '-0.27': '--',
            '0.0': '-',
            '0.25': '--',
            '0.5': '--',
            '0.618': '-',
            '0.705': '--',
            '0.79': '--',
            '1.0': '-'
        }
        
        for level_name, price in fib_levels.items():
            color = fib_colors.get(level_name, 'gray')
            ls = fib_line_styles.get(level_name, '--')
            lw = 2 if level_name in ['0.0', '0.618', '1.0'] else 1
            ax.hlines(y=price, xmin=dates.iloc[0], xmax=dates.iloc[-1], colors=color,
                     linestyles=ls, linewidth=lw, alpha=0.8)
            
            # Add label on right
            ax.annotate(f'{level_name}', xy=(dates.iloc[-1], price), xytext=(5, 0),
                       textcoords='offset points', fontsize=7, color=color,
                       ha='left', va='center', alpha=0.9)


def draw_candles(ax, df, swing_highs=None, swing_lows=None, liquidity=None, opening_range=None, daily_high_low=None, ifvgs=None, fvgs=None, pivots=None, fibs=None, entry_zone=None):
    import pandas as pd
    
    ax.clear()
    dates = pd.to_datetime(df['date'])
    
    for i, row in df.iterrows():
        date = dates.iloc[i]
        open_price = row['open']
        close_price = row['close']
        high = row['high']
        low = row['low']
        
        if close_price >= open_price:
            color = 'green'
            ax.plot([date, date], [low, high], color=color, linewidth=0.5)
            ax.plot([date, date], [open_price, close_price], color=color, linewidth=2)
        else:
            color = 'red'
            ax.plot([date, date], [low, high], color=color, linewidth=0.5)
            ax.plot([date, date], [open_price, close_price], color=color, linewidth=2)
    
    if swing_highs:
        for sh in swing_highs:
            try:
                date = pd.to_datetime(sh['timestamp'])
                price = sh['price']
                ax.annotate('↓', xy=(date, price), xytext=(0, 15),
                           textcoords='offset points', fontsize=14, color='red', 
                           ha='center', va='bottom', clip_on=True)
            except:
                pass
    
    if swing_lows:
        for sl in swing_lows:
            try:
                date = pd.to_datetime(sl['timestamp'])
                price = sl['price']
                ax.annotate('↑', xy=(date, price), xytext=(0, -15),
                           textcoords='offset points', fontsize=14, color='green', 
                           ha='center', va='top', clip_on=True)
            except:
                pass
    
    # Plot support and resistance levels
    if liquidity:
        # Get date range for horizontal lines
        if len(dates) > 0:
            min_date = dates.iloc[0]
            max_date = dates.iloc[-1]
            # Add some padding to the date range
            from matplotlib.dates import date2num
            date_range = max_date - min_date
            min_date = min_date - date_range * 0.02
            max_date = max_date + date_range * 0.02
            
            # Draw resistance levels (red dashed lines)
            for price in liquidity.get('resistance', []):
                ax.hlines(y=price, xmin=min_date, xmax=max_date, colors='red', 
                         linestyles='--', linewidth=1, alpha=0.7)
            
            # Draw support levels (green dashed lines)
            for price in liquidity.get('support', []):
                ax.hlines(y=price, xmin=min_date, xmax=max_date, colors='green', 
                         linestyles='--', linewidth=1, alpha=0.7)
    
    # Plot Opening Range (yellow shaded area)
    if opening_range:
        or_high = opening_range.get('high')
        or_low = opening_range.get('low')
        if or_high and or_low and len(dates) > 0:
            ax.axhspan(or_low, or_high, alpha=0.2, color='yellow', label='Opening Range')
            ax.hlines(y=or_high, xmin=dates.iloc[0], xmax=dates.iloc[-1], colors='orange', 
                     linestyles='-', linewidth=1.5, label='OR High')
            ax.hlines(y=or_low, xmin=dates.iloc[0], xmax=dates.iloc[-1], colors='orange', 
                     linestyles='-', linewidth=1.5, label='OR Low')
    
    # Plot Daily High/Low (purple lines)
    if daily_high_low:
        dh = daily_high_low.get('high')
        dl = daily_high_low.get('low')
        if dh and dl and len(dates) > 0:
            ax.hlines(y=dh, xmin=dates.iloc[0], xmax=dates.iloc[-1], colors='purple', 
                     linestyles='-', linewidth=2, label='Daily High')
            ax.hlines(y=dl, xmin=dates.iloc[0], xmax=dates.iloc[-1], colors='purple', 
                     linestyles='-', linewidth=2, label='Daily Low')
    
    # Plot Inverse Fair Value Gaps (IFVG) - purple
    if ifvgs and len(dates) > 0:
        for fvg in ifvgs:
            fvg_type = fvg.get('type')
            top = fvg.get('top')
            bottom = fvg.get('bottom')
            mid = fvg.get('mid')
            idx = fvg.get('index', 0)
            
            if top and bottom and idx < len(dates):
                color = 'purple'
                
                # Shade between top and bottom
                if top and bottom:
                    ax.axhspan(bottom, top, alpha=0.25, color=color)
                if top:
                    ax.hlines(y=top, xmin=dates.iloc[0], xmax=dates.iloc[-1], colors=color, 
                            linestyles=':', linewidth=0.8, alpha=0.6)
                if bottom:
                    ax.hlines(y=bottom, xmin=dates.iloc[0], xmax=dates.iloc[-1], colors=color, 
                            linestyles=':', linewidth=0.8, alpha=0.6)
                if mid:
                    ax.hlines(y=mid, xmin=dates.iloc[0], xmax=dates.iloc[-1], colors=color, 
                            linestyles='-', linewidth=1.5, alpha=0.9)
    
    # Plot Unfilled FVGs (green/red)
    if fvgs and len(dates) > 0:
        for fvg in fvgs:
            fvg_type = fvg.get('type')
            top = fvg.get('top')
            bottom = fvg.get('bottom')
            mid = fvg.get('mid')
            idx = fvg.get('index', 0)
            
            if top and bottom and idx < len(dates):
                if fvg_type == 'bullish':
                    color = 'limegreen'
                else:
                    color = 'orangered'
                
                # Shade between top and bottom
                if top and bottom:
                    ax.axhspan(bottom, top, alpha=0.2, color=color)
                if top:
                    ax.hlines(y=top, xmin=dates.iloc[0], xmax=dates.iloc[-1], colors=color, 
                            linestyles=':', linewidth=0.8, alpha=0.5)
                if bottom:
                    ax.hlines(y=bottom, xmin=dates.iloc[0], xmax=dates.iloc[-1], colors=color, 
                            linestyles=':', linewidth=0.8, alpha=0.5)
                if mid:
                    ax.hlines(y=mid, xmin=dates.iloc[0], xmax=dates.iloc[-1], colors=color, 
                            linestyles='-', linewidth=1.5, alpha=0.9)
    
    # Plot Pivot levels (blue)
    if pivots and len(dates) > 0:
        pivot_color = 'blue'
        # Main pivot - solid line
        if pivots.get('pivot'):
            ax.hlines(y=pivots['pivot'], xmin=dates.iloc[0], xmax=dates.iloc[-1], colors=pivot_color, 
                     linestyles='-', linewidth=2, alpha=0.8)
        # R levels - dashed above pivot
        for level in ['r1', 'r2', 'r3']:
            if pivots.get(level):
                ax.hlines(y=pivots[level], xmin=dates.iloc[0], xmax=dates.iloc[-1], colors='red', 
                         linestyles='--', linewidth=1, alpha=0.5)
        # S levels - dashed below pivot
        for level in ['s1', 's2', 's3']:
            if pivots.get(level):
                ax.hlines(y=pivots[level], xmin=dates.iloc[0], xmax=dates.iloc[-1], colors='green', 
                         linestyles='--', linewidth=1, alpha=0.5)
    
    # Add price labels on the right side
    if len(dates) > 0:
        right_edge = dates.iloc[-1]
        price_offsets = []  # Track used y positions to avoid overlap
        
        # Helper to add label if not overlapping
        def add_label(price, text, color, offset_pts=5):
            if price is None:
                return
            ax.annotate(f'{text}: {price}', xy=(right_edge, price), xytext=(offset_pts, 0),
                       textcoords='offset points', fontsize=7, color=color,
                       ha='left', va='center', alpha=0.8)
        
        # Pivot levels
        if pivots:
            add_label(pivots.get('pivot'), 'P', 'blue')
            add_label(pivots.get('r1'), 'R1', 'red')
            add_label(pivots.get('r2'), 'R2', 'red')
            add_label(pivots.get('r3'), 'R3', 'red')
            add_label(pivots.get('s1'), 'S1', 'green')
            add_label(pivots.get('s2'), 'S2', 'green')
            add_label(pivots.get('s3'), 'S3', 'green')
        
        # Daily High/Low
        if daily_high_low:
            add_label(daily_high_low.get('high'), 'DH', 'purple')
            add_label(daily_high_low.get('low'), 'DL', 'purple')
        
        # Opening Range
        if opening_range:
            add_label(opening_range.get('high'), 'ORH', 'orange')
            add_label(opening_range.get('low'), 'ORL', 'orange')
        
        # S/R levels (just first few to avoid clutter)
        if liquidity:
            for i, price in enumerate(liquidity.get('resistance', [])[:3]):
                add_label(price, f'R{i+1}', 'red')
            for i, price in enumerate(liquidity.get('support', [])[:3]):
                add_label(price, f'S{i+1}', 'green')
        
        # Entry zone levels
        if entry_zone and entry_zone.get('all_entries'):
            direction = entry_zone.get('direction', 'bullish')
            label_color = 'green' if direction == 'bullish' else 'red'
            for entry in entry_zone['all_entries'][:5]:
                add_label(entry.get('level'), entry.get('type'), label_color)
    
    # Plot Fibonacci retracement (ICT style)
    if fibs and len(dates) > 0:
        fib_levels = fibs.get('levels', {})
        move_type = fibs.get('move_type', '')
        
        # Key ICT Fibonacci levels to plot
        fib_colors = {
            '0.0': 'gray',
            '23.6': 'gray',
            '38.2': 'cyan',  # Key ICT level
            '50.0': 'gray',
            '61.8': 'cyan',  # Key ICT level
            '78.6': 'gray',
            '100.0': 'gray'
        }
        
        for level_name, price in fib_levels.items():
            color = fib_colors.get(level_name, 'gray')
            lw = 2.0 if level_name in ['38.2', '61.8'] else 0.8
            style = '-' if level_name in ['38.2', '61.8'] else '--'
            ax.hlines(y=price, xmin=dates.iloc[0], xmax=dates.iloc[-1], colors=color,
                     linestyles=style, linewidth=lw, alpha=0.7)
            
            # Add label for key levels
            if level_name in ['38.2', '61.8']:
                ax.annotate(f'F{level_name}', xy=(dates.iloc[-1], price), xytext=(5, 0),
                           textcoords='offset points', fontsize=7, color=color,
                           ha='left', va='center', alpha=0.9)
    
    # Plot Entry Zone (current price + closest entry level)
    if entry_zone and len(dates) > 0:
        current_price = entry_zone.get('current_price')
        closest = entry_zone.get('closest_entry')
        
        if current_price:
            # Plot current price line
            ax.hlines(y=current_price, xmin=dates.iloc[0], xmax=dates.iloc[-1], colors='yellow',
                     linestyles='-', linewidth=2, alpha=0.9)
        
        # Highlight closest entry - put on right side
        if closest:
            entry_price = closest.get('level')
            entry_type = closest.get('type')
            direction = entry_zone.get('direction', 'bullish')
            label_color = 'green' if direction == 'bullish' else 'red'
            ax.annotate(f'{direction.upper()} ENTRY:\n{entry_type} @ {entry_price}', xy=(dates.iloc[-1], entry_price),
                       xytext=(10, 0), textcoords='offset points', fontsize=8, color=label_color,
                       ha='left', va='center', fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.7, edgecolor=label_color),
                       arrowprops=dict(arrowstyle='->', color=label_color, lw=1))
    
    ax.set_xlabel('Date/Time')
    
    ax.set_xlabel('Date/Time')
    ax.set_ylabel('Price')
    ax.set_title(f'{live_symbol} - {live_timeframe} Candlestick Chart (Live - 1s)')
    ax.grid(True, alpha=0.3)
    study_fig.autofmt_xdate()


def schedule_update(prev_df, prev_store):
    global update_id
    update_id = root.after(1000, lambda: update_chart(prev_df, prev_store))


def update_chart(prev_df, prev_store):
    global study_frame, study_fig, study_ax, study_canvas, fib_frame, fib_fig, fib_ax, fib_canvas
    
    if study_frame is None or not study_frame.winfo_exists():
        return
    
    try:
        # Save current zoom/pan limits from study chart
        xlim = study_ax.get_xlim()
        ylim = study_ax.get_ylim()
        
        # Re-fetch historical data to get latest bar
        df = get_historical_data(live_client.ib, live_contract, duration="5 D", bar_size="5 mins")
        
        # Fall back to Yahoo if IB returns empty
        if df.empty:
            try:
                from ib_trading_api.market_data import get_yahoo_historical
                df = get_yahoo_historical(live_symbol, period="5d", interval="5m")
            except:
                pass
        
        if df.empty:
            schedule_update(prev_df, prev_store)
            return
        
        # Re-analyze
        store = load_from_dataframe(df, symbol=live_symbol, timeframe=live_timeframe)
        swing_highs = store.find_swing_highs()
        swing_lows = store.find_swing_lows()
        liquidity = store.find_liquidity_zones()
        opening_range = None
        if hasattr(store, 'find_opening_range'):
            opening_range = store.find_opening_range(minutes=30)
        daily_high_low = None
        if hasattr(store, 'find_daily_high_low'):
            daily_high_low = store.find_daily_high_low()
        ifvgs = store.find_inverse_fvgs()
        fvgs = store.find_unfilled_fvgs()
        pivots = store.find_pivot_levels()
        fibs = store.find_fibonacci_retracement()
        fibs_ext = store.find_extended_fibonacci()
        entry_zone = store.find_entry_zone()
        
        # Redraw study chart
        draw_candles(study_ax, df, swing_highs, swing_lows, liquidity, opening_range, daily_high_low, ifvgs, fvgs, pivots, fibs, entry_zone)
        
        # Redraw fib chart
        draw_fib_chart(fib_ax, df, swing_highs, swing_lows, fibs_ext)
        
        # Restore zoom/pan limits
        study_ax.set_xlim(xlim)
        study_ax.set_ylim(ylim)
        
        study_canvas.draw()
        fib_canvas.draw()
        
        schedule_update(df, store)
        
    except Exception as e:
        output.insert(tk.END, f"Update error: {e}\n")
        schedule_update(prev_df, prev_store)


def save_defaults():
    symbol = symbol_var.get().strip()
    if not symbol:
        messagebox.showwarning("Warning", "Symbol cannot be empty")
        return
    
    response = messagebox.askyesno("Save Defaults", f"Save '{symbol}' as default symbol?")
    if response:
        # Save to file
        import os
        defaults_file = os.path.join(os.path.dirname(__file__), "gui_defaults.txt")
        with open(defaults_file, "w") as f:
            f.write(f"symbol={symbol}\n")
        messagebox.showinfo("Saved", f"Default symbol saved as '{symbol}'")


def load_defaults():
    import os
    defaults_file = os.path.join(os.path.dirname(__file__), "gui_defaults.txt")
    if os.path.exists(defaults_file):
        with open(defaults_file, "r") as f:
            for line in f:
                if line.startswith("symbol="):
                    return line.split("=", 1)[1].strip()
    return "ES"


# ----- GUI layout -----
root = tk.Tk()
root.title("IB Trading API - ICT Analyzer (Live)")
root.geometry("1000x700")

# Top frame for symbol input
top_frame = ttk.Frame(root, padding="5")
top_frame.pack(fill=tk.X)

symbol_var = tk.StringVar(value=load_defaults())

ttk.Label(top_frame, text="Symbol:").pack(side=tk.LEFT, padx=5)
ttk.Entry(top_frame, width=12, textvariable=symbol_var).pack(side=tk.LEFT, padx=5)
ttk.Button(top_frame, text="Fetch & Analyze (Live)", command=fetch_and_analyze).pack(side=tk.LEFT, padx=5)
ttk.Button(top_frame, text="Save Defaults", command=save_defaults).pack(side=tk.LEFT, padx=5)

# Notebook for tabs
notebook = ttk.Notebook(root)
notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

# Info tab
info_tab = ttk.Frame(notebook)
notebook.add(info_tab, text="Info")

output = scrolledtext.ScrolledText(info_tab, wrap=tk.WORD)
output.pack(fill=tk.BOTH, expand=True)

# Study Chart tab (main candlestick chart with ICT analysis)
study_tab = ttk.Frame(notebook)
notebook.add(study_tab, text="Study Chart")

# Placeholder text in study tab
ttk.Label(study_tab, text="Click Fetch to load chart", font=("Arial", 14)).pack(expand=True)

# Fib Chart tab (Fibonacci extension chart)
fib_tab = ttk.Frame(notebook)
notebook.add(fib_tab, text="Fib Chart")

# Placeholder text in fib tab
ttk.Label(fib_tab, text="Click Fetch to load chart", font=("Arial", 14)).pack(expand=True)

# Bottom frame for close button
bottom_frame = ttk.Frame(root, padding="5")
bottom_frame.pack(fill=tk.X)

def on_close():
    global update_id, live_client
    if update_id:
        root.after_cancel(update_id)
    if live_client and live_client.is_connected:
        live_client.disconnect()
        live_client.ib = None
    root.destroy()


ttk.Button(bottom_frame, text="Close", command=on_close).pack()

root.mainloop()
