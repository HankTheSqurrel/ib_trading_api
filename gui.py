"""
Simple Tkinter GUI for the IB Trading API and ICT analysis.

Features:
- Enter symbol, contract type, exchange, expiry, and timeframe.
- Fetch historical data (5 days, 5‑minute bars) via IB.
- Build a CandleStore and run ICT analysis.
- Display a summary in a scrollable text box.

Run with:
    python gui.py
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# IB imports (ensure ib_insync is installed)
from ib_trading_api import IBClient, get_historical_data, get_delayed_quote
from ib_trading_api.candles import load_from_dataframe, create_store
from ib_insync import Future


def fetch_and_analyze():
    try:
        # Gather user input
        symbol = symbol_var.get().strip()
        sec_type = sec_type_var.get().strip()
        exchange = exchange_var.get().strip()
        expiry = expiry_var.get().strip()
        timeframe = timeframe_var.get().strip()
        
        # Connect to IB (assumes TWS/Gateway is running)
        client = IBClient()
        if not client.connect_sync():
            output.insert(tk.END, "Failed to connect to IB.\n")
            return
        
        # Build contract
        if sec_type.upper() == "FUT":
            # For futures, let IB pick the nearest contract if an expiry is not provided
        contract = client.create_contract(symbol, "FUT", exchange, "USD", expiry if expiry else None)
        else:
            contract = client.create_contract(symbol, sec_type.upper(), exchange)
        
        # Get historical data (5 days, 5‑minute bars)
        df = get_historical_data(client.ib, contract, duration="5 D", bar_size="5 mins")
        client.disconnect()
        
        if df.empty:
            output.insert(tk.END, "No historical data returned.\n")
            return
        
        # Load into CandleStore and run analysis
        store = load_from_dataframe(df, symbol=symbol, timeframe=timeframe)
        summary = store.get_summary()
        
        # Display summary
        output.insert(tk.END, f"--- Summary for {symbol} ({timeframe}) ---\n")
        for k, v in summary.items():
            output.insert(tk.END, f"{k}: {v}\n")
        output.insert(tk.END, "\nSwing Highs:\n")
        for sh in store.find_swing_highs():
            output.insert(tk.END, f"  {sh['timestamp']} – {sh['price']}\n")
        output.insert(tk.END, "\nSwing Lows:\n")
        for sl in store.find_swing_lows():
            output.insert(tk.END, f"  {sl['timestamp']} – {sl['price']}\n")
        output.insert(tk.END, "\nFair Value Gaps:\n")
        for fvg in store.find_fair_value_gaps():
            output.insert(tk.END, f"  {fvg['type']} gap at {fvg['mid']:.2f} (size {fvg['size']:.2f})\n")
        output.insert(tk.END, "\nLiquidity Zones (Support/Resistance):\n")
        zones = store.find_liquidity_zones()
        output.insert(tk.END, f"  Support: {zones['support']}\n")
        output.insert(tk.END, f"  Resistance: {zones['resistance']}\n")
    except Exception as e:
        messagebox.showerror("Error", str(e))

# ----- GUI layout -----
root = tk.Tk()
root.title("IB Trading API – ICT Analyzer")

mainframe = ttk.Frame(root, padding="10")
mainframe.grid(row=0, column=0, sticky=(tk.N, tk.W, tk.E, tk.S))

# Input fields
symbol_var = tk.StringVar(value="MES")
sec_type_var = tk.StringVar(value="FUT")
exchange_var = tk.StringVar(value="CME")
expiry_var = tk.StringVar(value="")
timeframe_var = tk.StringVar(value="5m")

ttk.Label(mainframe, text="Symbol:").grid(row=0, column=0, sticky=tk.W)
ttk.Entry(mainframe, width=12, textvariable=symbol_var).grid(row=0, column=1, sticky=(tk.W, tk.E))

ttk.Label(mainframe, text="Sec Type:").grid(row=1, column=0, sticky=tk.W)
ttk.Entry(mainframe, width=12, textvariable=sec_type_var).grid(row=1, column=1, sticky=(tk.W, tk.E))

ttk.Label(mainframe, text="Exchange:").grid(row=2, column=0, sticky=tk.W)
ttk.Entry(mainframe, width=12, textvariable=exchange_var).grid(row=2, column=1, sticky=(tk.W, tk.E))

ttk.Label(mainframe, text="Expiry (YYYYMM):").grid(row=3, column=0, sticky=tk.W)
ttk.Entry(mainframe, width=12, textvariable=expiry_var).grid(row=3, column=1, sticky=(tk.W, tk.E))

ttk.Label(mainframe, text="Timeframe:").grid(row=4, column=0, sticky=tk.W)
ttk.Entry(mainframe, width=12, textvariable=timeframe_var).grid(row=4, column=1, sticky=(tk.W, tk.E))

# Action button
ttk.Button(mainframe, text="Fetch & Analyze", command=fetch_and_analyze).grid(row=5, column=0, columnspan=2, pady=10)

# Output area
output = scrolledtext.ScrolledText(mainframe, width=80, height=20, wrap=tk.WORD)
output.grid(row=6, column=0, columnspan=2, pady=5)

# Start GUI loop
root.mainloop()
