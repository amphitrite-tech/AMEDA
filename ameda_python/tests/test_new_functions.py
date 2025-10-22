"""
Tests for newly implemented functions.
"""

import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ameda import compute_best_fit, min_dist_shapes, concat_eddy


class TestComputeBestFit:
    """Test compute_best_fit module."""
    
    def test_eddy_profile_model(self):
        """Test the theoretical eddy profile model."""
        # Test with Gaussian profile (alpha=2)
        r = np.linspace(0, 2, 100)
        v = compute_best_fit.eddy_profile_model(r, alpha=2.0)
        
        # Maximum should be at r=1
        max_idx = np.argmax(v)
        assert 0.95 < r[max_idx] < 1.05
        
        # Value at r=1 should be close to 1
        v_at_1 = compute_best_fit.eddy_profile_model(1.0, 2.0)
        assert 0.95 < v_at_1 < 1.05
    
    def test_best_fit_gaussian_profile(self):
        """Test fitting to a synthetic Gaussian eddy."""
        # Create synthetic profile data
        r = np.linspace(0.2, 2.0, 50)
        alpha_true = 2.0
        v = r * np.exp((1 - r**alpha_true) / alpha_true)
        
        # Add small noise
        np.random.seed(42)
        v += np.random.normal(0, 0.01, len(v))
        
        # Create lines array [nc, eta, rmoy, vel, tau, nrho]
        lines = np.column_stack([
            np.ones(len(r)),  # nc (1 center)
            np.zeros(len(r)),  # eta
            r * 100,  # rmoy (km)
            v * 0.5,  # vel (m/s)
            np.ones(len(r)) * 10,  # tau
            np.zeros(len(r))  # nrho
        ])
        
        # Fit
        rmax = 100.0  # km
        rend = 200.0  # km
        velmax = 0.5  # m/s
        
        curve, err = compute_best_fit.compute_best_fit(lines, rmax, rend, velmax)
        
        if curve is not None:
            # Check that alpha is close to 2
            assert 1.5 < curve['a'] < 2.5
            
            # Check R-squared is reasonable
            assert err['rsquare'] > 0.8
            
            print(f"Fitted alpha: {curve['a']:.2f} (expected: 2.0)")
            print(f"R-squared: {err['rsquare']:.3f}")
    
    def test_best_fit_insufficient_data(self):
        """Test with insufficient data points."""
        # Too few points
        lines = np.array([[1, 0, 10, 0.1, 5, 0],
                          [1, 0, 20, 0.2, 5, 0]])
        
        curve, err = compute_best_fit.compute_best_fit(lines, 100, 200, 0.5)
        
        # Should return None with insufficient data
        assert curve is None
        assert err is None


class TestMinDistShapes:
    """Test min_dist_shapes module."""
    
    def test_cartesian_circles_touching(self):
        """Test distance between two touching circles."""
        # Circle 1: centered at origin, radius 100
        theta = np.linspace(0, 2*np.pi, 50)
        xy1 = np.array([100*np.cos(theta), 100*np.sin(theta)])
        
        # Circle 2: centered at (200, 0), radius 100
        # These circles touch at (100, 0)
        xy2 = np.array([200 + 100*np.cos(theta), 100*np.sin(theta)])
        
        dist = min_dist_shapes.min_dist_shapes(xy1, xy2, grid_ll=False)
        
        # Distance should be approximately 0 (touching)
        assert dist < 10  # Within 10 km tolerance
        
        print(f"Distance between touching circles: {dist:.2f} km")
    
    def test_cartesian_circles_separated(self):
        """Test distance between separated circles."""
        # Circle 1: centered at origin, radius 50
        theta = np.linspace(0, 2*np.pi, 50)
        xy1 = np.array([50*np.cos(theta), 50*np.sin(theta)])
        
        # Circle 2: centered at (300, 0), radius 50
        # Minimum distance should be 200 km
        xy2 = np.array([300 + 50*np.cos(theta), 50*np.sin(theta)])
        
        dist = min_dist_shapes.min_dist_shapes(xy1, xy2, grid_ll=False)
        
        # Distance should be approximately 200 km
        assert 190 < dist < 210
        
        print(f"Distance between separated circles: {dist:.2f} km")
    
    def test_vectorized_vs_loop(self):
        """Test that vectorized version gives same result as loop version."""
        theta = np.linspace(0, 2*np.pi, 30)
        xy1 = np.array([100*np.cos(theta), 100*np.sin(theta)])
        xy2 = np.array([250 + 80*np.cos(theta), 80*np.sin(theta)])
        
        # Loop version
        dist_loop = min_dist_shapes.min_dist_shapes(xy1, xy2, grid_ll=False)
        
        # Vectorized version
        dist_vec = min_dist_shapes.min_dist_shapes_vectorized(xy1, xy2, grid_ll=False)
        
        # Should be identical for Cartesian case
        assert abs(dist_loop - dist_vec) < 1e-6
        
        print(f"Loop: {dist_loop:.2f} km, Vectorized: {dist_vec:.2f} km")


class TestConcatEddy:
    """Test concat_eddy module."""
    
    def test_concat_eddy_basic(self):
        """Test basic concatenation functionality."""
        import tempfile
        import pickle
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create fake profile data for two periods
            profil1 = [
                {'step': 1, 'nc': 1, 'vel': [0.1, 0.2]},
                {'step': 2, 'nc': 2, 'vel': [0.3, 0.4]}
            ]
            profil2 = [
                {'step': 1, 'nc': 1, 'vel': [0.5, 0.6]},
                {'step': 2, 'nc': 1, 'vel': [0.7, 0.8]}
            ]
            
            # Save to files
            with open(os.path.join(tmpdir, 'eddy_profil_2020.pkl'), 'wb') as f:
                pickle.dump(profil1, f)
            
            with open(os.path.join(tmpdir, 'eddy_profil_2021.pkl'), 'wb') as f:
                pickle.dump(profil2, f)
            
            # Concatenate
            concat_eddy.concat_eddy(['2020', '2021'], tmpdir, streamlines=True)
            
            # Check output exists
            output_file = os.path.join(tmpdir, 'eddy_profil_2020_2021.pkl')
            assert os.path.exists(output_file)
            
            # Load and verify
            with open(output_file, 'rb') as f:
                result = pickle.load(f)
            
            assert len(result) == 4  # 2 + 2 timesteps
            
            # Check step numbers are sequential
            steps = [r['step'] for r in result if 'step' in r]
            assert steps == [1, 2, 3, 4]
            
            print(f"Concatenated {len(result)} timesteps successfully")


def run_tests():
    """Run all new function tests."""
    print("=" * 70)
    print("Testing Newly Implemented Functions")
    print("=" * 70)
    print()
    
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == '__main__':
    run_tests()
