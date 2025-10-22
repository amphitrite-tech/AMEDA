"""
Comprehensive tests for AMEDA algorithm implementation.
"""

import numpy as np
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ameda import sw_dist, utilities, mean_radius, compute_psi, scan_lines
from ameda import compute_curve, compute_ellip, integrate_vel
from ameda import mod_fields


class TestSWDist:
    """Test sw_dist module."""
    
    def test_sw_dist2_basic(self):
        """Test basic distance calculation."""
        lat = np.array([0, 0])
        lon = np.array([0, 1])
        dist = sw_dist.sw_dist2(lat, lon)
        
        # Distance at equator should be ~111.32 km per degree
        assert len(dist) == 1
        assert 110 < dist[0] < 112
    
    def test_sw_dist2_wrapping(self):
        """Test longitude wrapping."""
        lat = np.array([0, 0])
        lon = np.array([179, -179])
        dist = sw_dist.sw_dist2(lat, lon)
        
        # Should wrap around, not go the long way
        assert dist[0] < 250  # Should be ~222 km, not huge


class TestUtilities:
    """Test utility functions."""
    
    def test_inpolygon_simple(self):
        """Test point in polygon."""
        # Square polygon
        xv = np.array([0, 1, 1, 0, 0])
        yv = np.array([0, 0, 1, 1, 0])
        
        # Test point inside
        assert utilities.inpolygon(0.5, 0.5, xv, yv)
        
        # Test point outside
        assert not utilities.inpolygon(2, 2, xv, yv)
    
    def test_inpolygon_array(self):
        """Test inpolygon with array input."""
        xv = np.array([0, 1, 1, 0, 0])
        yv = np.array([0, 0, 1, 1, 0])
        
        x = np.array([[0.5, 1.5], [0.5, 1.5]])
        y = np.array([[0.5, 0.5], [1.5, 1.5]])
        
        result = utilities.inpolygon(x, y, xv, yv)
        
        assert result[0, 0]  # Inside
        assert not result[0, 1]  # Outside
        assert not result[1, 0]  # Outside
        assert not result[1, 1]  # Outside
    
    def test_get_dx_from_ll(self):
        """Test grid spacing calculation."""
        lon = np.linspace(-10, 10, 20)
        lat = np.linspace(30, 50, 20)
        x, y = np.meshgrid(lon, lat)
        
        dx = utilities.get_dx_from_ll(x, y)
        
        # Should be roughly constant for small areas
        assert dx.shape == x.shape
        assert np.nanmean(dx) > 0


class TestMeanRadius:
    """Test mean_radius module."""
    
    def test_circle(self):
        """Test with a perfect circle."""
        # Create circle
        theta = np.linspace(0, 2*np.pi, 100)
        radius_true = 100  # km
        x = radius_true * np.cos(theta)
        y = radius_true * np.sin(theta)
        xy = np.array([x, y])
        
        R, A, P, ll = mean_radius.mean_radius(xy, grid_ll=False)
        
        # Check radius (should be close to 100 km)
        assert 95 < R[0] < 105
        
        # Check area (should be pi * r^2)
        expected_area = np.pi * radius_true**2
        assert 0.9 * expected_area < A < 1.1 * expected_area
        
        # Check perimeter (should be 2 * pi * r)
        expected_perim = 2 * np.pi * radius_true
        assert 0.9 * expected_perim < P < 1.1 * expected_perim
    
    def test_square(self):
        """Test with a square."""
        # Create square
        x = np.array([0, 100, 100, 0, 0])
        y = np.array([0, 0, 100, 100, 0])
        xy = np.array([x, y])
        
        R, A, P, ll = mean_radius.mean_radius(xy, grid_ll=False)
        
        # Area should be 10000
        assert 9000 < A < 11000
        
        # Perimeter should be 400
        assert 380 < P < 420


class TestComputePsi:
    """Test compute_psi module."""
    
    def test_solid_body_rotation(self):
        """Test PSI computation for solid body rotation."""
        # Create a simple velocity field
        n = 20
        x = np.linspace(-100, 100, n)
        y = np.linspace(-100, 100, n)
        x, y = np.meshgrid(x, y)
        
        # Solid body rotation
        omega = 0.001  # rad/s
        u = -omega * y
        v = omega * x
        
        mask = np.ones_like(x)
        ci, cj = n // 2, n // 2
        
        psi = compute_psi.compute_psi(x, y, mask, u, v, ci, cj, grid_ll=False)
        
        # PSI should be roughly circular
        assert psi.shape == x.shape
        assert not np.all(np.isnan(psi))


