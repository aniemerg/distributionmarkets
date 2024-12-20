from decimal import Decimal, ROUND_DOWN
from typing import Dict, Optional, Any
from distributionmarkets.core.marketmath import calculate_lambda, calculate_f, calculate_maximum_k, find_maximum_loss
from distributionmarkets.core.events import Event

class Position:
    """Represents a trader's position in the market"""
    def __init__(self, owner: str, 
                 mean: float, 
                 std_dev: float, 
                 collateral: Decimal = Decimal(0.0),
                 old_mean: float = 0.0,
                 old_std_dev: float = 0.0,
                 is_LP: bool = False
                ):
        self.owner = owner
        self.mean = mean
        self.std_dev = std_dev
        self.collateral = collateral
        self.old_mean = old_mean
        self.old_std_dev = old_std_dev
        self.is_LP = is_LP
        self.settled = False

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
            std_dev=initial_std_dev,
            collateral = initial_backing,
            is_LP = True
        )
        
        # Update market state
        self.current_mean = initial_mean
        self.current_std_dev = initial_std_dev
        self.total_backing = initial_backing
        self.initialized = True
        
        # update k
        self.k = calculate_maximum_k(initial_std_dev, initial_backing)
        print(f"Initial k: {self.k}")

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

    def trade(
        self,
        new_mean: float,
        new_std_dev: float,
        trader_address: str,
        max_collateral: Decimal
    ) -> Dict[str, Any]:
        """
        Execute a trade to move market to new position
        Returns position ID and required collateral amount
        """
        if not self.initialized:
            raise ValueError("Market not initialized")
        
        if self.settled:
            raise ValueError("Market already settled")

        required_collateral, _ = find_maximum_loss(self.current_mean, self.current_std_dev, 
                     new_mean, new_std_dev, self.k)

        required_collateral = Decimal(str(required_collateral))
        
        if required_collateral > max_collateral:
            raise ValueError("Insufficient collateral")
            
        # Transfer collateral
        self.ledger.transfer(trader_address, self.address, required_collateral)
        
        # Create new position
        position_id = str(self.next_position_id)
        self.next_position_id += 1
        
        self.positions[position_id] = Position(
            owner=trader_address,
            mean=new_mean,
            std_dev=new_std_dev,
            collateral=required_collateral,
            old_mean=self.current_mean,
            old_std_dev=self.current_std_dev
        )
        
        # Update market state
        self.current_mean = new_mean
        self.current_std_dev = new_std_dev

        # update k
        self.k = calculate_maximum_k(self.current_std_dev, self.total_backing)
        print(f"Updated k: {self.k}")
        
        # Emit event
        self.event_log.emit(Event(
            name="Trade",
            params={
                "type": "Trade",
                "position_id": position_id,
                "trader": trader_address,
                "new_mean": new_mean,
                "new_std_dev": new_std_dev,
                "collateral": float(required_collateral)
            }
        ))
        
        return {
            "position_id": position_id,
            "required_collateral": required_collateral
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
        
        if position.settled:
            raise ValueError("Position already settled.")
            
        # Calculate payout based on final value
        payout = calculate_f(self.final_value, position.mean, position.std_dev, self.k)
        if not position.is_LP:
            payout -= calculate_f(self.final_value, position.old_mean, position.old_std_dev, self.k)
        
        payout_amount = Decimal(str(payout)).quantize(Decimal('0.00000000001'), rounding=ROUND_DOWN)  # 18 decimal places should be more than sufficient
        
        if not position.is_LP:
            payout_amount += position.collateral
        
        # Transfer payout
        self.ledger.transfer(self.address, position.owner, payout_amount)
        position.settled = True
        
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
            "recipient": position.owner,
            "amount": payout_amount
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
        remaining_funds = self.total_backing - Decimal(calculate_f(self.final_value, self.current_mean, self.current_std_dev, self.k))
        payout = (lp_balance / total_lp_supply) * remaining_funds

        # Transfer payout and clear LP tokens
        self.ledger.transfer(self.address, lp_address, payout)
        self.lp_balances[lp_address] = Decimal('0')
        
        return {
            "recipient": lp_address,
            "amount": payout
        }