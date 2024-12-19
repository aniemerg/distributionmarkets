# distributionmarkets/core/ledger.py

from decimal import Decimal
from typing import Dict, Optional
from .events import EventLog, create_deposit_event, create_withdrawal_event, Event

class InsufficientBalanceError(Exception):
    """Raised when an address has insufficient balance for a transfer."""
    pass

class Ledger:
    """
    Simple token-like ledger system. Similar to an ERC-20 but without approvals.
    Balances are tracked in dollars (or other base currency unit).
    """
    def __init__(self, event_log: EventLog):
        self._balances: Dict[str, Decimal] = {}
        self._event_log = event_log
        self._total_supply: Decimal = Decimal('0')

    def balance_of(self, address: str) -> Decimal:
        """Get the balance of an address."""
        return self._balances.get(address, Decimal('0'))

    def total_supply(self) -> Decimal:
        """Get total supply of tokens in the system."""
        return self._total_supply

    def mint(self, to_address: str, amount: Decimal) -> bool:
        """
        Create new tokens and assign them to an address.
        Similar to depositing new funds into the system.
        """
        if amount <= 0:
            raise ValueError("Mint amount must be positive")
        
        current_balance = self.balance_of(to_address)
        self._balances[to_address] = current_balance + amount
        self._total_supply += amount
        
        self._event_log.emit(Event(
            name="Mint",
            params={
                "to": to_address,
                "amount": float(amount)
            }
        ))
        return True

    def burn(self, from_address: str, amount: Decimal) -> bool:
        """
        Destroy tokens from an address.
        Similar to withdrawing funds from the system.
        """
        if amount <= 0:
            raise ValueError("Burn amount must be positive")
        
        current_balance = self.balance_of(from_address)
        if current_balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient balance: {current_balance} < {amount}")
        
        self._balances[from_address] = current_balance - amount
        self._total_supply -= amount
        
        self._event_log.emit(Event(
            name="Burn",
            params={
                "from": from_address,
                "amount": float(amount)
            }
        ))
        return True

    def transfer(self, from_address: str, to_address: str, amount: Decimal) -> bool:
        """
        Transfer tokens from one address to another.
        """
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")
        
        if from_address == to_address:
            return True  # No-op transfer
        
        from_balance = self.balance_of(from_address)
        if from_balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient balance: {from_balance} < {amount}")
        
        to_balance = self.balance_of(to_address)
        
        self._balances[from_address] = from_balance - amount
        self._balances[to_address] = to_balance + amount
        
        self._event_log.emit(Event(
            name="Transfer",
            params={
                "from": from_address,
                "to": to_address,
                "amount": float(amount)
            }
        ))
        return True