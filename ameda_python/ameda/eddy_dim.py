"""
Compute eddy dimensions and shapes.
"""

import numpy as np
import matplotlib.pyplot as plt
from .compute_psi import compute_psi
from .max_curve import max_curve
from .utilities import inpolygon, EDDYParams


def eddy_dim(u, v, ssh, mask, x, y, centers, ii, farea, Rdarea, bxarea, params=None):
    """
    Compute the shape of the eddy defined by the iith center.
    
    Parameters
    ----------
    u, v : ndarray
        2D velocity fields
    ssh : ndarray
        2D SSH field (can be None)
    mask : ndarray
        2D mask array
    x, y : ndarray
        Grid coordinates
    centers : dict
        Potential eddy center structure
    ii : int
        Index of the main eddy center
    farea : float
        Coriolis parameter at center
    Rdarea : float
        Deformation radius
    bxarea : int
        Box size for shape computation
    params : EDDYParams, optional
        Parameters object
        
    Returns
    -------
    CD : ndarray
        Centers coordinates
    xy : list
        Eddy shapes [speed_radius, double, last]
    allines : ndarray
        Streamlines features
    rmax : ndarray
        Radii
    velmax : ndarray
        Maximum velocities
    tau : ndarray
        Turnover times
    deta : ndarray
        SSH deformations
    nrho : ndarray
        Curvature parameters
    large : ndarray
        Flags for largest contours
    warn : bool
        Warning flag
    calcul : int
        Calculation type (0=ssh, 1=psi)
    """
    if params is None:
        params = EDDYParams()
    
    bx = bxarea
    Rd = Rdarea
    f = np.abs(farea)
    
    # Main center info
    type_c = centers['type'][ii]
    xy_cj = centers['y'][ii]
    xy_ci = centers['x'][ii]
    C_I = centers['i'][ii]
    C_J = centers['j'][ii]
    
    # All centers
    type_cts = centers['type']
    centers_y = centers['y']
    centers_x = centers['x']
    
    # Resize arrays to smaller domain
    j_min, j_max = max(C_J - bx, 0), min(C_J + bx + 1, y.shape[0])
    i_min, i_max = max(C_I - bx, 0), min(C_I + bx + 1, x.shape[1])
    
    y = y[j_min:j_max, i_min:i_max]
    x = x[j_min:j_max, i_min:i_max]
    mask = mask[j_min:j_max, i_min:i_max]
    v = v[j_min:j_max, i_min:i_max]
    u = u[j_min:j_max, i_min:i_max]
    
    if ssh is not None and params.type_detection >= 2:
        ssh = ssh[j_min:j_max, i_min:i_max]
        Hs = np.arange(np.floor(np.nanmin(ssh)), np.ceil(np.nanmax(ssh)), params.DH)
        if len(Hs) > params.nH_lim:
            Hs = Hs[:params.nH_lim]
    
    # Find center in small domain
    cj, ci = np.where((y == xy_cj) & (x == xy_ci))
    if len(cj) == 0:
        # Center not found
        warn = True
        CD = np.array([])
        xy = [None, None, None]
        allines = np.array([])
        rmax = np.full(3, np.nan)
        velmax = np.zeros(3)
        tau = np.full(3, np.nan)
        deta = np.full(3, np.nan)
        nrho = np.full(3, np.nan)
        large = np.array([np.nan, np.nan])
        return CD, xy, allines, rmax, velmax, tau, deta, nrho, large, warn, 0
    
    cj, ci = cj[0], ci[0]
    
    # Find all centers in small domain
    bbox = [x[0, 0], x[0, -1], x[-1, -1], x[-1, 0], x[0, 0]]
    bbox_y = [y[0, 0], y[0, -1], y[-1, -1], y[-1, 0], y[0, 0]]
    in_box = inpolygon(centers_x, centers_y, bbox, bbox_y)
    
    type_cts = type_cts[in_box]
    xy_ctsj = centers_y[in_box]
    xy_ctsi = centers_x[in_box]
    
    # Compute PSI or use SSH
    calcul = 0
    cd, eddy_lim, lines, rmax, velmax, tau, eta, nrho, large = (None, None, None, 
                                                                  None, None, None, 
                                                                  None, None, None)
    
    if params.type_detection == 1 or params.type_detection == 3:
        # Compute PSI
        u_copy = u.copy()
        v_copy = v.copy()
        u_copy[np.isnan(u_copy)] = 0
        v_copy[np.isnan(v_copy)] = 0
        
        psi = compute_psi(x, y, mask, u_copy * f / params.g * 1e3, 
                         v_copy * f / params.g * 1e3, ci, cj, params.grid_ll)
        
        H = np.arange(np.floor(np.nanmin(psi)), np.ceil(np.nanmax(psi)), params.DH)
        if len(H) > params.nH_lim:
            H = H[:params.nH_lim]
        
        cd, eddy_lim, lines, rmax, velmax, tau, eta, nrho, large = max_curve(
            x, y, psi, xy_ci, xy_cj, type_cts, xy_ctsi, xy_ctsj, u, v, Rd,
            H, params.n_min, params.k_vel_decay, params.nR_lim, params.Np, 
            params.nrho_lim, params.grid_ll)
        calcul = 1
    
    if params.type_detection == 2 or (params.type_detection == 3 and np.isnan(large[0])):
        # Use SSH
        if ssh is not None:
            cd, eddy_lim, lines, rmax, velmax, tau, eta, nrho, large = max_curve(
                x, y, ssh, xy_ci, xy_cj, type_cts, xy_ctsi, xy_ctsj, u, v, Rd,
                Hs, params.n_min, params.k_vel_decay, params.nR_lim, params.Np,
                params.nrho_lim, params.grid_ll)
            calcul = 0
    
    # Calculate deta
    deta = np.full(3, np.nan)
    psi_field = psi if calcul == 1 else ssh
    
    if eddy_lim is not None and eddy_lim[2] is not None:
        warn = False
        CD = cd
        xy = eddy_lim
        allines = lines
        
        # Compute deta for last contour
        in_eddy = inpolygon(x, y, xy[2][0, :], xy[2][1, :])
        if type_c == -1:  # anticyclone
            deta[2] = np.nanmax(psi_field[in_eddy]) - eta[2]
        elif type_c == 1:  # cyclone
            deta[2] = np.nanmin(psi_field[in_eddy]) - eta[2]
        
        # Compute deta for speed radius
        if xy[0] is not None:
            in_eddy = inpolygon(x, y, xy[0][0, :], xy[0][1, :])
            if type_c == -1:
                deta[0] = np.nanmax(psi_field[in_eddy]) - eta[0]
            elif type_c == 1:
                deta[0] = np.nanmin(psi_field[in_eddy]) - eta[0]
        
        # Compute deta for double eddy
        if xy[1] is not None:
            in_eddy = inpolygon(x, y, xy[1][0, :], xy[1][1, :])
            if type_c == -1:
                deta[1] = np.nanmax(psi_field[in_eddy]) - eta[1]
            elif type_c == 1:
                deta[1] = np.nanmin(psi_field[in_eddy]) - eta[1]
    else:
        warn = True
        CD = np.array([])
        xy = [None, None, None]
        allines = np.array([])
    
    return CD, xy, allines, rmax, velmax, tau, deta, nrho, large, warn, calcul
