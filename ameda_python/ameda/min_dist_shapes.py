"""
Calculate minimum distance between two eddy shapes.
"""

import numpy as np
from .sw_dist import sw_dist2


def min_dist_shapes(xy1, xy2, grid_ll=True):
    """
    Calculate the minimal distance in km between two eddy edges.
    
    Parameters
    ----------
    xy1, xy2 : ndarray
        2xN arrays where first row is x/lon and second row is y/lat
        Contour polygon coordinates from eddy detection
    grid_ll : bool, optional
        True if coordinates are (lon, lat), False if in km
        
    Returns
    -------
    ds : float
        Minimal distance between the two shapes in km
        
    Examples
    --------
    >>> # Two circular eddies separated by some distance
    >>> theta = np.linspace(0, 2*np.pi, 50)
    >>> xy1 = np.array([100*np.cos(theta), 100*np.sin(theta)])
    >>> xy2 = np.array([300 + 100*np.cos(theta), 100*np.sin(theta)])
    >>> dist = min_dist_shapes(xy1, xy2, grid_ll=False)
    >>> # dist should be ~100 km (distance between circle centers - 2*radius)
    """
    # Get lengths
    n1 = xy1.shape[1]
    n2 = xy2.shape[1]
    
    # Initialize distance matrix
    ds = np.full((n1, n2), np.nan)
    
    # Double loop to compute all pairwise distances
    # (This is the most straightforward approach, though not the most efficient)
    for i in range(n1):
        for j in range(n2):
            if grid_ll:
                # Use spherical distance for lat/lon
                ys = np.array([xy1[1, i], xy2[1, j]])
                xs = np.array([xy1[0, i], xy2[0, j]])
                dist = sw_dist2(ys, xs)
                ds[i, j] = dist[0] if len(dist) > 0 else np.nan
            else:
                # Use Euclidean distance for Cartesian coordinates
                dx = xy2[0, j] - xy1[0, i]
                dy = xy2[1, j] - xy1[1, i]
                ds[i, j] = np.sqrt(dx**2 + dy**2)
    
    # Return minimum distance
    if np.all(np.isnan(ds)):
        return np.nan
    
    return np.nanmin(ds)


def min_dist_shapes_vectorized(xy1, xy2, grid_ll=True):
    """
    Vectorized version of min_dist_shapes for better performance.
    
    This is an optimized version that computes distances more efficiently.
    
    Parameters
    ----------
    xy1, xy2 : ndarray
        2xN arrays of contour coordinates
    grid_ll : bool, optional
        True if using lat/lon coordinates
        
    Returns
    -------
    ds : float
        Minimal distance in km
    """
    if not grid_ll:
        # Cartesian case - can vectorize easily
        # Broadcast to compute all pairwise distances
        dx = xy2[0, :, np.newaxis] - xy1[0, np.newaxis, :]
        dy = xy2[1, :, np.newaxis] - xy1[1, np.newaxis, :]
        distances = np.sqrt(dx**2 + dy**2)
        return np.min(distances)
    else:
        # For lat/lon, use the original loop method
        # (spherical distance doesn't vectorize easily)
        return min_dist_shapes(xy1, xy2, grid_ll=True)
