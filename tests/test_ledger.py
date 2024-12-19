# distributionmarkets/tests/test_balance.py

import pytest
from decimal import Decimal
from distributionmarkets.core.ledger import Ledger, InsufficientBalanceError
from distributionmarkets.core.events import EventLog

@pytest.fixture
def ledger():
    return Ledger(EventLog())

def test_initial_state(ledger):
    """Test initial ledger state."""
    assert ledger.balance_of("User A") == Decimal('0')
    assert ledger.total_supply() == Decimal('0')

def test_mint(ledger):
    """Test minting new tokens."""
    ledger.mint("User A", Decimal('100'))
    assert ledger.balance_of("User A") == Decimal('100')
    assert ledger.total_supply() == Decimal('100')

def test_burn(ledger):
    """Test burning tokens."""
    ledger.mint("User A", Decimal('100'))
    ledger.burn("User A", Decimal('30'))
    assert ledger.balance_of("User A") == Decimal('70')
    assert ledger.total_supply() == Decimal('70')

def test_transfer(ledger):
    """Test transferring tokens between addresses."""
    ledger.mint("User A", Decimal('100'))
    ledger.transfer("User A", "User B", Decimal('30'))
    
    assert ledger.balance_of("User A") == Decimal('70')
    assert ledger.balance_of("User B") == Decimal('30')
    assert ledger.total_supply() == Decimal('100')

def test_insufficient_balance_transfer(ledger):
    """Test insufficient balance handling in transfers."""
    ledger.mint("User A", Decimal('50'))
    
    with pytest.raises(InsufficientBalanceError):
        ledger.transfer("User A", "User B", Decimal('60'))

def test_insufficient_balance_burn(ledger):
    """Test insufficient balance handling in burns."""
    ledger.mint("User A", Decimal('50'))
    
    with pytest.raises(InsufficientBalanceError):
        ledger.burn("User A", Decimal('60'))

def test_event_emission(ledger):
    """Test that events are properly emitted."""
    event_log = ledger._event_log
    
    ledger.mint("User A", Decimal('100'))
    ledger.transfer("User A", "User B", Decimal('30'))
    ledger.burn("User A", Decimal('20'))
    
    events = event_log.get_events()
    assert len(events) == 3
    
    mint_event = events[0]
    assert mint_event.name == "Mint"
    assert mint_event.params["to"] == "User A"
    assert mint_event.params["amount"] == 100.0
    
    transfer_event = events[1]
    assert transfer_event.name == "Transfer"
    assert transfer_event.params["from"] == "User A"
    assert transfer_event.params["to"] == "User B"
    assert transfer_event.params["amount"] == 30.0
    
    burn_event = events[2]
    assert burn_event.name == "Burn"
    assert burn_event.params["from"] == "User A"
    assert burn_event.params["amount"] == 20.0