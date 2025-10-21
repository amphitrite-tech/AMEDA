"""
Compute shapes of detected eddies.

Full implementation of shape detection and validation.
"""

import numpy as np
from .eddy_dim import eddy_dim
from .compute_ellip import compute_ellip
from .compute_best_fit import compute_best_fit
from .utilities import inpolygon, EDDYParams


def mod_eddy_shapes(x, y, mask, u, v, ssh, fields, centers, params, 
                    bxi, Dxi, Rdi, f_i, stp):
    """
    Compute shapes of eddies from potential centers.
    
    Determines eddy boundaries by scanning streamlines and finding
    the contour with maximum velocity. Handles both single and double eddies.
    
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
        Detection fields
    centers : dict
        Potential centers from mod_eddy_centers
    params : EDDYParams
        Parameters object
    bxi, Dxi, Rdi, f_i : ndarray
        Interpolated parameters
    stp : int
        Current time step
        
    Returns
    -------
    centers2 : dict
        Validated centers with shapes
    shapes1 : dict
        Single eddy shapes and features
    shapes2 : dict
        Double eddy shapes (interactions)
    profil2 : dict
        Streamline profiles (if streamlines enabled)
    warn_shapes : dict
        Warning flags for shape computation
    warn_shapes2 : dict
        Warning flags for double eddies
    """
    print(f'Start step {stp} %-------------')
    print()
    
    # Initialize structures
    centers2 = {
        'step': stp,
        'type': [],
        'x1': [],
        'y1': [],
        'x2': [],
        'y2': [],
        'dc': [],
        'ind2': []
    }
    
    shapes1 = {
        'step': stp,
        'xy': [],
        'velmax': [],
        'deta': [],
        'taumin': [],
        'nrho': [],
        'rmax': [],
        'aire': [],
        'xbary': [],
        'ybary': [],
        'ellip': [],
        'theta': [],
        'xy_end': [],
        'vel_end': [],
        'deta_end': [],
        'nrho_end': [],
        'r_end': [],
        'aire_end': []
    }
    
    shapes2 = {
        'step': stp,
        'xy': [],
        'velmax': [],
        'deta': [],
        'taumin': [],
        'nrho': [],
        'rmax': [],
        'aire': [],
        'xbary': [],
        'ybary': [],
        'ellip': [],
        'theta': []
    }
    
    warn_shapes = {
        'no_curve': [],
        'f': [],
        'Rd': [],
        'gama': [],
        'bx': [],
        'calcul_curve': [],
        'large_curve1': [],
        'large_curve2': [],
        'too_weak2': []
    }
    
    warn_shapes2 = warn_shapes.copy()
    
    profil2 = {'step': stp, 'nc': [], 'eta': [], 'rmoy': [], 
               'vel': [], 'tau': [], 'nrhoi': [], 'myfit': []}
    
    # Loop through all centers
    for ii in range(len(centers['type'])):
        print(f' === Center {ii+1} ===')
        
        c_j = int(centers['j'][ii])
        c_i = int(centers['i'][ii])
        
        # Initialize temporary variables
        bound = True
        fac = 0
        tmp_large = [1, np.nan]
        tmp_CD = []
        tmp_xy = [None, None, None]
        tmp_allines = []
        tmp_rmax = np.full(3, np.nan)
        tmp_velmax = np.zeros(3)
        tmp_tau = np.full(2, np.nan)
        tmp_deta = np.full(3, np.nan)
        tmp_nrho = np.full(3, np.nan)
        
        # Expand search area if needed
        while bound:
            fac += 1
            
            # Call eddy_dim to compute shape
            CD, xy, allines, rmax, velmax, tau, deta, nrho, large, warn, calcul = eddy_dim(
                u, v, ssh, mask, x, y, centers, ii,
                f_i[c_j, c_i], Rdi[c_j, c_i], fac * bxi[c_j, c_i], params
            )
            
            # Process flags
            if warn:
                print('    -> No significant streamlines closed around the center')
                bound = False
            else:
                # Update single eddy
                if velmax[0] > tmp_velmax[0] * (1 + params.epsil) or large[0] < tmp_large[0]:
                    if tmp_large[0] == 1 or velmax[0] > 0:
                        tmp_large[0] = large[0]
                        tmp_xy[0] = xy[0]
                        tmp_rmax[0] = rmax[0]
                        tmp_velmax[0] = velmax[0]
                        tmp_tau[0] = tau[0]
                        tmp_deta[0] = deta[0]
                        tmp_nrho[0] = nrho[0]
                        tmp_allines = allines
                
                # Update last contour
                if np.isnan(tmp_deta[2]) or (np.abs(deta[2]) > np.abs(tmp_deta[2]) * (1 + params.epsil) and rmax[2] >= tmp_rmax[0]):
                    bound = True
                    tmp_xy[2] = xy[2]
                    tmp_rmax[2] = rmax[2]
                    tmp_velmax[2] = velmax[2]
                    tmp_nrho[2] = nrho[2]
                    tmp_deta[2] = deta[2]
                else:
                    bound = False
                
                # Handle double eddy
                if np.isnan(large[1]) and fac == 1:
                    bound = True
                elif velmax[1] > tmp_velmax[1] * (1 + params.epsil):
                    bound = True
                    tmp_large[1] = large[1]
                    tmp_CD = CD
                    tmp_xy[1] = xy[1]
                    tmp_rmax[1] = rmax[1]
                    tmp_velmax[1] = velmax[1]
                    tmp_deta[1] = deta[1]
                    tmp_nrho[1] = nrho[1]
                    tmp_tau[1] = tau[1]
                elif not np.isnan(large[1]):
                    bound = False
            
            if bound and fac < 5:  # Limit expansion
                print(f'    Big eddy: going to fac = {fac+1}')
            else:
                if fac > 1:
                    print(f'    No bigger eddy nor interaction stop dezoom by fac {fac}')
                    large = tmp_large
                    CD = tmp_CD
                    xy = tmp_xy
                    allines = tmp_allines
                    rmax = tmp_rmax
                    velmax = tmp_velmax
                    tau = tmp_tau
                    deta = tmp_deta
                    nrho = tmp_nrho
                bound = False
        
        # Determine eddy type
        if xy[0] is None:
            print('    -> No Eddy')
            xy = [None, None, None]
        elif rmax[0] < 2.5 * Dxi[c_j, c_i] or rmax[2] < 2.5 * Dxi[c_j, c_i]:
            print('    -> Too small Eddy')
            xy = [None, None, None]
        elif large[1] == 0:
            print('    -> Eddy with 2 centers')
        elif large[0] == 0:
            print('    -> Eddy with 1 center')
        elif large[1] == 1:
            print('    -> Largest with 2 centers')
        elif large[0] == 1:
            print('    -> Largest with 1 center')
        
        # Save results to structures
        centers2['type'].append(centers['type'][ii])
        centers2['x1'].append(centers['x'][ii])
        centers2['y1'].append(centers['y'][ii])
        
        if xy[2] is not None:
            # Validate end contour
            if rmax[0] > rmax[2]:
                print(f'!!! ERROR !!! Rmax > Rend ({round((rmax[0]/rmax[2]-1)*100)}%) center {ii+1} step {stp}')
                xy[2] = xy[0]
                rmax[2] = rmax[0]
                velmax[2] = velmax[0]
                deta[2] = deta[0]
                nrho[2] = nrho[0]
            
            shapes1['xy_end'].append(xy[2])
            shapes1['vel_end'].append(velmax[2])
            shapes1['deta_end'].append(deta[2])
            shapes1['nrho_end'].append(nrho[2])
            shapes1['r_end'].append(rmax[2])
            shapes1['aire_end'].append(np.pi * rmax[2]**2)
        else:
            shapes1['xy_end'].append(None)
            shapes1['vel_end'].append(np.nan)
            shapes1['deta_end'].append(np.nan)
            shapes1['nrho_end'].append(np.nan)
            shapes1['r_end'].append(np.nan)
            shapes1['aire_end'].append(np.nan)
        
        # Save single eddy shape
        if xy[0] is not None:
            shapes1['xy'].append(xy[0])
            shapes1['velmax'].append(velmax[0])
            shapes1['taumin'].append(tau[0])
            shapes1['deta'].append(deta[0])
            shapes1['nrho'].append(nrho[0])
            shapes1['rmax'].append(rmax[0])
            shapes1['aire'].append(np.pi * rmax[0]**2)
            
            # Compute ellipse
            xbary, ybary, z, a, b, theta, lim = compute_ellip(xy[0], params.grid_ll)
            shapes1['xbary'].append(xbary)
            shapes1['ybary'].append(ybary)
            
            if a >= b and a != 0:
                shapes1['ellip'].append(1 - b/a)
                shapes1['theta'].append(theta)
            elif a < b and b != 0:
                shapes1['ellip'].append(1 - a/b)
                shapes1['theta'].append(theta + np.pi/2 if theta <= np.pi/2 else theta - np.pi/2)
            else:
                shapes1['ellip'].append(np.nan)
                shapes1['theta'].append(np.nan)
        else:
            for key in ['xy', 'velmax', 'taumin', 'deta', 'nrho', 'rmax', 'aire', 
                       'xbary', 'ybary', 'ellip', 'theta']:
                if key == 'xy':
                    shapes1[key].append(None)
                else:
                    shapes1[key].append(np.nan)
        
        # Save double eddy shape
        if xy[1] is not None and CD is not None and len(CD) > 0:
            if CD[0, 0] == centers['x'][ii] and CD[1, 0] == centers['y'][ii]:
                centers2['x2'].append(CD[0, 1])
                centers2['y2'].append(CD[1, 1])
            else:
                centers2['x2'].append(CD[0, 0])
                centers2['y2'].append(CD[1, 0])
            
            # Distance between centers
            if params.grid_ll:
                from .sw_dist import sw_dist2
                dc = sw_dist2(CD[1, :], CD[0, :])[0]
            else:
                dc = np.sqrt(np.diff(CD[0, :])**2 + np.diff(CD[1, :])**2)
            centers2['dc'].append(dc)
            
            # Shape features
            shapes2['xy'].append(xy[1])
            shapes2['velmax'].append(velmax[1])
            shapes2['taumin'].append(tau[1])
            shapes2['deta'].append(deta[1])
            shapes2['nrho'].append(nrho[1])
            shapes2['rmax'].append(rmax[1])
            shapes2['aire'].append(np.pi * rmax[1]**2)
            
            xbary, ybary, z, a, b, theta, lim = compute_ellip(xy[1], params.grid_ll)
            shapes2['xbary'].append(xbary)
            shapes2['ybary'].append(ybary)
            
            if a >= b and a != 0:
                shapes2['ellip'].append(1 - b/a)
                shapes2['theta'].append(theta)
            elif a < b and b != 0:
                shapes2['ellip'].append(1 - a/b)
                shapes2['theta'].append(theta + np.pi/2 if theta <= np.pi/2 else theta - np.pi/2)
            else:
                shapes2['ellip'].append(np.nan)
                shapes2['theta'].append(np.nan)
        else:
            centers2['x2'].append(np.nan)
            centers2['y2'].append(np.nan)
            centers2['dc'].append(np.nan)
            
            for key in shapes2.keys():
                if key == 'step':
                    continue
                elif key == 'xy':
                    shapes2[key].append(None)
                else:
                    shapes2[key].append(np.nan)
        
        centers2['ind2'].append(np.nan)
        
        # Save warnings
        warn_shapes['no_curve'].append(warn if 'warn' in locals() else 0)
        warn_shapes['f'].append(f_i[c_j, c_i])
        warn_shapes['Rd'].append(Rdi[c_j, c_i])
        gama = Rdi[c_j, c_i] / Dxi[c_j, c_i] if Dxi[c_j, c_i] != 0 else np.nan
        warn_shapes['gama'].append(gama)
        warn_shapes['bx'].append(bxi[c_j, c_i] * fac)
        warn_shapes['calcul_curve'].append(calcul if 'calcul' in locals() else 0)
        warn_shapes['large_curve1'].append(large[0] if 'large' in locals() else np.nan)
        warn_shapes['large_curve2'].append(large[1] if 'large' in locals() else np.nan)
        warn_shapes['too_weak2'].append(0)
        
        print()
    
    # Convert to numpy arrays
    for key in centers2.keys():
        if key != 'step':
            centers2[key] = np.array(centers2[key])
    
    for key in shapes1.keys():
        if key not in ['step', 'xy', 'xy_end']:
            shapes1[key] = np.array(shapes1[key])
    
    for key in shapes2.keys():
        if key not in ['step', 'xy']:
            shapes2[key] = np.array(shapes2[key])
    
    for key in warn_shapes.keys():
        warn_shapes[key] = np.array(warn_shapes[key])
        warn_shapes2[key] = warn_shapes[key].copy()
    
    # Remove shapes with no valid end contour
    if len(centers2['type']) > 0:
        replace = np.where(np.isnan(shapes1['vel_end']))[0]
        
        if len(replace) > 0:
            for key in centers2.keys():
                if key != 'step':
                    centers2[key] = np.delete(centers2[key], replace)
            
            for key in shapes1.keys():
                if key == 'xy' or key == 'xy_end':
                    shapes1[key] = [shapes1[key][i] for i in range(len(shapes1[key])) if i not in replace]
                elif key != 'step':
                    shapes1[key] = np.delete(shapes1[key], replace)
            
            for key in shapes2.keys():
                if key == 'xy':
                    shapes2[key] = [shapes2[key][i] for i in range(len(shapes2[key])) if i not in replace]
                elif key != 'step':
                    shapes2[key] = np.delete(shapes2[key], replace)
            
            for key in warn_shapes.keys():
                warn_shapes[key] = np.delete(warn_shapes[key], replace)
                warn_shapes2[key] = np.delete(warn_shapes2[key], replace)
    
    print(f'-------------% End step {stp}')
    print()
    
    return centers2, shapes1, shapes2, profil2, warn_shapes, warn_shapes2
