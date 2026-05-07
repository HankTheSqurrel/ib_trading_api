"""
Example usage of IB Trading API

Before running:
1. Install requirements: pip install -r requirements.txt
2. Start IB Gateway or TWS
3. Enable paper trading in Account Management
"""

from ib_trading_api import (
    IBClient, IBConfig,
    get_account_summary, get_positions, get_pnl,
    place_market_order, place_limit_order,
    get_realtime_quote, get_historical_data
)
from ib_insync import Contract, Stock, Future

def main():
    # Configure connection (paper trading uses same port)
    config = IBConfig(
        host="127.0.0.1",
        port=4001,  # 4001 for Gateway, 7496 for TWS
        client_id=1
    )
    
    # Create client and connect
    client = IBClient(config)
    
    if not client.connect_sync():
        print("Failed to connect. Is IB Gateway/TWS running?")
        return
    
    print("Connected successfully!")
    
    # Get account info
    print("\n=== Account Summary ===")
    account = get_account_summary(client.ib)
    print(f"Net Liquidation: ${account.get('NetLiquidation', 'N/A')}")
    print(f"Buying Power: ${account.get('BuyingPower', 'N/A')}")
    print(f"Cash Balance: ${account.get('CashBalance', 'N/A')}")
    
    # Get positions
    print("\n=== Positions ===")
    positions = get_positions(client.ib)
    for pos in positions:
        print(f"  {pos['symbol']}: {pos['position']} @ ${pos['avg_cost']}")
    
    # Get P&L
    print("\n=== P&L ===")
    pnl = get_pnl(client.ib)
    print(f"Today's P&L: ${pnl['today_pnl']}")
    print(f"Unrealized P&L: ${pnl['unrealized_pnl']}")
    print(f"Realized P&L: ${pnl['realized_pnl']}")
    
    # === Trading Examples ===
    
    # Example 1: Get quote for MES (Micro E-mini S&P 500)
    print("\n=== MES Quote ===")
    mes_contract = client.create_contract(
        symbol="MES",
        sec_type="FUT",
        exchange="CME",
        currency="USD",
        expiry="202606"  # June 2026
    )
    mes_quote = get_realtime_quote(client.ib, mes_contract)
    print(f"MES Bid: {mes_quote['bid']}, Ask: {mes_quote['ask']}")
    
    # Example 2: Get historical data
    print("\n=== MES Historical (last day, 5min bars) ===")
    bars = get_historical_data(
        client.ib, mes_contract,
        duration="1 D",
        bar_size="5 mins"
    )
    print(bars.tail())
    
    # Example 3: Place a market order (paper trading)
    print("\n=== Placing Order ===")
    # Note: Uncomment to actually trade
    # order = place_market_order(client.ib, mes_contract, "BUY", 1)
    # print(f"Order placed: {order.orderId}")
    
    # Disconnect
    client.disconnect()
    print("\nDisconnected.")


if __name__ == "__main__":
    main()
