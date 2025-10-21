"""
Integrate velocity along a contour.
"""

import numpy as np
from scipy.interpolate import RegularGridInterpolator
from .sw_dist import sw_dist2


def integrate_vel(x, y, u, v, xdata, ydata, grid_ll=True):
    """
    Project velocity field onto a contour and integrate to get average velocity.
    
    Parameters
    ----------
    x, y : ndarray
        Grid coordinates
    u, v : ndarray
        Velocity components
    xdata, ydata : ndarray
        Contour coordinates
    grid_ll : bool, optional
        True if using lat/lon coordinates
        
    Returns
    -------
    V : float
        Mean velocity along contour (m/s)
    """
    # Interpolate velocity to contour points
    if grid_ll:
        # For irregular grids or lat/lon, use nearest neighbor or linear interpolation
        from scipy.interpolate import griddata
        
        points = np.column_stack([x.flatten(), y.flatten()])
        u_interp = griddata(points, u.flatten(), np.column_stack([xdata, ydata]), method='linear')
        v_interp = griddata(points, v.flatten(), np.column_stack([xdata, ydata]), method='linear')
    else:
        # For regular grids
        if x.ndim == 1:
            x_vec, y_vec = x, y
        else:
            x_vec, y_vec = x[0, :], y[:, 0]
        
        interp_u = RegularGridInterpolator((y_vec, x_vec), u, bounds_error=False, fill_value=0)
        interp_v = RegularGridInterpolator((y_vec, x_vec), v, bounds_error=False, fill_value=0)
        
        points = np.column_stack([ydata, xdata])
        u_interp = interp_u(points)
        v_interp = interp_v(points)
    
    # Handle NaN values
    u_interp = np.nan_to_num(u_interp, 0)
    v_interp = np.nan_to_num(v_interp, 0)
    
    # Calculate velocity magnitude
    vel_magnitude = np.sqrt(u_interp**2 + v_interp**2)
    
    # Calculate tangent vectors along contour
    if grid_ll:
        # Calculate distances between points
        distances = sw_dist2(ydata, xdata)  # km
        distances = np.append(distances, distances[-1])  # extend for last segment
    else:
        dx = np.diff(xdata)
        dy = np.diff(ydata)
        distances = np.sqrt(dx**2 + dy**2)
        distances = np.append(distances, distances[-1])
    
    # Calculate tangent directions
    dx = np.diff(np.append(xdata, xdata[0]))
    dy = np.diff(np.append(ydata, ydata[0]))
    
    if grid_ll:
        # Approximate tangent for lat/lon
        tangent_mag = np.sqrt(dx**2 + dy**2)
    else:
        tangent_mag = np.sqrt(dx**2 + dy**2)
    
    tangent_mag[tangent_mag == 0] = 1  # Avoid division by zero
    tx = dx / tangent_mag
    ty = dy / tangent_mag
    
    # Project velocity onto tangent
    vel_tangent = np.abs(u_interp * tx + v_interp * ty)
    
    # Calculate mean velocity (integrate and divide by perimeter)
    if len(distances) > 0 and np.sum(distances) > 0:
        V = np.sum(vel_tangent * distances) / np.sum(distances) * 1000  # convert km to m
    else:
        V = np.mean(vel_magnitude) if len(vel_magnitude) > 0 else 0
    
    return V