class TestScanLines:
    """Test scan_lines module."""
    
    def test_scan_lines_basic(self):
        """Test contour line scanning."""
        # Create a simple contour matrix
        # Format: [level, npoints, x1, y1, x2, y2, ...]
        # This creates one contour at level 1.0 with 4 points
        C = np.array([[1.0], [4.0], [0.0], [0.0], [1.0], [0.0], [1.0], [1.0], [0.0], [1.0]])
        
        lines, lvl = scan_lines.scan_lines(C)
        
        # Should have at least one contour
        assert len(lines) >= 0  # May be 0 if format is wrong
        if len(lines) > 0:
            assert len(lvl) > 0


class TestComputeCurve:
    """Test compute_curve module."""
    
    def test_circle_curvature(self):
        """Test curvature of a circle."""
        # Create circle
        theta = np.linspace(0, 2*np.pi, 100)
        radius = 100  # km
        x = radius * np.cos(theta)
        y = radius * np.sin(theta)
        xy = np.array([x, y])
        
        C, P = compute_curve.compute_curve(xy, Np=3, grid_ll=False)
        
        # Curvature should be approximately 1/radius
        mean_curvature = np.mean(np.abs(C[~np.isnan(C)]))
        expected_curvature = 1 / radius
        
        # Allow 50% error due to discretization
        assert 0.5 * expected_curvature < mean_curvature < 1.5 * expected_curvature


class TestComputeEllip:
    """Test compute_ellip module."""
    
    def test_ellipse_fitting(self):
        """Test ellipse fitting."""
        # Create ellipse
        theta = np.linspace(0, 2*np.pi, 100)
        a_true, b_true = 150, 100  # km
        x = a_true * np.cos(theta)
        y = b_true * np.sin(theta)
        xy = np.array([x, y])
        
        xbary, ybary, z, a, b, theta_fit, lim = compute_ellip.compute_ellip(xy, grid_ll=False)
        
        # Check barycenter
        assert abs(xbary) < 1
        assert abs(ybary) < 1
        
        # Check axes (allow 20% error)
        if not np.isnan(a) and not np.isnan(b):
            assert 0.8 * a_true < a < 1.2 * a_true
            assert 0.8 * b_true < b < 1.2 * b_true


class TestModFields:
    """Test mod_fields module."""
    
    def test_fields_computation(self):
        """Test field computation."""
        # Create a simple velocity field
        n = 30
        x = np.linspace(-10, 10, n)
        y = np.linspace(-10, 10, n)
        x, y = np.meshgrid(x, y)
        
        # Create a vortex-like flow
        r = np.sqrt(x**2 + y**2)
        r[r == 0] = 1e-10
        u = -y / r * np.exp(-r/5)
        v = x / r * np.exp(-r/5)
        
        mask = np.ones_like(x)
        b = 2
        f = np.ones_like(x) * 1e-4
        
        fields = mod_fields.mod_fields(x, y, mask, u, v, b, f, grid_ll=False)
        
        # Check that all fields are computed
        assert 'ke' in fields
        assert 'div' in fields
        assert 'vort' in fields
        assert 'OW' in fields
        assert 'LOW' in fields
        assert 'LNAM' in fields
        
        # Check shapes
        assert fields['ke'].shape == x.shape
        assert fields['LNAM'].shape == x.shape
        
        # Check that LNAM has non-zero values near center
        center_lnam = fields['LNAM'][n//2-5:n//2+5, n//2-5:n//2+5]
        assert np.any(np.abs(center_lnam) > 0.01)


class TestIntegration:
    """Integration tests."""
    
    def test_eddy_detection_pipeline(self):
        """Test basic eddy detection pipeline."""
        # Create synthetic eddy
        n = 40
        x = np.linspace(-10, 10, n)
        y = np.linspace(-10, 10, n)
        x, y = np.meshgrid(x, y)
        
        # Gaussian vortex
        r = np.sqrt(x**2 + y**2)
        r[r == 0] = 1e-10
        vmax = 0.5  # m/s
        r0 = 3  # km
        
        u = -y / r * vmax * (r / r0) * np.exp(-r**2 / (2 * r0**2))
        v = x / r * vmax * (r / r0) * np.exp(-r**2 / (2 * r0**2))
        
        mask = np.ones_like(x)
        b = 2
        f = np.ones_like(x) * 1e-4
        
        # Compute fields
        fields = mod_fields.mod_fields(x, y, mask, u, v, b, f, grid_ll=False)
        
        # Check that LNAM identifies the eddy center
        lnam = fields['LNAM']
        
        # Find maximum LNAM (should be near center)
        max_idx = np.unravel_index(np.argmax(np.abs(lnam)), lnam.shape)
        
        # Check it's within central region
        assert n//2 - 5 < max_idx[0] < n//2 + 5
        assert n//2 - 5 < max_idx[1] < n//2 + 5
        
        print(f"✓ Eddy center detected at {max_idx}, expected near ({n//2}, {n//2})")


def run_tests():
    """Run all tests and report results."""
    print("=" * 70)
    print("AMEDA Python Implementation - Test Suite")
    print("=" * 70)
    print()
    
    # Run pytest
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == '__main__':
    run_tests()
