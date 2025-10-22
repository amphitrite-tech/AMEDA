"""
Compute 2D fields for eddy detection (LNAM, OW, vorticity, etc.).
"""

import numpy as np


def mod_fields(x, y, mask, u, v, b, f, grid_ll=True):
    """
    Compute 2D fields for eddy detection.
    
    Creates fields of kinetic energy, divergence, vorticity, Okubo-Weiss,
    Local Okubo-Weiss (LOW), and Local Normalized Angular Momentum (LNAM).
    
    Parameters
    ----------
    x, y : ndarray
        Grid coordinates (lon/lat or km)
    mask : ndarray
        Ocean mask (1=ocean, 0=land)
    u, v : ndarray
        Velocity fields (m/s)
    b : ndarray
        Half-length of box for LNAM computation (pixels)
    f : ndarray
        Coriolis parameter (s^-1)
    grid_ll : bool, optional
        True if coordinates are lat/lon
        
    Returns
    -------
    fields : dict
        Dictionary containing:
        - ke: kinetic energy
        - div: divergence
        - vort: vorticity
        - OW: Okubo-Weiss parameter
        - LOW: Local Okubo-Weiss
        - LNAM: Local Normalized Angular Momentum
    """
    print(f" Computing fields...")
    
    # Calculate kinetic energy
    ke = (u**2 + v**2) / 2
    
    # Initialize spatial elements
    dx = np.zeros_like(x)
    dy = np.zeros_like(x)
    dux = np.zeros_like(x)
    duy = np.zeros_like(x)
    dvx = np.zeros_like(x)
    dvy = np.zeros_like(x)
    
    # Calculate spatial elements
    dx[1:-1, 1:-1] = x[1:-1, 2:] - x[1:-1, :-2]
    dy[1:-1, 1:-1] = y[2:, 1:-1] - y[:-2, 1:-1]
    
    if grid_ll:
        # Convert to km
        earth_radius = 6378.137  # km
        R = earth_radius * np.pi / 180  # 111.320 km per degree
        dx = dx * R * np.cos(np.deg2rad(y))
        dy = dy * R
    
    # Convert to meters
    dx = dx * 1000
    dy = dy * 1000
    
    # Calculate velocity gradients
    dux[1:-1, 1:-1] = u[1:-1, 2:] - u[1:-1, :-2]
    duy[1:-1, 1:-1] = u[2:, 1:-1] - u[:-2, 1:-1]
    dvx[1:-1, 1:-1] = v[1:-1, 2:] - v[1:-1, :-2]
    dvy[1:-1, 1:-1] = v[2:, 1:-1] - v[:-2, 1:-1]
    
    # Avoid division by zero
    dx[dx == 0] = np.nan
    dy[dy == 0] = np.nan
    
    # Calculate Okubo-Weiss components
    sn = (dux / dx) - (dvy / dy)  # shear
    ss = (dvx / dx) + (duy / dy)  # strain
    om = (dvx / dx) - (duy / dy)  # vorticity
    
    okubo = sn**2 + ss**2 - om**2  # Okubo-Weiss parameter (s^-2)
    
    # Calculate divergence
    div = (dux / dx) + (dvy / dy)
    
    # Calculate vorticity field
    vorticity = om * np.sign(f)
    
    # Border parameter
    if np.isscalar(b):
        borders = int(b) + 1
    else:
        borders = int(np.max(b)) + 1
    
    # Calculate LNAM and LOW
    print("Computing LNAM...")
    
    L = np.zeros_like(u)
    LOW = np.full_like(u, np.nan)
    
    for i in range(borders, u.shape[0] - borders):
        for ii in range(borders, u.shape[1] - borders):
            if not np.isnan(v[i, ii]):
                # Get local b value
                if np.isscalar(b):
                    b_local = int(b)
                else:
                    b_local = int(b[i, ii])
                
                # Calculate LOW (Local Okubo-Weiss)
                OW = okubo[i-b_local:i+b_local+1, ii-b_local:ii+b_local+1]
                LOW[i, ii] = np.mean(OW[~np.isnan(OW)])
                
                # Calculate LNAM
                xlocal = x[i-b_local:i+b_local+1, ii-b_local:ii+b_local+1]
                ylocal = y[i-b_local:i+b_local+1, ii-b_local:ii+b_local+1]
                ulocal = u[i-b_local:i+b_local+1, ii-b_local:ii+b_local+1]
                vlocal = v[i-b_local:i+b_local+1, ii-b_local:ii+b_local+1]
                
                # Center of the box
                coordcentre = ulocal.shape[0] - b_local
                
                if grid_ll:
                    R = earth_radius * np.pi / 180
                    d_xcentre = (xlocal - xlocal[coordcentre, coordcentre]) * R * \
                                np.cos(np.deg2rad(ylocal))
                    d_ycentre = (ylocal - ylocal[coordcentre, coordcentre]) * R
                else:
                    d_xcentre = xlocal - xlocal[coordcentre, coordcentre]
                    d_ycentre = ylocal - ylocal[coordcentre, coordcentre]
                
                # Angular momentum components
                cross = (d_xcentre * vlocal) - (d_ycentre * ulocal)
                dot = (ulocal * d_xcentre) + (vlocal * d_ycentre)
                produit = np.sqrt(ulocal**2 + vlocal**2) * \
                         np.sqrt(d_xcentre**2 + d_ycentre**2)
                
                cross_sum = np.nansum(cross)
                dot_sum = np.nansum(dot)
                produit_sum = np.nansum(produit)
                sumdp = dot_sum + produit_sum
                
                if sumdp != 0:
                    L[i, ii] = cross_sum / sumdp * np.sign(f[i, ii])
                else:
                    L[i, ii] = 0
    
    # Set NaN to 0 in LNAM
    L[np.isnan(L)] = 0
    
    # Apply mask
    fields = {
        'ke': ke * mask,
        'div': div * mask,
        'vort': vorticity * mask,
        'OW': okubo * mask,
        'LOW': LOW * mask,
        'LNAM': L * mask
    }
    
    print(" Fields computed successfully")
    
    return fields
