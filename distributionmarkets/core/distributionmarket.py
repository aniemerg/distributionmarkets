from decimal import Decimal
from typing import Dict, Optional
from distributionmarkets.core.marketmath import calculate_lambda, calculate_f
from distributionmarkets.core.events import Event

class Position:
    """Represents a trader's position in the market"""
    def __init__(self, owner: str, mean: float, std_dev: float):
        self.owner = owner
        self.mean = mean
        self.std_dev = std_dev

class DistributionMarket:
    """
    Implements a distribution market where traders can take positions on 
    continuous probability distributions
    """
    def __init__(self, ledger, event_log, k: float = 1.0):
        self.ledger = ledger
        self.event_log = event_log
        self.k = k
        self.address = "market"
        
        # Market state
        self.current_mean = 0.0
        self.current_std_dev = 0.0
        self.total_backing = Decimal('0')
        self.initialized = False
        self.settled = False
        self.final_value = None
        self.next_position_id = 1
        
        # LP token balances, like ERC-20
        self.lp_balances = {}
        
        # Trader positions
        self.positions = {}

    def initialize_market(
        self,
        initial_mean: float,
        initial_std_dev: float,
        initial_backing: Decimal,
        lp_address: str
    ) -> Dict[str, str]:
        """Initialize market with first LP position"""
        if self.initialized:
            raise ValueError("Market already initialized")

        # Transfer backing to market
        self.ledger.transfer(lp_address, self.address, initial_backing)
        
        # Mint LP tokens to address
        self.lp_balances[lp_address] = initial_backing
        
        # Create trader position
        position_id = str(self.next_position_id)
        self.next_position_id += 1
        self.positions[position_id] = Position(
            owner=lp_address,
            mean=initial_mean,
            std_dev=initial_std_dev
        )
        
        # Update market state
        self.current_mean = initial_mean
        self.current_std_dev = initial_std_dev
        self.total_backing = initial_backing
        self.initialized = True
        
        # Emit event
        self.event_log.emit(Event(
            name="MarketInitialized",
            params={
                "type": "MarketInitialized",
                "position_id": position_id,
                "initial_mean": initial_mean,
                "initial_std_dev": initial_std_dev,
                "backing": float(initial_backing)
            }
        ))
        
        return {
            "position_id": position_id
        }

    def balanceOf(self, address: str) -> Decimal:
        """Get LP token balance of address"""
        return self.lp_balances.get(address, Decimal('0'))

    def total_lp_tokens(self) -> Decimal:
        """Get total supply of LP tokens"""
        return sum(self.lp_balances.values(), Decimal('0'))

    def get_position(self, position_id: str) -> Optional[Dict]:
        """Get position information by ID"""
        position = self.positions.get(position_id)
        if position is None:
            return None
        return {
            "owner": position.owner,
            "mean": position.mean,
            "std_dev": position.std_dev
        }

    def settle_market(self, final_value: float) -> None:
        """Settle market at final value"""
        if self.settled:
            raise ValueError("Market already settled")
            
        self.settled = True
        self.final_value = final_value

        self.event_log.emit(Event(
            name="MarketSettled",
            params={
                "type": "MarketSettled",
                "final_value": final_value
            }
        ))

    def settle_trader_position(self, position_id: str) -> Dict:
        """Settle a trader position"""
        if not self.settled:
            raise ValueError("Market not settled")
            
        position = self.positions.get(position_id)
        if position is None:
            raise ValueError("Position not found")
            
        # Calculate payout based on final value
        lambda_val = calculate_lambda(position.std_dev, self.k)
        payout = calculate_f(self.final_value, position.mean, position.std_dev, self.k)
        payout_amount = Decimal(str(payout))
        
        # Transfer payout
        self.ledger.transfer(self.address, position.owner, payout_amount)
        
        # Emit event
        self.event_log.emit(Event(
            name="PositionSettled",
            params={
                "type": "PositionSettled",
                "position_id": position_id,
                "payout": float(payout_amount)
            }
        ))
        
        return {
            "recipient": position.owner
        }

    def settle_lp_position(self, lp_address: str) -> Dict:
        """Settle LP position"""
        if not self.settled:
            raise ValueError("Market not settled")
            
        lp_balance = self.balanceOf(lp_address)
        if lp_balance == 0:
            raise ValueError("No LP position found")
            
        # Calculate proportional payout of remaining funds
        total_lp_supply = self.total_lp_tokens()
        # Is it valid to assume that the contracts balance is the backing? Probably Not. 
        remaining_funds = self.ledger.balance_of(self.address)
        payout = (lp_balance / total_lp_supply) * remaining_funds
        
        # Transfer payout and clear LP tokens
        self.ledger.transfer(self.address, lp_address, payout)
        self.lp_balances[lp_address] = Decimal('0')
        
        return {
            "recipient": lp_address,
            "amount": payout
        }