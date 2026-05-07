# IB Trading API

Python API for Interactive Brokers paper trading.

## Setup

### 1. Install Dependencies
```bash
pip install ib_insync pandas
```

### 2. Start IB Gateway or TWS
- Download from IB website
- Log in to your IBKR account
- Enable paper trading: Account Settings → Paper Trading → "Enable Paper Trading"
- Start Gateway (recommended) or TWS

### 3. Configure Connection
- Gateway: host 127.0.0.1, port 4001 (or 4002 for secure)
- TWS: host 127.0.0.1, port 7496 (or 7497 for secure)

## Quick Start

```python
from ib_trading_api import IBClient, IBConfig, get_account_summary

config = IBConfig(host="127.0.0.1", port=4001)
client = IBClient(config)
client.connect_sync()

account = get_account_summary(client.ib)
print(f"Balance: ${account['NetLiquidation']}")

client.disconnect()
```

## Trading Example

```python
from ib_trading_api import IBClient, place_market_order, get_realtime_quote

client = IBClient()
client.connect_sync()

# Create MES futures contract
mes = client.create_contract(
    symbol="MES",
    sec_type="FUT",
    exchange="CME",
    currency="USD",
    expiry="202606"
)

# Get quote
quote = get_realtime_quote(client.ib, mes)
print(f"MES: {quote['bid']} / {quote['ask']}")

# Place order (1 lot)
order = place_market_order(client.ib, mes, "BUY", 1)
print(f"Order ID: {order.orderId}")

client.disconnect()
```

## Run Example
```bash
cd ib_trading_api
pip install -r requirements.txt
python example.py
```