# distributionmarkets/core/utils.py

from decimal import Decimal
from typing import Tuple, Callable
import numpy as np
from scipy.stats import norm
from scipy.optimize import minimize

def calculate_lambda(sigma: float, k: float = 1.0) -> float:
    """
    Calculate the scaling factor lambda given a standard deviation.
    
    Args:
        sigma: Standard deviation of the distribution
        k: l2 norm constraint (default 1.0)
    
    Returns:
        Scaling factor lambda = k * sqrt(2σ√π)
    """
    return k * np.sqrt(2 * sigma * np.sqrt(np.pi))

def calculate_f(x: float, mu: float, sigma: float, k: float = 1.0) -> float:
    """
    Calculate the scaled PDF at point x.
    
    Args:
        x: Point at which to evaluate
        mu: Mean of the distribution
        sigma: Standard deviation of the distribution
        k: l2 norm constraint (default 1.0)
    
    Returns:
        Value of the scaled PDF at point x
    """
    lambda_val = calculate_lambda(sigma, k)
    return lambda_val * norm.pdf(x, mu, sigma)

def position_at_point(x: float, from_mu: float, from_sigma: float, 
                     to_mu: float, to_sigma: float, k: float = 1.0) -> float:
    """
    Calculate the value of a position at a given price point.
    
    Args:
        x: Point at which to evaluate
        from_mu: Initial mean
        from_sigma: Initial standard deviation
        to_mu: Target mean
        to_sigma: Target standard deviation
        k: l2 norm constraint (default 1.0)
    
    Returns:
        Value of the position at point x (positive for profit, negative for loss)
    """
    f1 = calculate_f(x, from_mu, from_sigma, k)
    f2 = calculate_f(x, to_mu, to_sigma, k)
    return f2 - f1

def find_maximum_loss(from_mu: float, from_sigma: float, 
                     to_mu: float, to_sigma: float, k: float = 1.0) -> Tuple[float, float]:
    """
    Find the point of maximum loss and its value for a position.
    
    Args:
        from_mu: Initial mean
        from_sigma: Initial standard deviation
        to_mu: Target mean
        to_sigma: Target standard deviation
        k: l2 norm constraint (default 1.0)
    
    Returns:
        Tuple of (maximum loss amount, price point where it occurs)
    """
    def loss_at_point(x):
        # If x is a numpy array, get the first element
        if hasattr(x, '__iter__'):
            x = x.item()
        return position_at_point(float(x), from_mu, from_sigma, to_mu, to_sigma, k)
    
    # Try multiple starting points to avoid local minima
    x_guesses = [
        from_mu - 2*max(from_sigma, to_sigma),
        from_mu,
        to_mu,
        (from_mu + to_mu)/2,
        to_mu + 2*max(from_sigma, to_sigma)
    ]
    
    results = []
    for x_guess in x_guesses:
        result = minimize(loss_at_point, x_guess)
        if result.success:
            results.append((result.fun, result.x[0]))
    
    min_val, min_x = min(results, key=lambda x: x[0])
    return (-min_val, min_x)  # Return positive number for maximum loss

def calculate_required_collateral(from_mu: float, from_sigma: float,
                                to_mu: float, to_sigma: float,
                                k: float = 1.0) -> float:
    """
    Calculate required collateral for a trade.
    
    Args:
        from_mu: Initial mean
        from_sigma: Initial standard deviation
        to_mu: Target mean
        to_sigma: Target standard deviation
        k: l2 norm constraint (default 1.0)
    
    Returns:
        Required collateral amount
    """
    max_loss, _ = find_maximum_loss(from_mu, from_sigma, to_mu, to_sigma, k)
    return max_loss

def calculate_maximum_k(sigma: float, b: Decimal) -> float:
    """
    Calculate the maximum allowable k (l2 norm constraint) given sigma and maximum payout b.
    
    Args:
        sigma: Standard deviation of the distribution (float)
        b: Maximum payout allowed (Decimal)
    
    Returns:
        Maximum allowable k value that ensures maximum payout constraint is satisfied (float)
    
    Note: While b is a Decimal as it represents currency, k is returned as a float
    as it's a mathematical scaling factor, not a currency amount.
    """
    if sigma <= 0:
        raise ValueError("sigma must be positive")
    if b <= 0:
        raise ValueError("maximum payout must be positive")
        
    b_float = float(b)  # Convert Decimal to float for numpy operations
    return b_float * np.sqrt(sigma * np.sqrt(np.pi))

def calculate_minimum_sigma(k: float, b: float) -> float:
    """
    Calculate minimum allowed standard deviation given k and backing amount.
    
    Args:
        k: l2 norm constraint 
        b: backing amount
        
    Returns:
        Minimum allowed standard deviation
    """
    if k <= 0 or b <= 0:
        raise ValueError("k and b must be positive")
    return (k * k) / (b * b * np.sqrt(np.pi))