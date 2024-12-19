# distributionmarkets/core/roles.py

from abc import ABC, abstractmethod
from typing import Optional
from decimal import Decimal

class Oracle(ABC):
    """
    Abstract base class for oracles that provide resolution values for markets.
    """
    @abstractmethod
    def get_resolution_value(self) -> Optional[Decimal]:
        """
        Get the resolution value for the market.
        Returns None if the value is not yet available.
        """
        pass

class SimpleOracle(Oracle):
    """
    Basic oracle implementation that returns a preset value.
    """
    def __init__(self, resolution_value: Decimal):
        self._resolution_value = Decimal(str(resolution_value))

    def get_resolution_value(self) -> Optional[Decimal]:
        return self._resolution_value