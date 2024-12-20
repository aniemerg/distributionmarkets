import pytest
import numpy as np
from distributionmarkets.core.marketmath import (
    calculate_lambda,
    calculate_f,
    position_at_point,
    find_maximum_loss,
    calculate_required_collateral
)

def test_lambda_calculation():
    """Test lambda calculation with known values."""
    sigma = 10
    k = 1.0
    lambda_val = calculate_lambda(sigma, k)
    assert lambda_val > 0
    # Could add specific value tests if we have them

def test_position_symmetry():
    """Test if position values are symmetric in the equal variance case."""
    from_mu = 95
    to_mu = 100
    sigma = 10
    mid = (from_mu + to_mu) / 2
    
    pos_up = position_at_point(mid + 5, from_mu, sigma, to_mu, sigma)
    pos_down = position_at_point(mid - 5, from_mu, sigma, to_mu, sigma)
    
    assert np.isclose(pos_up, -pos_down, rtol=1e-3)

def test_maximum_loss():
    """Test maximum loss calculation."""
    from_mu = 95
    to_mu = 100
    sigma = 10
    
    max_loss, worst_price = find_maximum_loss(from_mu, sigma, to_mu, sigma)
    
    assert max_loss > 0
    assert worst_price < from_mu  # Worst price should be below initial mean

def test_collateral_calculation():
    """Test collateral calculation matches maximum loss."""
    from_mu = 95
    to_mu = 100
    sigma = 10
    
    collateral = calculate_required_collateral(from_mu, sigma, to_mu, sigma)
    max_loss, _ = find_maximum_loss(from_mu, sigma, to_mu, sigma)
    
    assert np.isclose(collateral, max_loss)

def test_pdf_scaling():
    """Test that PDFs are properly scaled."""
    mu = 100
    sigma = 10
    k = 1.0
    
    # Test points
    x = np.linspace(mu - 3*sigma, mu + 3*sigma, 1000)
    f = calculate_f(x, mu, sigma, k)
    
    # Check that the scaled PDF integrates properly
    integral = np.trapz(f**2, x)
    assert np.isclose(np.sqrt(integral), k, rtol=1e-2)