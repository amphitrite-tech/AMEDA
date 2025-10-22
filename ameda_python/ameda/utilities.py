"""
Utility functions for AMEDA algorithm
"""

import numpy as np
from matplotlib.path import Path


def inpolygon(x, y, xv, yv):
    """
    Test if points (x, y) are inside or on polygon (xv, yv).
    
    Parameters
    ----------
    x, y : array-like
        Points to test
    xv, yv : array-like
        Vertices of polygon
        
    Returns
    -------
    in_polygon : ndarray of bool
        True if point is inside or on polygon
    """
    # Handle different input shapes
    x = np.asarray(x)
    y = np.asarray(y)
    xv = np.asarray(xv)
    yv = np.asarray(yv)
    
    original_shape = x.shape
    x_flat = x.flatten()
    y_flat = y.flatten()
    
    # Create path from polygon vertices
    vertices = np.column_stack([xv, yv])
    path = Path(vertices)
    
    # Test points
    points = np.column_stack([x_flat, y_flat])
    result = path.contains_points(points)
    
    # Reshape back to original
    return result.reshape(original_shape)


def get_dx_from_ll(x, y):
    """
    Calculate grid spacing in km from lon/lat coordinates.
    
    Parameters
    ----------
    x, y : ndarray
        Longitude and latitude arrays (2D)
        
    Returns
    -------
    dx : ndarray
        Grid spacing in km
    """
    earth_radius = 6378.137  # km
    R = earth_radius * np.pi / 180  # 111.320 km per degree
    
    # Calculate spacing
    dx = np.zeros_like(x)
    dy = np.zeros_like(y)
    
    # Central differences for interior points
    dx[1:-1, 1:-1] = (x[1:-1, 2:] - x[1:-1, :-2]) * R * np.cos(np.deg2rad(y[1:-1, 1:-1]))
    dy[1:-1, 1:-1] = (y[2:, 1:-1] - y[:-2, 1:-1]) * R
    
    # Average horizontal and vertical spacing
    Dx = (np.abs(dx) + np.abs(dy)) / 2
    
    return Dx


def nanmean(a, axis=None):
    """Compute mean ignoring NaN values."""
    return np.nanmean(a, axis=axis)


def nansum(a, axis=None):
    """Compute sum ignoring NaN values."""
    return np.nansum(a, axis=axis)


def nanstd(a, axis=None):
    """Compute standard deviation ignoring NaN values."""
    return np.nanstd(a, axis=axis)


class EDDYParams:
    """Container for AMEDA parameters."""
    
    def __init__(self):
        # Scanning parameters
        self.DH = 0.002  # ssh space between streamlines (m)
        self.nH_lim = 200  # max number of streamlines
        self.n_min = 6  # min points to define a contour
        self.epsil = 0.01  # min increase threshold (1%)
        self.k_vel_decay = 0.97  # velocity decay coefficient
        self.nR_lim = 100  # size limit in Rd
        self.Np = 3  # points for curvature calculation
        self.nrho_lim = 0.2  # curvature limit
        self.lat_min = 5  # minimal latitude
        
        # Double eddy parameters
        self.dc_max = 3.5  # max distance for interaction
        
        # Tracking parameters
        self.V_eddy = 6.5  # km/day
        self.Dt = 10  # days (for AVISO)
        self.cut_off = 0  # days
        self.D_stp = 4  # steps
        self.N_can = 30  # number of candidates
        
        # Detection parameters
        self.K = 0.7  # LNAM threshold
        
        # Grid parameters
        self.grid_ll = True  # lat/lon grid
        self.grid_reg = True  # regular grid
        self.type_detection = 3  # 1=psi, 2=ssh, 3=both
        
        # Physical constants
        self.g = 9.8  # m/s^2
        self.T = 86400  # seconds in day
        self.earth_radius = 6378.137  # km
