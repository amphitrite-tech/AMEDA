"""
Calculate mean radius, perimeter, and area of a closed contour.
"""

import numpy as np
from .sw_dist import sw_dist2


def mean_radius(xy, grid_ll=True):
    """
    Compute the mean radius (R), perimeter (P), surface area (A) of a closed contour.
    
    Parameters
    ----------
    xy : ndarray
        2xN array where first row is x/lon and second row is y/lat
    grid_ll : bool, optional
        True if coordinates are (lon, lat), False if in km
        
    Returns
    -------
    R : ndarray
        Mean radius (4 different calculations)
        R[0] = radius of equivalent circle
        R[1] = radius weighted by surface area
        R[2] = max radius from barycenter
        R[3] = mean radius from barycenter
    A : float
        Surface area
    P : float
        Perimeter
    ll : ndarray
        Barycenter coordinates [x, y]
    """
    # Size of the polygon
    lim = xy.shape[1] - 1
    
    # Barycenter computation
    somme_x = np.sum(xy[0, :lim])
    somme_y = np.sum(xy[1, :lim])
    
    ll = np.array([somme_x / lim, somme_y / lim])
    
    # Initialize arrays
    distance = np.zeros(lim + 1)
    aire = np.zeros(lim)
    
    # Distance from barycenter to every point
    xs = np.array([ll[0], 0])
    ys = np.array([ll[1], 0])
    
    for point in range(lim + 1):
        xs[1] = xy[0, point]
        ys[1] = xy[1, point]
        
        if grid_ll:
            dist_result = sw_dist2(ys, xs)
            distance[point] = dist_result[0] if len(dist_result) > 0 else 0
        else:
            diff_val = np.sqrt(np.diff(xs)**2 + np.diff(ys)**2)
            distance[point] = float(diff_val[0]) if len(diff_val) > 0 else 0
    
    # Distance between consecutive points
    if grid_ll:
        distance2 = sw_dist2(xy[1, :], xy[0, :])
    else:
        distance2 = np.sqrt(np.diff(xy[0, :])**2 + np.diff(xy[1, :])**2)
    
    # Perimeter
    P = np.sum(distance2)
    
    # Surface area using Heron's formula for triangles
    for point in range(lim):
        a = distance[point]
        b = distance[point + 1]
        c = distance2[point] if point < len(distance2) else distance2[-1]
        s = (a + b + c) / 2
        aire[point] = np.sqrt(np.maximum(0, s * (s - a) * (s - b) * (s - c)))
    
    A = np.sum(np.real(aire))
    
    # Mean radius computation (4 different methods)
    R = np.zeros(4)
    
    # Radius of equivalent circle
    R[0] = np.sqrt(A / np.pi)
    
    # Radius weighted by surface area
    param = np.zeros(lim)
    for point in range(lim):
        rayonmoy = (distance[point] + distance[point + 1]) / 2
        param[point] = aire[point] * rayonmoy
    
    if A > 0:
        R[1] = np.sum(param) / A
    else:
        R[1] = 0
    
    # Max radius
    R[2] = np.max(distance[:lim])
    
    # Mean radius
    R[3] = np.mean(distance[:lim])
    
    return R, A, P, ll
