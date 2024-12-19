# distributionmarkets/tests/test_events.py

import pytest
from datetime import datetime
from distributionmarkets.core.events import Event, EventLog, create_trade_event, create_deposit_event

def test_event_creation():
    """Test basic event creation."""
    event = Event("TestEvent", {"param1": "value1"})
    assert event.name == "TestEvent"
    assert event.params["param1"] == "value1"
    assert isinstance(event.timestamp, datetime)

def test_event_log():
    """Test EventLog basic functionality."""
    log = EventLog()
    event1 = Event("Event1", {"param1": "value1"})
    event2 = Event("Event2", {"param2": "value2"})
    
    log.emit(event1)
    log.emit(event2)
    
    events = log.get_events()
    assert len(events) == 2
    assert events[0].name == "Event1"
    assert events[1].name == "Event2"

def test_event_filtering():
    """Test filtering events by name."""
    log = EventLog()
    log.emit(Event("TypeA", {"value": 1}))
    log.emit(Event("TypeB", {"value": 2}))
    log.emit(Event("TypeA", {"value": 3}))
    
    type_a_events = log.get_events("TypeA")
    assert len(type_a_events) == 2
    assert all(e.name == "TypeA" for e in type_a_events)

def test_trade_event_creation():
    """Test trade event factory function."""
    event = create_trade_event(
        user="trader1",
        from_mu=95.0,
        from_sigma=10.0,
        to_mu=100.0,
        to_sigma=10.0,
        collateral=0.07
    )
    
    assert event.name == "Trade"
    assert event.params["user"] == "trader1"
    assert event.params["from_mu"] == 95.0
    assert event.params["to_mu"] == 100.0
    assert event.params["collateral"] == 0.07

def test_deposit_event_creation():
    """Test deposit event factory function."""
    event = create_deposit_event("user1", 100.0)
    
    assert event.name == "Deposit"
    assert event.params["user"] == "user1"
    assert event.params["amount"] == 100.0

def test_event_log_clear():
    """Test clearing the event log."""
    log = EventLog()
    log.emit(Event("Event1", {"param1": "value1"}))
    log.emit(Event("Event2", {"param2": "value2"}))
    
    assert len(log.get_events()) == 2
    log.clear()
    assert len(log.get_events()) == 0