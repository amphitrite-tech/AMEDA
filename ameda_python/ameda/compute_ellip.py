"""
Compute barycenter and fit ellipse to a polygon.
"""

import numpy as np
from .sw_dist import sw_dist2


def fit_ellipse_linear(coord):
    """
    Fit an ellipse to 2D points using linear least squares.
    
    Parameters
    ----------
    coord : ndarray
        Nx2 array of (x, y) coordinates
        
    Returns
    -------
    z : ndarray
        Center coordinates [xc, yc]
    a : float
        Semi-major axis
    b : float
        Semi-minor axis
    theta : float
        Orientation angle (radians)
    """
    n = coord.shape[0]
    
    if n < 5:
        return np.array([np.nan, np.nan]), np.nan, np.nan, np.nan
    
    # Normalize coordinates
    mean_coord = np.mean(coord, axis=0)
    coord_centered = coord - mean_coord
    
    # Build design matrix
    x = coord_centered[:, 0]
    y = coord_centered[:, 1]
    
    D = np.column_stack([x**2, x*y, y**2, x, y, np.ones(n)])
    
    # Constraint matrix for ellipse
    C = np.zeros((6, 6))
    C[0, 2] = 2
    C[1, 1] = -1
    C[2, 0] = 2
    
    try:
        # Solve generalized eigenvalue problem
        _, eigvec = np.linalg.eig(np.linalg.inv(D.T @ D) @ C)
        
        # Find positive eigenvalue
        cond = 4 * eigvec[0, :] * eigvec[2, :] - eigvec[1, :]**2
        valid_idx = np.where(cond > 0)[0]
        
        if len(valid_idx) == 0:
            return np.array([np.nan, np.nan]), np.nan, np.nan, np.nan
        
        a_coeffs = eigvec[:, valid_idx[0]]
        
        # Extract ellipse parameters
        A, B, C, D, E, F = a_coeffs
        
        # Calculate center
        den = B**2 - 4*A*C
        if den == 0:
            return np.array([np.nan, np.nan]), np.nan, np.nan, np.nan
        
        xc = (2*C*D - B*E) / den
        yc = (2*A*E - B*D) / den
        
        # Calculate axes and angle
        theta = 0.5 * np.arctan2(B, A - C)
        
        # Calculate semi-axes
        cos_t = np.cos(theta)
        sin_t = np.sin(theta)
        
        ap = A * cos_t**2 + B * cos_t * sin_t + C * sin_t**2
        cp = A * sin_t**2 - B * cos_t * sin_t + C * cos_t**2
        fp = F + A * xc**2 + B * xc * yc + C * yc**2 + D * xc + E * yc
        
        if ap * fp < 0 and cp * fp < 0:
            a = np.sqrt(-fp / ap)
            b = np.sqrt(-fp / cp)
        else:
            return np.array([np.nan, np.nan]), np.nan, np.nan, np.nan
        
        # Ensure a >= b
        if a < b:
            a, b = b, a
            theta = theta + np.pi / 2
        
        # Return center in original coordinates
        z = np.array([xc, yc]) + mean_coord
        
        return z, a, b, theta
        
    except:
        return np.array([np.nan, np.nan]), np.nan, np.nan, np.nan


def compute_ellip(xy, grid_ll=True):
    """
    Compute the barycenter of a closed polygon and fit an ellipse.
    
    Parameters
    ----------
    xy : ndarray
        2xN array where xy[0] is x/lon and xy[1] is y/lat
    grid_ll : bool, optional
        True if coordinates are (lon, lat), False if in km
        
    Returns
    -------
    xbary, ybary : float
        Barycenter coordinates
    z : ndarray
        Ellipse center [xc, yc]
    a : float
        Semi-major axis (km)
    b : float
        Semi-minor axis (km)
    theta : float
        Orientation angle (radians)
    lim : int
        Number of vertices
    """
    # Size of polygon
    lim = xy.shape[1] - 1
    
    # Barycenter computation
    xbary = np.mean(xy[0, :lim])
    ybary = np.mean(xy[1, :lim])
    
    # Ellipse fitting requires at least 5 points
    if lim < 5:
        return xbary, ybary, np.array([np.nan, np.nan]), np.nan, np.nan, np.nan, lim
    
    try:
        # Convert to coordinates relative to barycenter
        if grid_ll:
            xs = np.array([xbary, 0])
            ys = np.array([ybary, 0])
            
            coord = np.zeros((lim, 2))
            for pt in range(lim):
                xs[1] = xy[0, pt]
                ys[1] = xy[1, pt]
                
                # Distances in km
                dist_x = sw_dist2(np.array([ybary, ybary]), xs)
                dist_y = sw_dist2(ys, np.array([xbary, xbary]))
                
                coord[pt, 0] = np.sign(np.diff(xs)[0]) * (dist_x[0] if len(dist_x) > 0 else 0)
                coord[pt, 1] = np.sign(np.diff(ys)[0]) * (dist_y[0] if len(dist_y) > 0 else 0)
            
            z, a, b, theta = fit_ellipse_linear(coord)
            z = np.array([xbary, ybary])  # Return barycenter for grid_ll
        else:
            coord = xy[:, :lim].T
            z, a, b, theta = fit_ellipse_linear(coord)
        
        # Check validity
        if a < 0 or b < 0 or np.isnan(a) or np.isnan(b):
            return xbary, ybary, np.array([np.nan, np.nan]), np.nan, np.nan, np.nan, lim
        
        return xbary, ybary, z, a, b, theta, lim
        
    except:
        return xbary, ybary, np.array([np.nan, np.nan]), np.nan, np.nan, np.nan, lim
