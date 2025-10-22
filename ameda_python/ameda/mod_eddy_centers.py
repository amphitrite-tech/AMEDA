"""
Detect potential eddy centers from LNAM and LOW fields.

Full implementation of center detection algorithm from LNAM extrema.
"""

import numpy as np
import matplotlib.pyplot as plt
from .scan_lines import scan_lines
from .utilities import inpolygon, EDDYParams
from .compute_psi import compute_psi
from .mean_radius import mean_radius


def mod_eddy_centers(x, y, mask, u, v, ssh, fields, params, bxi, Dxi, Rdi, f_i, stp):
    """
    Detect potential eddy centers from LNAM and LOW fields.
    
    Two-step process:
    1. Find max(|LNAM(LOW<0)>K|) - centers0
    2. Validate centers with at least 2 closed streamlines of proper size - centers
    
    Parameters
    ----------
    x, y : ndarray
        Grid coordinates
    mask : ndarray
        Ocean mask
    u, v : ndarray
        Velocity fields (m/s)
    ssh : ndarray
        Sea surface height (m)
    fields : dict
        Detection fields (LNAM, LOW, etc.)
    params : EDDYParams
        Parameters object
    bxi, Dxi, Rdi, f_i : ndarray
        Interpolated parameters (box size, grid spacing, Rossby radius, Coriolis)
    stp : int
        Current time step
        
    Returns
    -------
    centers0 : dict
        All LNAM extrema
    centers : dict
        Validated potential centers with at least 2 closed streamlines
    """
    print(f' Find potential centers step {stp} %-------------')
    
    # Set u, v to 0 in land for PSI calculation
    u = u.copy()
    v = v.copy()
    u[np.isnan(u)] = 0
    v[np.isnan(v)] = 0
    
    # Initialize centers structures
    centers0 = {
        'step': stp,
        'type': [],
        'x': [],
        'y': [],
        'i': [],
        'j': []
    }
    centers = {
        'step': stp,
        'type': [],
        'x': [],
        'y': [],
        'i': [],
        'j': []
    }
    
    # LNAM and OW criteria define contours including potential centers
    OW = fields['LOW'].astype(float)
    LNAM = fields['LNAM'].astype(float)
    LOW = np.abs(LNAM)
    LOW[(OW >= 0) | np.isnan(OW)] = 0
    
    # Create contours at threshold K
    try:
        if params.grid_reg or (x.ndim == 2 and np.all(x[0, :] == x[-1, :]) and np.all(y[:, 0] == y[:, -1])):
            # Regular grid
            if x.ndim == 2:
                CS = plt.contour(x[0, :], y[:, 0], LOW, levels=[params.K])
            else:
                CS = plt.contour(x, y, LOW, levels=[params.K])
        else:
            # Irregular grid
            CS = plt.contour(x, y, LOW, levels=[params.K])
    except Exception as e:
        print(f"Error creating contours: {e}")
        CS = None
    
    # Extract contour data
    contour_data = []
    if CS is not None:
        # Handle different matplotlib contour formats
        if hasattr(CS, 'allsegs'):
            # Old matplotlib format
            for level_segs in CS.allsegs:
                for seg in level_segs:
                    if len(seg) > 0:
                        contour_data.append(seg)
        elif hasattr(CS, 'collections'):
            # Newer matplotlib format
            for collection in CS.collections:
                for path in collection.get_paths():
                    vertices = path.vertices
                    if len(vertices) > 0:
                        contour_data.append(vertices)
        plt.close()
    
    if len(contour_data) == 0:
        print(f'  -> No contours found at threshold K={params.K}')
        return centers0, centers
    
    # Scan each LNAM contour
    k = 0  # counter for validated centers
    MaxL = []
    
    for vertices in contour_data:
        xv = vertices[:, 0]
        yv = vertices[:, 1]
        n = len(xv)
        
        # Validate only bigger contours
        if n >= params.n_min:
            # Create mask inside the contour
            in_contour = inpolygon(x, y, xv, yv)
            Lm = LNAM.copy()
            Lm[~in_contour] = np.nan
            
            # Find L maximum inside the contour
            if np.any(mask[in_contour] > 0) and np.nanmax(np.abs(Lm)) != 0:
                LC_max = np.nanmax(np.abs(Lm))
                
                # Find location of maximum
                max_locations = np.where(np.abs(Lm) == LC_max)
                if len(max_locations[0]) > 0:
                    max_j, max_i = max_locations[0][0], max_locations[1][0]
                    
                    if mask[max_j, max_i] == 1:
                        xLmax = x[max_j, max_i]
                        yLmax = y[max_j, max_i]
                        LC = Lm[max_j, max_i]
                        
                        # Check latitude constraint and uniqueness
                        if (not params.grid_ll or (params.grid_ll and np.abs(yLmax) > params.lat_min)):
                            # Check if not already recorded
                            already_exists = False
                            for idx in range(len(centers0['x'])):
                                if centers0['x'][idx] == xLmax and centers0['y'][idx] == yLmax:
                                    already_exists = True
                                    break
                            
                            if not already_exists:
                                centers0['type'].append(np.sign(LC))
                                centers0['x'].append(xLmax)
                                centers0['y'].append(yLmax)
                                centers0['j'].append(max_j)
                                centers0['i'].append(max_i)
                                MaxL.append(LC)
                                k += 1
    
    # Convert to numpy arrays
    for key in ['type', 'x', 'y', 'i', 'j']:
        centers0[key] = np.array(centers0[key])
    
    print(f'  -> {len(centers0["type"])} max LNAM found step {stp}')
    
    if len(centers0['type']) == 0:
        print(f'!!! WARNING !!! No LNAM extrema found - check LNAM computation step {stp}')
        return centers0, centers
    
    # Validate centers with streamline checking
    print(f'  Remove max LNAM without 2 closed streamlines with proper size step {stp}')
    
    type1 = np.full(len(centers0['type']), np.nan)
    x1 = np.full(len(centers0['type']), np.nan)
    y1 = np.full(len(centers0['type']), np.nan)
    j1 = np.full(len(centers0['type']), np.nan)
    i1 = np.full(len(centers0['type']), np.nan)
    second = np.full(len(centers0['type']), np.nan)
    
    # Compute each max LNAM in a smaller area
    for ii in range(len(centers0['x'])):
        C_I = int(centers0['i'][ii])
        C_J = int(centers0['j'][ii])
        xy_ci = centers0['x'][ii]
        xy_cj = centers0['y'][ii]
        
        # Get local parameters
        bx = int(bxi[C_J, C_I])
        Dx = np.abs(Dxi[C_J, C_I])
        Rd = np.abs(Rdi[C_J, C_I])
        f = np.abs(f_i[C_J, C_I])
        
        # Extract smaller domain
        j_min, j_max = max(C_J - bx, 0), min(C_J + bx + 1, x.shape[0])
        i_min, i_max = max(C_I - bx, 0), min(C_I + bx + 1, x.shape[1])
        
        xx = x[j_min:j_max, i_min:i_max]
        yy = y[j_min:j_max, i_min:i_max]
        mk = mask[j_min:j_max, i_min:i_max]
        uu = u[j_min:j_max, i_min:i_max]
        vv = v[j_min:j_max, i_min:i_max]
        
        if params.type_detection >= 2 and ssh is not None:
            sshh = ssh[j_min:j_max, i_min:i_max]
        else:
            sshh = None
        
        # Find center in small domain
        cj, ci = np.where((yy == xy_cj) & (xx == xy_ci))
        if len(cj) == 0:
            continue
        cj, ci = cj[0], ci[0]
        
        # Find all centers in smaller area
        xy_ctsi = []
        xy_ctsj = []
        for k_idx in range(len(centers0['x'])):
            matches = np.where((yy == centers0['y'][k_idx]) & (xx == centers0['x'][k_idx]))
            if len(matches[0]) > 0:
                xy_ctsi.append(xx[matches[0][0], matches[1][0]])
                xy_ctsj.append(yy[matches[0][0], matches[1][0]])
        
        xy_ctsi = np.array(xy_ctsi) if xy_ctsi else np.array([])
        xy_ctsj = np.array(xy_ctsj) if xy_ctsj else np.array([])
        
        # Compute streamlines
        CS_list = []
        
        # Compute PSI streamlines if needed
        if params.type_detection == 1 or params.type_detection == 3:
            try:
                psi1 = compute_psi(xx, yy, mk, uu * f / params.g * 1e3, 
                                  vv * f / params.g * 1e3, ci, cj, params.grid_ll)
                H = np.arange(np.floor(np.nanmin(psi1)), np.ceil(np.nanmax(psi1)), params.DH)
                if len(H) > params.nH_lim:
                    H = H[:params.nH_lim]
                
                if xx.ndim == 2:
                    CS1 = plt.contour(xx[0, :], yy[:, 0], psi1, levels=H) if params.grid_reg else plt.contour(xx, yy, psi1, levels=H)
                else:
                    CS1 = plt.contour(xx, yy, psi1, levels=H)
                
                for collection in CS1.collections:
                    for path in collection.get_paths():
                        CS_list.append(path.vertices)
                plt.close()
            except Exception as e:
                print(f"Error computing PSI streamlines: {e}")
        
        # Compute SSH streamlines if needed
        if params.type_detection >= 2 and sshh is not None:
            try:
                Hs = np.arange(np.floor(np.nanmin(sshh)), np.ceil(np.nanmax(sshh)), params.DH)
                if len(Hs) > params.nH_lim:
                    Hs = Hs[:params.nH_lim]
                
                if xx.ndim == 2:
                    CS2 = plt.contour(xx[0, :], yy[:, 0], sshh, levels=Hs) if params.grid_reg else plt.contour(xx, yy, sshh, levels=Hs)
                else:
                    CS2 = plt.contour(xx, yy, sshh, levels=Hs)
                
                for collection in CS2.collections:
                    for path in collection.get_paths():
                        CS_list.append(path.vertices)
                plt.close()
            except Exception as e:
                print(f"Error computing SSH streamlines: {e}")
        
        # Scan streamlines to validate center
        radius = []
        
        for vertices in CS_list:
            xdata = vertices[:, 0]
            ydata = vertices[:, 1]
            
            # Check if closed and contains center
            if (len(xdata) >= params.n_min and 
                xdata[0] == xdata[-1] and ydata[0] == ydata[-1] and
                inpolygon(xy_ci, xy_cj, xdata, ydata)):
                
                # Find centers in contour
                if len(xy_ctsi) > 0:
                    IN = inpolygon(xy_ctsi, xy_ctsj, xdata, ydata)
                    nc = np.sum(IN)
                else:
                    nc = 0
                
                # Only one center in streamline
                if nc == 1:
                    # Calculate radius
                    R, _, _, _ = mean_radius(np.array([xdata, ydata]), params.grid_ll)
                    radius.append(R[0])
                    
                    # Record if 2+ streamlines and proper size
                    nRmin = 2.5  # From MATLAB default
                    if (len(radius) >= 2 and 
                        radius[-1] >= nRmin * Dx and 
                        radius[-1] <= params.nR_lim * Rd):
                        
                        print(f'   Validate max LNAM {ii} with 2 streamlines at step {stp}')
                        type1[ii] = centers0['type'][ii]
                        x1[ii] = xy_ci
                        y1[ii] = xy_cj
                        i1[ii] = C_I
                        j1[ii] = C_J
                        second[ii] = 0
                        break
                
                # Two centers in streamline
                elif nc == 2 and ii > 0:
                    R, _, _, _ = mean_radius(np.array([xdata, ydata]), params.grid_ll)
                    radius.append(R[0])
                    
                    nRmin = 2.5
                    if (len(radius) >= 2 and 
                        radius[-1] >= nRmin * Dx and 
                        radius[-1] <= params.nR_lim * Rd):
                        
                        # Find second center index
                        other_centers = np.where(IN & ((xy_ctsi != xy_ci) | (xy_ctsj != xy_cj)))[0]
                        if len(other_centers) > 0:
                            # Find which centers0 index this corresponds to
                            for jj in range(len(centers0['x'])):
                                if (centers0['x'][jj] == xy_ctsi[other_centers[0]] and
                                    centers0['y'][jj] == xy_ctsj[other_centers[0]]):
                                    
                                    if np.isnan(x1[jj]):
                                        second[ii] = jj
                                    elif second[jj] == 0:
                                        # Already validated as single
                                        pass
                                    elif second[jj] == ii:
                                        # Double eddy already recorded
                                        if MaxL[jj] > MaxL[ii]:
                                            second[ii] = np.nan
                                        else:
                                            second[ii] = jj
                                            second[jj] = np.nan
                                    break
                        break
        
        # Record center if validated
        if not np.isnan(second[ii]):
            type1[ii] = centers0['type'][ii]
            x1[ii] = centers0['x'][ii]
            y1[ii] = centers0['y'][ii]
            i1[ii] = centers0['i'][ii]
            j1[ii] = centers0['j'][ii]
    
    # Export validated centers
    IND = np.where(second == 0)[0]
    
    # Handle double eddies
    IND1 = np.where(second > 0)[0]
    if len(IND1) > 0:
        IND2 = []
        for idx in IND1:
            if second[idx] < len(second) and np.isnan(second[int(second[idx])]):
                IND2.append(int(second[idx]))
                print(f'   Remove max LNAM {int(second[idx])} at step {stp}')
        
        if IND2:
            IND = np.concatenate([IND, np.where(np.isin(np.arange(len(second)), IND2))[0]])
    
    if len(IND) == 0:
        print(f'!!! WARNING or ERROR !!! No potential centers found step {stp}')
        return centers0, centers
    
    IND = np.sort(IND)
    centers['type'] = type1[IND].tolist()
    centers['x'] = x1[IND].tolist()
    centers['y'] = y1[IND].tolist()
    centers['i'] = i1[IND].astype(int).tolist()
    centers['j'] = j1[IND].astype(int).tolist()
    
    # Convert to arrays
    for key in ['type', 'x', 'y', 'i', 'j']:
        centers[key] = np.array(centers[key])
    
    print(f' Potential eddy centers found step {stp}')
    print(f'  -> {len(IND)} potential centers found')
    print(f'    ({len(type1) - len(IND)} max LNAM removed)')
    print()
    
    return centers0, centers
