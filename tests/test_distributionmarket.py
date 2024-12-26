import pytest
from decimal import Decimal
from typing import Dict
from distributionmarkets.core.events import EventLog
from distributionmarkets.core.ledger import Ledger
from distributionmarkets.core.marketmath import calculate_lambda, calculate_f 
from distributionmarkets.core.distributionmarket import DistributionMarket
import numpy as np

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
        "initial_mean": 95.0,
        "initial_std_dev": 10.0,
        "initial_backing": Decimal('50'),
        "initial_k": 210.5026039569057
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
        initial_k=market_params["initial_k"],
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
        initial_k=market_params["initial_k"],
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
            initial_k=market_params["initial_k"],
            lp_address="lp_2"
        )

# desmos: https://www.desmos.com/calculator/5xquurzbwe
def test_settlement_after_initialization(market, market_params, funded_ledger):
    """Test market settlement with just initial LP position"""
    # Initialize market
    result = market.initialize_market(
        initial_mean=market_params["initial_mean"],
        initial_std_dev=market_params["initial_std_dev"],
        initial_backing=market_params["initial_backing"],
        initial_k=market_params["initial_k"],
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

    # Check that LP has received all funds back
    assert abs(settlement["amount"] + lp_settlement["amount"] - market_params["initial_backing"]) < 0.001
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

def test_trade_after_lp(market, market_params, funded_ledger):
    """Test trade execution after initial LP"""
    # Initialize market
    result = market.initialize_market(
        initial_mean=market_params["initial_mean"],
        initial_std_dev=market_params["initial_std_dev"],
        initial_backing=market_params["initial_backing"],
        initial_k=market_params["initial_k"],
        lp_address=market_params["lp_address"]
    )
    
    # Setup trader
    trader_address = "trader_1"
    collateral = Decimal('15')  # More than needed
    funded_ledger.mint(trader_address, collateral)
    
    # Execute trade
    trade_result = market.trade(
        new_mean=100.0,
        new_std_dev=10.0,
        trader_address=trader_address,
        max_collateral=collateral
    )
    
    # Verify required collateral is close to expected value
    assert abs(float(trade_result["required_collateral"]) - 14.8519) < 0.0001

# Desmos: https://www.desmos.com/calculator/minuot5ho5
def test_trade_and_settlement(market, market_params, funded_ledger):
    """Test complete flow with trade and settlement"""
    # Initialize market
    result = market.initialize_market(
        initial_mean=market_params["initial_mean"],
        initial_std_dev=market_params["initial_std_dev"],
        initial_backing=market_params["initial_backing"],
        initial_k=market_params["initial_k"],
        lp_address=market_params["lp_address"]
    )
    
    position_id = result["position_id"]
    # Setup and execute trade
    trader_address = "trader_1"
    collateral = Decimal('15')
    funded_ledger.mint(trader_address, collateral)
    
    trade_result = market.trade(
        new_mean=100.0,
        new_std_dev=10.0,
        trader_address=trader_address,
        max_collateral=collateral
    )
    
    trade_position_id = trade_result["position_id"]
    required_collateral = trade_result["required_collateral"]
    
    # Record balances before settlement
    initial_trader_balance = funded_ledger.balance_of(trader_address)
    initial_lp_balance = funded_ledger.balance_of(market_params["lp_address"])
    
    # Settle market
    market.settle_market(107.6)
    
    # Settle trader position
    trader_settlement = market.settle_trader_position(trade_position_id)
    trader_received = trader_settlement["amount"]
    # expected trader position: required collateral + trader payout
    expected_trader_position = float(required_collateral) + 14.8519282576
    assert abs(float(trader_received) - expected_trader_position) < 0.0001 
    
    # Verify trader got collateral back
    assert funded_ledger.balance_of(trader_address) == initial_trader_balance + trader_received 
    
    # Settle LP position
    lp_settlement = market.settle_lp_position(market_params["lp_address"])
    lp_payout = lp_settlement["amount"]
    assert abs(float(lp_payout) - 12.5418988588) < 0.0001

    # Settle LP trader position position_id = result["position_id"]
    lp_trader_settlement = market.settle_trader_position(position_id)
    lp_trader_payout = lp_trader_settlement["amount"]
    assert abs(float(lp_trader_payout) -  22.6061728837) < 0.0001
    
    # Verify total payouts
    total_payout = trader_received + lp_payout + lp_trader_payout
    # expected total payouts
    expected_total_payouts = float(market_params["initial_backing"] + required_collateral)
    assert abs(float(total_payout) - expected_total_payouts) < 0.001 

# desmos: https://www.desmos.com/calculator/giueqolx40
def test_std_dev_backing_constraint(market, market_params, funded_ledger):
    """Test that trades are rejected when std dev violates backing constraint"""
    # Initialize market
    result = market.initialize_market(
        initial_mean=market_params["initial_mean"],
        initial_std_dev=market_params["initial_std_dev"], 
        initial_backing=market_params["initial_backing"],
        initial_k=market_params["initial_k"],
        lp_address=market_params["lp_address"]
    )
    
    # Setup trader
    trader_address = "trader_1"
    collateral = Decimal('20')  # More than needed
    funded_ledger.mint(trader_address, collateral)
    
    # Calculate minimum allowed std dev based on current k and backing
    # σ >= k^2 / (b^2 * sqrt(π))
    k = market.k
    b = float(market_params["initial_backing"])
    min_std_dev = (k * k) / (b * b * np.sqrt(np.pi))
    print(f"Minimum standard Deviation: {min_std_dev}")

    # Try to trade with std dev below minimum - should fail
    invalid_std_dev = 9.9  # below minimum
    print(f"Invalid standard Deviation: {invalid_std_dev}")
    
    with pytest.raises(ValueError, match="Standard deviation too low"):
        market.trade(
            new_mean=100.0,
            new_std_dev=invalid_std_dev,
            trader_address=trader_address, 
            max_collateral=collateral
        )
    
    # Verify trade with valid std dev succeeds
    valid_std_dev = 10.1  # Just above minimum
    trade_result = market.trade(
        new_mean=100.0,
        new_std_dev=valid_std_dev,
        trader_address=trader_address,
        max_collateral=collateral
    )
    
    assert "position_id" in trade_result
    assert "required_collateral" in trade_result

# desmos: https://www.desmos.com/calculator/mthafyguaj
def test_initialize_and_add_liquidity(market, market_params, funded_ledger):
    """Test initial LP providing liquidity followed by additional LP"""
    # Initial setup and market initialization
    initial_lp_balance = funded_ledger.balance_of(market_params["lp_address"])
    initial_market_balance = funded_ledger.balance_of(market.address)
    assert initial_lp_balance == market_params["initial_backing"]
    assert initial_market_balance == 0

    # Initialize market with first LP
    result = market.initialize_market(
        initial_mean=market_params["initial_mean"],
        initial_std_dev=market_params["initial_std_dev"],
        initial_backing=market_params["initial_backing"],
        initial_k=market_params["initial_k"],
        lp_address=market_params["lp_address"]
    )
    initial_position_id = result["position_id"]
    
    # Record state after initialization
    initial_k = market.k
    initial_total_backing = market.total_backing
    initial_lp_tokens = market.total_lp_tokens()
    
    # Setup second LP
    lp2_address = "lp_2"
    additional_backing = Decimal('25')  # Half of initial backing
    funded_ledger.mint(lp2_address, additional_backing)
    
    # Add liquidity from second LP
    add_liquidity_result = market.add_liquidity(
        lp_address=lp2_address,
        backing_amount=additional_backing
    )
    
    # Test market state after additional liquidity
    assert market.total_backing == initial_total_backing + additional_backing
    assert market.k == initial_k * (float(market.total_backing) / float(initial_total_backing))
    
    # Test LP token issuance
    expected_new_lp_tokens = initial_lp_tokens * (additional_backing / initial_total_backing)
    assert market.balanceOf(lp2_address) == expected_new_lp_tokens
    
    # Test LP trader position creation
    new_position = market.get_position(add_liquidity_result["position_id"])
    assert new_position["owner"] == lp2_address
    assert new_position["mean"] == market_params["initial_mean"]
    assert new_position["std_dev"] == market_params["initial_std_dev"]
    
    # Settle market and verify payouts
    final_value = 95.0  # Equal to initial mean for simplicity
    market.settle_market(final_value)
    
    # Settle initial LP position
    initial_lp_settlement = market.settle_trader_position(initial_position_id)
    initial_lp_payout = initial_lp_settlement["amount"]
    
    # Settle second LP position
    second_lp_settlement = market.settle_trader_position(add_liquidity_result["position_id"])
    second_lp_payout = second_lp_settlement["amount"]
    
    # Settle LP positions
    first_lp_position = market.settle_lp_position(market_params["lp_address"])
    second_lp_position = market.settle_lp_position(lp2_address)
    
    # Calculate total payouts for each LP
    total_first_lp = initial_lp_payout + first_lp_position["amount"]
    total_second_lp = second_lp_payout + second_lp_position["amount"]
    
    # Each LP should get exactly their initial amount back since final_value = initial_mean
    assert abs(float(total_first_lp) - float(market_params["initial_backing"])) < 0.001
    assert abs(float(total_second_lp) - float(additional_backing)) < 0.001
    
    # Total payouts should equal total initial backing
    total_payouts = total_first_lp + total_second_lp
    assert abs(float(total_payouts) - float(market_params["initial_backing"] + additional_backing)) < 0.001
    
    # Test events
    events = market.event_log.get_events()
    assert any(
        e.name == "LiquidityAdded" and
        e.params["lp_address"] == lp2_address and
        e.params["backing_amount"] == float(additional_backing) and
        e.params["position_id"] == add_liquidity_result["position_id"]
        for e in events
    )

def test_trade_with_liquidity_addition(market, market_params, funded_ledger):
    """Test that trader payouts remain correct when liquidity is added after their trade"""
    # Initialize market
    result = market.initialize_market(
        initial_mean=market_params["initial_mean"],
        initial_std_dev=market_params["initial_std_dev"],
        initial_backing=market_params["initial_backing"],
        initial_k=market_params["initial_k"],
        lp_address=market_params["lp_address"]
    )
    
    # Setup and execute trader position
    trader_address = "trader_1"
    trader_collateral = Decimal('15')
    funded_ledger.mint(trader_address, trader_collateral)
    
    trade_result = market.trade(
        new_mean=100.0,  # Move mean up
        new_std_dev=10.0,
        trader_address=trader_address,
        max_collateral=trader_collateral
    )
    trader_position_id = trade_result["position_id"]
    required_collateral = trade_result["required_collateral"]
    
    # Record market state before additional liquidity
    k_before_liquidity = market.k
    
    # Add additional liquidity
    lp2_address = "lp_2"
    additional_backing = Decimal('25')
    funded_ledger.mint(lp2_address, additional_backing)
    
    market.add_liquidity(
        lp_address=lp2_address,
        backing_amount=additional_backing
    )
    
    # Verify k increased
    assert market.k > k_before_liquidity
    
    # Settle market at a profitable point for trader
    final_value = 107.6  # Above trader's mean
    market.settle_market(final_value)
    
    # Calculate expected trader payout 
    trader_settlement = market.settle_trader_position(trader_position_id)
    trader_payout = trader_settlement["amount"]
    
    # Trader's total (payout + initial collateral) should be same whether 
    # liquidity was added or not
    expected_total = float(required_collateral) + 14.8519282576  # From previous test
    assert abs(float(trader_payout) - expected_total) < 0.001

def test_add_liquidity_insufficient_funds(market, market_params, funded_ledger):
    """Test that add_liquidity fails when LP has insufficient funds"""
    # Initialize market
    market.initialize_market(
        initial_mean=market_params["initial_mean"],
        initial_std_dev=market_params["initial_std_dev"],
        initial_backing=market_params["initial_backing"],
        initial_k=market_params["initial_k"],
        lp_address=market_params["lp_address"]
    )
    
    # Try to add liquidity without sufficient funds
    lp2_address = "lp_2"
    backing_amount = Decimal('25')
    # Don't mint funds to lp2
    
    with pytest.raises(ValueError, match="Insufficient funds"):
        market.add_liquidity(
            lp_address=lp2_address,
            backing_amount=backing_amount
        )
        
def test_add_liquidity_to_settled_market(market, market_params, funded_ledger):
    """Test that add_liquidity fails when market is already settled"""
    # Initialize market
    market.initialize_market(
        initial_mean=market_params["initial_mean"],
        initial_std_dev=market_params["initial_std_dev"],
        initial_backing=market_params["initial_backing"],
        initial_k=market_params["initial_k"],
        lp_address=market_params["lp_address"]
    )
    
    # Settle market
    market.settle_market(95.0)
    
    # Try to add liquidity to settled market
    lp2_address = "lp_2"
    backing_amount = Decimal('25')
    funded_ledger.mint(lp2_address, backing_amount)
    
    with pytest.raises(ValueError, match="Market already settled"):
        market.add_liquidity(
            lp_address=lp2_address,
            backing_amount=backing_amount
        )