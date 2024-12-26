# Distribution Markets

A Python module for simulating distribution prediction markets, based on ["Distribution Markets"](https://www.paradigm.xyz/2024/12/distribution-markets) by [Dave White](https://x.com/_Dave__White_).

## Overview

Distribution markets extend traditional prediction markets by allowing traders to express beliefs about entire probability distributions rather than just discrete outcomes. This module provides tools for simulating these markets, including balance tracking, position management, and event logging, all designed to parallel potential blockchain implementations. It employs blockchain-like patterns such as event emission and user-initiated settlement.

## Installation

Currently, this package is in development. To install in development mode:

```bash
git clone [your-repo-url]
cd distributionmarkets
pip install -e .
```

## Development

To run tests:
```bash
pytest
```

## Contributing

Contributions via pull requests are welcome. Please make sure to add tests for new functionality, and
follow existing patterns for event emission.