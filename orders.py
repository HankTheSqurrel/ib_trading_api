from typing import Optional, Union
from ib_insync import IB, Contract, Order, MarketOrder, LimitOrder, StopOrder, StopLimitOrder

def place_market_order(
    ib: IB,
    contract: Contract,
    action: str,  # "BUY" or "SELL"
    quantity: int,
    outside_rth: bool = False
) -> Order:
    """
    Place a market order.
    
    Args:
        ib: IB instance
        contract: Contract to trade
        action: "BUY" or "SELL"
        quantity: Number of contracts/shares
        outside_rth: Allow outside regular trading hours
    
    Returns:
        Order object
    """
    order = MarketOrder(action, quantity, outsideRth=outside_rth)
    trade = ib.placeOrder(contract, order)
    return trade.order

def place_limit_order(
    ib: IB,
    contract: Contract,
    action: str,
    quantity: int,
    limit_price: float,
    outside_rth: bool = False
) -> Order:
    """
    Place a limit order.
    
    Args:
        ib: IB instance
        contract: Contract to trade
        action: "BUY" or "SELL"
        quantity: Number of contracts/shares
        limit_price: Limit price
        outside_rth: Allow outside regular trading hours
    """
    order = LimitOrder(action, quantity, limit_price, outsideRth=outside_rth)
    trade = ib.placeOrder(contract, order)
    return trade.order

def place_stop_order(
    ib: IB,
    contract: Contract,
    action: str,
    quantity: int,
    stop_price: float,
    outside_rth: bool = False
) -> Order:
    """
    Place a stop (market) order.
    
    Args:
        ib: IB instance
        contract: Contract to trade
        action: "BUY" or "SELL"
        quantity: Number of contracts/shares
        stop_price: Stop price
        outside_rth: Allow outside regular trading hours
    """
    order = StopOrder(action, quantity, stop_price, outsideRth=outside_rth)
    trade = ib.placeOrder(contract, order)
    return trade.order

def place_stop_limit_order(
    ib: IB,
    contract: Contract,
    action: str,
    quantity: int,
    limit_price: float,
    stop_price: float,
    outside_rth: bool = False
) -> Order:
    """
    Place a stop-limit order.
    
    Args:
        ib: IB instance
        contract: Contract to trade
        action: "BUY" or "SELL"
        quantity: Number of contracts/shares
        limit_price: Limit price
        stop_price: Stop price
        outside_rth: Allow outside regular trading hours
    """
    order = StopLimitOrder(action, quantity, limit_price, stop_price, outsideRth=outside_rth)
    trade = ib.placeOrder(contract, order)
    return trade.order

def cancel_order(ib: IB, order: Order) -> bool:
    """
    Cancel an order.
    
    Args:
        ib: IB instance
        order: Order to cancel
    
    Returns:
        True if cancellation was successful
    """
    try:
        ib.cancelOrder(order)
        return True
    except Exception as e:
        print(f"Failed to cancel order: {e}")
        return False

def get_open_orders(ib: IB) -> list:
    """Get all open orders"""
    return ib.orders()

def get_order_status(ib: IB, order_id: int) -> dict:
    """Get status of a specific order"""
    for order in ib.openOrders():
        if order.orderId == order_id:
            return {
                "order_id": order.orderId,
                "status": order.status,
                "action": order.action,
                "quantity": order.totalQuantity,
                "filled": order.filled,
                "remaining": order.remaining,
                "avg_fill_price": order.avgFillPrice
            }
    return {"error": "Order not found"}
