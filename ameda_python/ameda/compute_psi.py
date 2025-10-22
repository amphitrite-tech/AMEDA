"""
Compute streamfunction (PSI) field from velocity components.
"""

import numpy as np
try:
    from scipy.integrate import cumulative_trapezoid as cumtrapz
except ImportError:
    from scipy.integrate import cumtrapz
from .sw_dist import sw_dist2


def compute_psi(x, y, mask, u, v, ci, cj, grid_ll=True):
    """
    Compute the streamfunction (PSI) field by spatially integrating u and v components.
    
    The function integrates velocity in the geostrophic equilibrium within 4 areas
    around a detected eddy center (ci, cj). The assumption is that in the presence
    of an eddy, the velocity field has weak divergence, so contours of PSI are
    tangential to the velocity vectors.
    
    Parameters
    ----------
    x, y : ndarray
        NxM matrices of coordinates (lon/lat or km)
    mask : ndarray
        NxM mask array (1=ocean, 0=land)
    u, v : ndarray
        NxM matrices of velocity components (m/s)
    ci, cj : int
        Indices of the center in the grid
    grid_ll : bool, optional
        True if coordinates are in (lon, lat), False if in km
        
    Returns
    -------
    psi : ndarray
        NxM matrix of streamfunction field
    """
    # Build mask (convert 0 to nan)
    mask = mask.copy().astype(float)
    mask[mask == 0] = np.nan
    N0, M0 = mask.shape
    
    # Set NaN values to 0 in velocity
    u = np.nan_to_num(u, 0)
    v = np.nan_to_num(v, 0)
    
    # Prepare distance matrices for the 4 domains
    km_di = np.full((x.shape[0], x.shape[1] - 1), np.nan)
    km_dj = np.full((y.shape[0] - 1, y.shape[1]), np.nan)
    
    # Calculate distances along i direction (longitude)
    for i in range(x.shape[0]):
        if grid_ll:
            km_di[i, :] = sw_dist2(y[i, :], x[i, :])
        else:
            km_di[i, :] = np.sqrt(np.diff(x[i, :])**2 + np.diff(y[i, :])**2)
    
    # Calculate distances along j direction (latitude)
    for i in range(y.shape[1]):
        if grid_ll:
            km_dj[:, i] = sw_dist2(y[:, i], x[:, i])
        else:
            km_dj[:, i] = np.sqrt(np.diff(x[:, i])**2 + np.diff(y[:, i])**2)
    
    # Lengths for the 4 domains (NE, SE, NW, SW)
    lx1 = u[cj:, :].shape[0]
    lx2 = u[:cj+1, :].shape[0]
    ly1 = u[:, ci:].shape[1]
    ly2 = u[:, :ci+1].shape[1]
    
    # Adjust km_di and km_dj for trapz integration starting at ci, cj
    di = np.column_stack([
        km_di[:, :ci],
        np.zeros((lx1 + lx2 - 1, 1)),
        km_di[:, ci:]
    ])
    dj = np.vstack([
        km_dj[:cj, :],
        np.zeros((1, ly1 + ly2 - 1)),
        km_dj[cj:, :]
    ])
    
    # Integrate first row of v along x (first term of equations A1)
    cx1 = cumtrapz(v[cj, ci:], initial=0) * di[cj, ci:]
    cx2 = -cumtrapz(v[cj, ci::-1], initial=0) * di[cj, ci::-1]
    
    # Integrate first column of u along y (first term of equations A2)
    cy1 = -cumtrapz(u[cj:, ci], initial=0) * dj[cj:, ci]
    cy2 = cumtrapz(u[cj::-1, ci], initial=0) * dj[cj::-1, ci]
    
    # Expand vectors into matrices to compute PSI
    mcx11 = np.tile(cx1, (lx1, 1))
    mcx12 = np.tile(cx1, (lx2, 1))
    mcx21 = np.tile(cx2, (lx1, 1))
    mcx22 = np.tile(cx2, (lx2, 1))
    mcy11 = np.tile(cy1.reshape(-1, 1), (1, ly1))
    mcy12 = np.tile(cy1.reshape(-1, 1), (1, ly2))
    mcy21 = np.tile(cy2.reshape(-1, 1), (1, ly1))
    mcy22 = np.tile(cy2.reshape(-1, 1), (1, ly2))
    
    # PSI from integrating v first then u (4 parts of eq. A1)
    psi_xy11 = mcx11 - cumtrapz(u[cj:, ci:], axis=0, initial=0) * dj[cj:, ci:]
    psi_xy12 = mcx12 + cumtrapz(u[cj::-1, ci:], axis=0, initial=0) * dj[cj::-1, ci:]
    psi_xy21 = mcx21 - cumtrapz(u[cj:, ci::-1], axis=0, initial=0) * dj[cj:, ci::-1]
    psi_xy22 = mcx22 + cumtrapz(u[cj::-1, ci::-1], axis=0, initial=0) * dj[cj::-1, ci::-1]
    
    # Concatenate 4 parts (NE, SE, NW, SW)
    psi_xy = np.block([
        [psi_xy22[::-1, ::-1][1:, 1:], psi_xy12[::-1, :][1:, :]],
        [psi_xy21[:, ::-1][:, 1:], psi_xy11]
    ])
    
    # PSI from integrating u first then v (4 parts of eq. A2)
    psi_yx11 = mcy11 + cumtrapz(v[cj:, ci:], axis=1, initial=0) * di[cj:, ci:]
    psi_yx21 = mcy12 - cumtrapz(v[cj:, ci::-1], axis=1, initial=0) * di[cj:, ci::-1]
    psi_yx12 = mcy21 + cumtrapz(v[cj::-1, ci:], axis=1, initial=0) * di[cj::-1, ci:]
    psi_yx22 = mcy22 - cumtrapz(v[cj::-1, ci::-1], axis=1, initial=0) * di[cj::-1, ci::-1]
    
    # Concatenate 4 parts (NE, SE, NW, SW)
    psi_yx = np.block([
        [psi_yx22[::-1, ::-1][1:, 1:], psi_yx12[::-1, :][1:, :]],
        [psi_yx21[:, ::-1][:, 1:], psi_yx11]
    ])
    
    # Computed PSI as average between the two
    psi = (psi_xy + psi_yx) / 2 * mask
    
    # Enlarge PSI into land by 1 pixel (average of 9 neighbors)
    mask_binary = np.nan_to_num(mask, 0).astype(bool)
    
    for i in range(N0):
        for j in range(M0):
            if not mask_binary[i, j]:
                i_min, i_max = max(i-1, 0), min(i+2, N0)
                j_min, j_max = max(j-1, 0), min(j+2, M0)
                neighbors = mask[i_min:i_max, j_min:j_max]
                
                if np.any(~np.isnan(neighbors)):
                    psi1 = psi[i_min:i_max, j_min:j_max]
                    psi[i, j] = np.nanmean(psi1)
    
    return psi
