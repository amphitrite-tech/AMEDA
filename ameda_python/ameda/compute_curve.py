"""
Compute curvature along a contour.
"""

import numpy as np
from .sw_dist import sw_dist2
from .utilities import inpolygon


def taubin_fit(points):
    """
    Fit a circle using Taubin's method.
    
    Parameters
    ----------
    points : ndarray
        Nx2 array of (x, y) coordinates
        
    Returns
    -------
    params : ndarray
        [xc, yc, r] - center coordinates and radius
    """
    n = points.shape[0]
    
    if n < 3:
        return np.array([0, 0, np.inf])
    
    # Calculate centroid
    x_mean = np.mean(points[:, 0])
    y_mean = np.mean(points[:, 1])
    
    # Center the points
    u = points[:, 0] - x_mean
    v = points[:, 1] - y_mean
    
    # Calculate moments
    Suu = np.sum(u * u)
    Suv = np.sum(u * v)
    Svv = np.sum(v * v)
    Suuu = np.sum(u * u * u)
    Suvv = np.sum(u * v * v)
    Svvv = np.sum(v * v * v)
    Svuu = np.sum(v * u * u)
    
    # Build matrix
    A = np.array([[Suu, Suv], [Suv, Svv]])
    b = np.array([0.5 * (Suuu + Suvv), 0.5 * (Svvv + Svuu)])
    
    try:
        # Solve for center
        uc_vc = np.linalg.solve(A, b)
        xc = uc_vc[0] + x_mean
        yc = uc_vc[1] + y_mean
        
        # Calculate radius
        r = np.sqrt(uc_vc[0]**2 + uc_vc[1]**2 + (Suu + Svv) / n)
        
        return np.array([xc, yc, r])
    except np.linalg.LinAlgError:
        return np.array([x_mean, y_mean, np.inf])


def compute_curve(xy, Np, grid_ll=True):
    """
    Calculate curvature for each point of contour using a fixed number of points.
    
    Parameters
    ----------
    xy : ndarray
        2xN array where xy[0] is x/lon and xy[1] is y/lat
    Np : int
        Number of points on each side for curvature calculation
    grid_ll : bool, optional
        True if coordinates are lat/lon
        
    Returns
    -------
    C : ndarray
        Curvature at each point (1/km)
    P : ndarray
        Segment length along contour (km)
    """
    # Number of total points
    N = xy.shape[1] - 1
    
    # Adjust Np if needed
    if N < Np * 2 + 1:
        Np = max(1, (N - 1) // 2)
    
    # Average coordinates (for reference point in grid_ll case)
    Mx = np.mean(xy[0, :N])
    My = np.mean(xy[1, :N])
    
    # Duplicate the contour for periodic boundary
    if xy[0, 0] == xy[0, -1] and xy[1, 0] == xy[1, -1]:
        xy2 = np.column_stack([xy[:, :-1], xy, xy[:, 1:]])
    else:
        xy2 = np.column_stack([xy, xy, xy])
    
    # Calculate segment lengths
    if grid_ll:
        P = sw_dist2(xy2[1, :], xy2[0, :])
    else:
        P = np.sqrt(np.diff(xy2[0, :])**2 + np.diff(xy2[1, :])**2)
    
    # Initialize curvature
    C = np.zeros(N)
    
    # Sliding curvature for Np-point segments
    for i in range(N):
        # Extract the ith segment
        x = xy2[0, N + i - Np:N + i + Np + 1]
        y = xy2[1, N + i - Np:N + i + Np + 1]
        
        # Coordinates in km if grid_ll
        if grid_ll:
            xs = np.array([Mx, 0])
            ys = np.array([My, 0])
            
            coord = np.zeros((len(x), 2))
            for pt in range(len(x)):
                xs[1] = x[pt]
                ys[1] = y[pt]
                
                # Distance in km from the barycenter
                dist_x = sw_dist2(np.array([My, My]), xs)
                dist_y = sw_dist2(ys, np.array([Mx, Mx]))
                
                coord[pt, 0] = np.sign(np.diff(xs)[0]) * (dist_x[0] if len(dist_x) > 0 else 0)
                coord[pt, 1] = np.sign(np.diff(ys)[0]) * (dist_y[0] if len(dist_y) > 0 else 0)
        else:
            coord = np.column_stack([x, y])
        
        try:
            # Fit a circle using Taubin method
            params = taubin_fit(coord)
            R = params[2]
            
            if not np.isfinite(R) or R == 0:
                C[i] = 0
            else:
                # Determine if center is inside or outside contour
                IN = inpolygon(np.mean(x), np.mean(y), xy[0, :], xy[1, :])
                if IN:
                    C[i] = 1 / R
                else:
                    C[i] = -1 / R
        except:
            C[i] = 0
    
    # Truncate P to match C
    P = P[:N]
    
    return C, P
