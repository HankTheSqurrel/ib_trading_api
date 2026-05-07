from typing import Dict, Any, List
from ib_insync import IB

def get_account_summary(ib: IB, account: str = "") -> Dict[str, Any]:
    """
    Get account summary values.
    
    Args:
        ib: IB instance
        account: Account ID (empty for default)
    
    Returns:
        Dict of account values
    """
    values = ib.accountSummary(account)
    return {v.tag: v.value for v in values}

def get_positions(ib: IB, account: str = "") -> List[Dict[str, Any]]:
    """
    Get current positions.
    
    Args:
        ib: IB instance
        account: Account ID (empty for default)
    
    Returns:
        List of position dicts
    """
    positions = ib.positions(account)
    
    return [{
        "symbol": p.contract.symbol,
        "sec_type": p.contract.secType,
        "exchange": p.contract.exchange,
        "currency": p.contract.currency,
        "expiry": p.contract.lastTradeDateOrContractMonth,
        "position": p.position,
        "avg_cost": p.avgCost,
        "market_value": p.marketValue,
        "unrealized_pnl": p.unrealizedPNL,
        "realized_pnl": p.realizedPNL
    } for p in positions]

def get_pnl(ib: IB, account: str = "") -> Dict[str, float]:
    """
    Get daily P&L.
    
    Args:
        ib: IB instance
        account: Account ID (empty for default)
    
    Returns:
        Dict with today_pnl, unrealized_pnl, realized_pnl
    """
    values = ib.accountSummary(account, "DailyPnL")
    
    result = {
        "today_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "realized_pnl": 0.0
    }
    
    for v in values:
        if v.tag == "DailyPnL":
            result["today_pnl"] = float(v.value)
        elif v.tag == "UnrealizedPnL":
            result["unrealized_pnl"] = float(v.value)
        elif v.tag == "RealizedPnL":
            result["realized_pnl"] = float(v.value)
    
    return result

def get_pnl_by_symbol(ib: IB, contract) -> Dict[str, float]:
    """
    Get P&L for a specific contract.
    
    Args:
        ib: IB instance
        contract: Contract to get P&L for
    
    Returns:
        Dict with unrealized/realized P&L for the contract
    """
    from ib_insync import PnL
    
    # Get PnL for the contract
    pnl_obj = ib.pnl(contract)
    
    return {
        "unrealized_pnl": pnl_obj.unrealizedPNL,
        "realized_pnl": pnl_obj.realizedPNL,
        "daily_pnl": pnl_obj.dailyPNL
    }

def get_portfolio_value(ib: IB) -> float:
    """Get total portfolio value"""
    account = get_account_summary(ib)
    return float(account.get("NetLiquidation", 0))

def get_cash_balance(ib: IB) -> float:
    """Get cash balance"""
    account = get_account_summary(ib)
    return float(account.get("CashBalance", 0))
