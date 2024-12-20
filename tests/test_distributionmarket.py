import pytest
from decimal import Decimal
from typing import Dict
from distributionmarkets.core.events import EventLog
from distributionmarkets.core.ledger import Ledger
from distributionmarkets.core.marketmath import calculate_lambda, calculate_f 
from distributionmarkets.core.distributionmarket import DistributionMarket

@pytest.fixture
def event_log():
    return EventLog()

@pytest.fixture
def ledger(event_log):
    return Ledger(event_log)

@pytest.fixture
def market(ledger, event_log):
    return DistributionMarket(ledger, event_log)

@pytest.fixture
def market_params():
    return {
        "lp_address": "lp_1",
        "initial_mean": 100.0,
        "initial_std_dev": 10.0,
        "initial_backing": Decimal('1000')
    }

@pytest.fixture
def funded_ledger(ledger, market_params):
    """Setup ledger with initial funds for LP"""
    ledger.mint(market_params["lp_address"], market_params["initial_backing"])
    return ledger

def test_initialize_market(market, market_params, funded_ledger):
    """Test initial LP providing liquidity to create market"""
    # Check initial balances
    initial_lp_balance = funded_ledger.balance_of(market_params["lp_address"])
    initial_market_balance = funded_ledger.balance_of(market.address)
    assert initial_lp_balance == market_params["initial_backing"]
    assert initial_market_balance == 0

    # Initialize market with LP position
    result = market.initialize_market(
        initial_mean=market_params["initial_mean"],
        initial_std_dev=market_params["initial_std_dev"],
        initial_backing=market_params["initial_backing"],
        lp_address=market_params["lp_address"]
    )
    
    # Unpack results
    position_id = result["position_id"]
    
    # Test market state initialization
    assert market.current_mean == market_params["initial_mean"]
    assert market.current_std_dev == market_params["initial_std_dev"]
    assert market.total_backing == market_params["initial_backing"]
    
    # Test LP token creation
    assert market.balanceOf(market_params["lp_address"]) == market_params["initial_backing"]
    assert market.total_lp_tokens() == market_params["initial_backing"]
    
    # Test LP trader position
    position = market.get_position(position_id)
    assert position is not None
    assert position["owner"] == market_params["lp_address"]
    assert position["mean"] == market_params["initial_mean"]
    assert position["std_dev"] == market_params["initial_std_dev"]
    
    # Test ledger balances after initialization
    assert funded_ledger.balance_of(market_params["lp_address"]) == 0
    assert funded_ledger.balance_of(market.address) == market_params["initial_backing"]
    
    # Test event emission
    events = market.event_log.get_events()
    assert any(
        e.name == "MarketInitialized" and
        e.params["position_id"] == position_id
        for e in events
    )

def test_initialize_market_twice(market, market_params, funded_ledger):
    """Test that market can't be initialized twice"""
    # First initialization
    market.initialize_market(
        initial_mean=market_params["initial_mean"],
        initial_std_dev=market_params["initial_std_dev"],
        initial_backing=market_params["initial_backing"],
        lp_address=market_params["lp_address"]
    )
    
    # Fund second LP
    funded_ledger.mint("lp_2", Decimal('500'))
    
    # Second initialization should fail
    with pytest.raises(ValueError):
        market.initialize_market(
            initial_mean=95.0,
            initial_std_dev=12.0,
            initial_backing=Decimal('500'),
            lp_address="lp_2"
        )

def test_settlement_after_initialization(market, market_params, funded_ledger):
    """Test market settlement with just initial LP position"""
    # Initialize market
    result = market.initialize_market(
        initial_mean=market_params["initial_mean"],
        initial_std_dev=market_params["initial_std_dev"],
        initial_backing=market_params["initial_backing"],
        lp_address=market_params["lp_address"]
    )
    
    position_id = result["position_id"]
    initial_market_balance = funded_ledger.balance_of(market.address)
    
    # Settle market
    final_value = 105.0
    market.settle_market(final_value)
    
    # Test trader position settlement
    initial_lp_balance = funded_ledger.balance_of(market_params["lp_address"])
    settlement = market.settle_trader_position(position_id)
    assert settlement["recipient"] == market_params["lp_address"]
    
    # Check LP balance increased after trader position settlement
    new_lp_balance = funded_ledger.balance_of(market_params["lp_address"])
    assert new_lp_balance > initial_lp_balance
    
    # Test LP position settlement
    initial_lp_token_balance = market.balanceOf(market_params["lp_address"])
    lp_settlement = market.settle_lp_position(market_params["lp_address"])
    
    # Check LP token balance is now 0
    assert market.balanceOf(market_params["lp_address"]) == 0
    
    # Check final ledger balances
    final_lp_balance = funded_ledger.balance_of(market_params["lp_address"])
    final_market_balance = funded_ledger.balance_of(market.address)
    assert final_lp_balance > new_lp_balance  # LP got more funds from LP position
    assert final_market_balance < initial_market_balance  # Market paid out funds

    # Test events
    events = market.event_log.get_events()
    assert any(
        e.name == "MarketSettled" and
        e.params["final_value"] == final_value
        for e in events
    )
    assert any(
        e.name == "PositionSettled" and
        e.params["position_id"] == position_id
        for e in events
    )