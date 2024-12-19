# distributionmarkets/core/events.py

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime

@dataclass
class Event:
    """Base class for all events in the system."""
    name: str
    params: Dict[str, Any]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class EventLog:
    """Maintains a log of all events in the system."""
    def __init__(self):
        self._events: List[Event] = []
    
    def emit(self, event: Event):
        """Add an event to the log."""
        self._events.append(event)
    
    def get_events(self, event_name: Optional[str] = None) -> List[Event]:
        """
        Retrieve events from the log.
        If event_name is provided, only returns events with that name.
        """
        if event_name is None:
            return self._events.copy()
        return [e for e in self._events if e.name == event_name]
    
    def clear(self):
        """Clear all events from the log."""
        self._events = []

# Common event factories
def create_trade_event(user: str, from_mu: float, from_sigma: float, 
                      to_mu: float, to_sigma: float, collateral: float) -> Event:
    return Event(
        name="Trade",
        params={
            "user": user,
            "from_mu": from_mu,
            "from_sigma": from_sigma,
            "to_mu": to_mu,
            "to_sigma": to_sigma,
            "collateral": collateral
        }
    )

def create_deposit_event(user: str, amount: float) -> Event:
    return Event(
        name="Deposit",
        params={
            "user": user,
            "amount": amount
        }
    )

def create_withdrawal_event(user: str, amount: float) -> Event:
    return Event(
        name="Withdrawal",
        params={
            "user": user,
            "amount": amount
        }
    )

def create_market_finalized_event(final_value: float) -> Event:
    return Event(
        name="MarketFinalized",
        params={
            "final_value": final_value
        }
    )

def create_position_settled_event(user: str, payout: float) -> Event:
    return Event(
        name="PositionSettled",
        params={
            "user": user,
            "payout": payout
        }
    )