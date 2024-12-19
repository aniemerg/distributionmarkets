# Distribution Markets Module Design

## Overview
This module implements simulation infrastructure for distribution markets, suitable for modeling both smart contract and web-based implementations. The design prioritizes blockchain-like patterns while maintaining flexibility for web-based implementations.

## Core Components

### DistributionMarket
Central class representing a single prediction market for one event.
- Tracks market state (Active, Paused, Finalized)
- Manages user positions and balances
- Enforces market invariants
- Emits events for all state changes
- Interacts with balance system for fund management

### Balance System
Separate system managing user funds:
- Tracks user balances
- Handles deposits/withdrawals
- Enforces sufficient balance for trades
- Maintains market<->user fund transfers

### Roles
Multiple admin roles with distinct responsibilities:
- Oracle: Provides and certifies final outcome value
- Admin: Controls market parameters, can pause/unpause
- Users: Regular market participants

### Events
Blockchain-style event system:
- Each event has name and parameters
- Events emitted for all state changes
- Examples:
  - Trade(user, size, parameters)
  - Deposit(user, amount)
  - MarketFinalized(finalValue)
  - PositionSettled(user, payout)

## State Management

### Market States
```
Active -> Paused -> Active
Active -> Finalized
```

### Position Settlement
- Users must claim their own positions
- Settlement available after market finalization
- Partial settlement should be supported
- Settlement updates user balance atomically

## Testing Strategy

### Unit Tests
- Individual component functionality
- Market state transitions
- Balance management
- Event emission

### Integration Tests
- Complete market lifecycle
- Multiple user interactions
- Complex settlement patterns

### Invariant Tests
- Total payouts = Total deposits
- User balance consistency
- Position settlement completeness

### Test Scenarios
Specific scenarios to implement:
1. Basic market lifecycle
2. Multiple traders
3. Settlement patterns
4. Edge cases (e.g., zero liquidity)


## Development Practices

### Code Organization
```
distributionmarkets/
  ├── core/
  │   ├── market.py
  │   ├── ledger.py
  │   ├── events.py
  │   └── roles.py
  ├── tests/
  │   ├── unit/
  │   ├── integration/
  │   └── scenarios/
  └── utils/
```
