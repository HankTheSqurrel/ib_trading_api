from dataclasses import dataclass
from typing import Optional, Dict, Any
from ib_insync import IB, Stock, Future, Option, Forex, Contract

@dataclass
class IBConfig:
    """Configuration for IB connection"""
    host: str = "127.0.0.1"
    port: int = 4001  # 4001 for Gateway, 7496 for TWS
    client_id: int = 1

class IBClient:
    """Client for Interactive Brokers API"""
    
    def __init__(self, config: Optional[IBConfig] = None):
        self.config = config or IBConfig()
        self.ib: Optional[IB] = None
        self._connected = False
    
    async def connect(self) -> bool:
        """Connect to IB Gateway/TWS asynchronously"""
        self.ib = IB()
        try:
            await self.ib.connectAsync(
                host=self.config.host,
                port=self.config.port,
                clientId=self.config.client_id,
                timeout=10
            )
            self._connected = True
            print(f"Connected to IB at {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            self._connected = False
            return False
    
    def connect_sync(self, timeout: int = 10) -> bool:
        """Synchronous connect"""
        self.ib = IB()
        try:
            self.ib.connect(
                host=self.config.host,
                port=self.config.port,
                clientId=self.config.client_id,
                timeout=timeout
            )
            self._connected = True
            print(f"Connected to IB at {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            self._connected = False
            return False
    
    def disconnect(self):
        """Disconnect from IB"""
        if self.ib and self.ib.isConnected():
            self.ib.disconnect()
        self._connected = False
        print("Disconnected from IB")
    
    @property
    def is_connected(self) -> bool:
        return self._connected and self.ib and self.ib.isConnected()
    
    def get_account(self) -> Dict[str, Any]:
        """Get account summary"""
        if not self.is_connected:
            raise ConnectionError("Not connected to IB")
        account_values = self.ib.accountSummary()
        result = {}
        for av in account_values:
            result[av.tag] = av.value
        return result
    
    def get_balance(self) -> float:
        """Get net liquidation value (total equity)"""
        account = self.get_account()
        return float(account.get("NetLiquidation", 0))
    
    def get_buying_power(self) -> float:
        """Get buying power"""
        account = self.get_account()
        return float(account.get("BuyingPower", 0))
    
    def create_contract(
        self,
        symbol: str,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        expiry: Optional[str] = None,
        strike: Optional[float] = None,
        right: Optional[str] = None
    ) -> Contract:
        """
        Create an IB contract for trading.
        
        Examples:
            # Stock
            create_contract("AAPL", "STK")
            
            # MES Futures
            create_contract("MES", "FUT", "CME", expiry="202606")
            
            # Forex
            create_contract("EUR", "FOREX", "IDEALPRO")
            
            # Options
            create_contract("AAPL", "OPT", strike=150.0, right="C")
        """
        if sec_type == "STK":
            contract = Stock(symbol, exchange, currency)
        elif sec_type == "FUT":
            contract = Future(symbol, exchange, currency, expiry)
        elif sec_type == "OPT":
            contract = Option(symbol, expiry, strike, right, exchange, currency)
        elif sec_type == "FOREX":
            contract = Forex(symbol, exchange, currency)
        else:
            raise ValueError(f"Unsupported security type: {sec_type}")
        return contract


# Convenience function for quick connection
_default_client: Optional[IBClient] = None

def get_client(config: Optional[IBConfig] = None) -> IBClient:
    """Get or create default client instance"""
    global _default_client
    if config:
        _default_client = IBClient(config)
    elif not _default_client:
        _default_client = IBClient()
    return _default_client


if __name__ == "__main__":
    # Quick test
    client = IBClient()
    if client.connect_sync():
        print("Account:", client.get_account())
        client.disconnect()
