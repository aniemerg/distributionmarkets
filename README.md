# Distribution Markets

A Python module for simulating distribution prediction markets, based on ["Distribution Markets"](https://www.paradigm.xyz/2024/12/distribution-markets) by [Dave White](https://x.com/_Dave__White_).

## Overview

Distribution markets extend traditional prediction markets by allowing traders to express beliefs about entire probability distributions rather than just discrete outcomes. This module provides tools for simulating these markets, including balance tracking, position management, and event logging, all designed to parallel potential blockchain implementations. It employs blockchain-like patterns such as event emission and user-initiated settlement.

# Blockchain-like Architecture

The implementation follows Ethereum smart contract patterns to facilitate future on-chain deployment. The ledger system mirrors ERC-20 token mechanics, providing mint, burn, and transfer functionality with proper decimal handling. Each operation emits corresponding transfer events, matching the pattern used in token contracts. The ledger tracks balances using Decimals to maintain precision in financial calculations, similar to how ERC-20s handle token amounts.

Events follow the Ethereum event logging pattern where each contract action emits structured events. The EventLog system captures trade executions, liquidity provisions, settlements, and transfers - each with typed parameters and timestamps. This enables the same kind of historical analysis and event indexing that blockchain explorers provide. The event structure matches Solidity event declarations, making it straightforward to implement the same logging in smart contracts.

The role system demonstrates smart contract interfaces through abstract base classes. The Oracle role shows how off-chain data can be brought on-chain through a clean interface, similar to Chainlink's oracle pattern. The SimpleOracle provides a reference implementation that future integrations can build upon.

## Installation

Currently, this package is in development. To install in development mode:

```bash
git clone [your-repo-url]
cd distributionmarkets
pip install -e .
```

## Usage Example

```python
from distributionmarkets import DistributionMarket, Ledger, EventLog
from decimal import Decimal

# Initialize components
ledger = Ledger(EventLog())
market = DistributionMarket(ledger, EventLog())

# Initialize market
market.initialize_market(
    initial_mean=100.0,
    initial_std_dev=10.0,
    initial_backing=Decimal('1000.0'),
    initial_k=1.0,
    lp_address="lp_1"
)

# Execute a trade
market.trade(
    new_mean=105.0,
    new_std_dev=8.0,
    trader_address="trader_1",
    max_collateral=Decimal('100.0')
)
```

## Development

To run tests:
```bash
pytest
```

## Contributing

Contributions via pull requests are welcome. Please make sure to add tests for new functionality, and
follow existing patterns for event emission.