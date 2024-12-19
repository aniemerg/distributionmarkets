# distributionmarkets/tests/test_roles.py

import pytest
from decimal import Decimal
from distributionmarkets.core.roles import SimpleOracle

def test_simple_oracle():
    """Test basic oracle functionality."""
    oracle = SimpleOracle(Decimal('100.0'))
    assert oracle.get_resolution_value() == Decimal('100.0')

def test_simple_oracle_conversion():
    """Test that oracle properly converts to Decimal."""
    oracle = SimpleOracle(100.0)  # Pass in float
    assert isinstance(oracle.get_resolution_value(), Decimal)
    assert oracle.get_resolution_value() == Decimal('100.0')