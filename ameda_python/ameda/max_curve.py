"""
Compute eddy shapes by finding maximum velocity contours.
"""

import numpy as np
import matplotlib.pyplot as plt
from .scan_lines import scan_lines
from .integrate_vel import integrate_vel
from .mean_radius import mean_radius
from .compute_curve import compute_curve
from .utilities import inpolygon


def max_curve(x, y, psi, xy_ci, xy_cj, type_cts, xy_ctsi, xy_ctsj, u, v, Rd,
              H, n_min, k_vel_decay, nR_lim, Np, nrho_lim, grid_ll=True):
    """
    Compute 3 different eddy shapes based on velocity contours.
    
    Parameters
    ----------
    x, y : ndarray
        Coordinate arrays
    psi : ndarray
        Streamfunction or SSH field
    xy_ci, xy_cj : float
        Main center coordinates
    type_cts : array
        Types of all centers (1=cyclonic, -1=anticyclonic)
    xy_ctsi, xy_ctsj : array
        Coordinates of all centers
    u, v : ndarray
        Velocity components
    Rd : float
        Deformation radius (km)
    H : array
        Streamline levels to scan
    n_min : int
        Minimum points for contour
    k_vel_decay : float
        Velocity decay coefficient
    nR_lim : float
        Size limit in Rd units
    Np : int
        Points for curvature
    nrho_lim : float
        Curvature limit
    grid_ll : bool
        Using lat/lon grid
        
    Returns
    -------
    cd : ndarray
        Centers coordinates (2x2 for double eddy)
    eddy_lim : list
        Eddy contours [speed_radius, double, last]
    lines : ndarray
        Streamlines features
    rmax : ndarray
        Radii (3 values)
    velmax : ndarray
        Maximum velocities (3 values)
    tau : ndarray
        Turnover times (3 values)
    eta : ndarray
        SSH/PSI levels (3 values)
    nrho : ndarray
        Curvature parameters (3 values)
    large : ndarray
        Flags for largest contours (2 values)
    """
    # Compute contour lines
    if x.ndim == 2 and np.all(x[0, :] == x[-1, :]) and np.all(y[:, 0] == y[:, -1]):
        # Regular grid
        CS = plt.contour(x[0, :], y[:, 0], psi, levels=H)
    else:
        # Irregular grid
        CS = plt.contour(x, y, psi, levels=H)
    
    C = CS.allsegs
    plt.close()
    
    # Convert matplotlib contours to our format
    C_matrix = []
    for level_idx, level_contours in enumerate(C):
        for contour in level_contours:
            if len(contour) > 0:
                npts = len(contour)
                # Format: [level, npoints, x1, y1, x2, y2, ...]
                level_val = H[level_idx] if level_idx < len(H) else 0
                C_matrix.append([level_val, npts])
                C_matrix.extend(contour.flatten().tolist())
    
    if len(C_matrix) == 0:
        # No contours found
        cd = np.full((2, 2), np.nan)
        eddy_lim = [None, None, None]
        lines = np.array([])
        large = np.array([np.nan, np.nan])
        velmax = np.zeros(3)
        rmax = np.full(3, np.nan)
        tau = np.full(3, np.nan)
        eta = np.full(3, np.nan)
        nrho = np.full(3, np.nan)
        return cd, eddy_lim, lines, rmax, velmax, tau, eta, nrho, large
    
    # Convert to numpy array for scan_lines
    C_array = np.array(C_matrix).reshape(-1, 1).T
    
    # Rearrange contours
    isolines, lvl = scan_lines(C_array)
    
    # Initialize variables
    cd = np.full((2, 2), np.nan)
    eddy_lim = [None, None, None]
    lines = []
    large = np.array([np.nan, np.nan])
    velmax = np.zeros(3)
    rmax = np.full(3, np.nan)
    tau = np.full(3, np.nan)
    eta = np.full(3, np.nan)
    nrho = np.full(3, np.nan)
    
    # Starting values
    Rmax = np.zeros(2)
    Vmax = np.zeros(2)
    Tmin = 9999
    nrhomax = np.ones(2)
    linesmax = None
    etamax = 0
    
    # Scan all isolines
    i = 0
    I = 0
    
    while i < len(isolines):
        xdata = isolines[i]['x']
        ydata = isolines[i]['y']
        
        # Check if contour is closed and contains center
        if (len(xdata) >= n_min and xdata[0] == xdata[-1] and ydata[0] == ydata[-1] and
            inpolygon(xy_ci, xy_cj, xdata, ydata)):
            
            # Check if contour doesn't contain land
            in_eddy = inpolygon(x, y, xdata, ydata)
            if not np.any(np.isnan(u[in_eddy])):
                
                # Find centers in contour
                IN = inpolygon(xy_ctsi, xy_ctsj, xdata, ydata)
                p = np.where(IN)[0]
                nc = len(p)  # number of centers
                
                # Process contours with 1 or 2 centers
                if nc <= 2 and nc > 0 and np.sum(type_cts[p]) != 0:
                    
                    # Calculate velocity
                    V = integrate_vel(x, y, u, v, xdata, ydata, grid_ll)
                    
                    # Calculate radius
                    R, _, _, _ = mean_radius(np.array([xdata, ydata]), grid_ll)
                    
                    # Calculate curvature
                    C_curv, P = compute_curve(np.array([xdata, ydata]), Np, grid_ll)
                    
                    # Calculate turnover time
                    T = np.sum(P) * 1000 / V / 3600 / 24 if V > 0 else np.inf  # days
                    
                    # Calculate negative curvature parameter
                    N = np.abs(np.sum(P[C_curv < 0] * C_curv[C_curv < 0]) / (2 * np.pi))
                    
                    # Record streamline features
                    lines.append([nc, lvl[i] if i < len(lvl) else 0, R[0], V, T, N])
                    
                    # Record last shape for single center
                    if nc == 1:
                        velmax[2] = V
                        rmax[2] = R[0]
                        eddy_lim[2] = np.array([xdata, ydata])
                        eta[2] = lvl[i] if i < len(lvl) else 0
                        tau[2] = T
                        nrho[2] = N
                    elif nc == 2 and np.isnan(cd[0, 0]):
                        cd = np.array([[xy_ctsi[p[0]], xy_ctsi[p[1]]], 
                                      [xy_ctsj[p[0]], xy_ctsj[p[1]]]])
                    
                    # Check for velocity maximum
                    if Vmax[0] == 0:
                        if nc == 1 and R[0] < nR_lim * Rd:
                            Vmax[0] = V
                            Tmin = min(Tmin, T)
                            velmax[2] = V
                            rmax[2] = R[0]
                            eddy_lim[2] = np.array([xdata, ydata])
                            eta[2] = lvl[i] if i < len(lvl) else 0
                            tau[2] = Tmin
                            nrho[2] = N
                        else:
                            break
                    elif V > Vmax[nc-1]:
                        I = i
                        if nc == 2 or (R[0] < nR_lim * Rd and N < nrho_lim):
                            Rmax[nc-1] = R[0]
                            Vmax[nc-1] = V
                            Tmin = min(Tmin, T)
                            linesmax = np.array([xdata, ydata])
                            etamax = lvl[i] if i < len(lvl) else 0
                            nrhomax[nc-1] = N
                        
                        if not np.isnan(large[nc-1]):
                            large[nc-1] = 1
                            if nc == 2 or (Rmax[0] < nR_lim * Rd and nrhomax[0] < nrho_lim):
                                rmax[nc-1] = Rmax[nc-1]
                                velmax[nc-1] = Vmax[nc-1]
                                tau[nc-1] = Tmin
                                eddy_lim[nc-1] = linesmax
                                eta[nc-1] = etamax
                                nrho[nc-1] = nrhomax[nc-1]
                    
                    elif V < k_vel_decay * Vmax[nc-1]:
                        if large[nc-1] == 1 and i - I > 1:
                            large[nc-1] = 0
                        elif Vmax[nc-1] > velmax[nc-1] and velmax[nc-1] != 0:
                            if nc == 2 or (Rmax[0] < nR_lim * Rd and nrhomax[0] < nrho_lim):
                                rmax[nc-1] = Rmax[nc-1]
                                velmax[nc-1] = Vmax[nc-1]
                                eddy_lim[nc-1] = linesmax
                                tau[nc-1] = Tmin
                                eta[nc-1] = etamax
                                nrho[nc-1] = nrhomax[nc-1]
                else:
                    break
            else:
                break
        
        i += 1
    
    lines = np.array(lines) if lines else np.array([])
    
    return cd, eddy_lim, lines, rmax, velmax, tau, eta, nrho, large
