"""
Track eddies over time using assignment algorithm.

Implements temporal tracking of detected eddies across time steps.
"""

import numpy as np
from scipy.optimize import linear_sum_assignment
from .sw_dist import sw_dist2
import pickle
import os


def compute_cost_matrix(tracks_active, eddies_new, params):
    """
    Compute cost matrix for eddy assignment.
    
    Cost function: C = sqrt((d/D)² + (dR/Rmax)² + (dRo/Ro)² + (dt/Dt/2)²)
    
    Parameters
    ----------
    tracks_active : list of dict
        Currently tracked eddies
    eddies_new : dict
        Newly detected eddies
    params : EDDYParams
        Parameters object
        
    Returns
    -------
    cost_matrix : ndarray
        NxM cost matrix (N=old eddies, M=new eddies)
    """
    n_old = len(tracks_active)
    n_new = len(eddies_new['type'])
    
    if n_old == 0 or n_new == 0:
        return np.array([])
    
    cost_matrix = np.full((n_old, n_new), np.inf)
    
    for i, track in enumerate(tracks_active):
        # Get last known position and features
        last_x = track['x1'][-1]
        last_y = track['y1'][-1]
        last_rmax = track['rmax1'][-1] if not np.isnan(track['rmax1'][-1]) else 50
        last_step = track['step'][-1]
        
        # Calculate mean radius over last D_stp steps
        n_avg = min(params.D_stp, len(track['rmax1']))
        rmax_mean = np.nanmean(track['rmax1'][-n_avg:])
        
        for j in range(n_new):
            # Check same type
            if track['type'][-1] != eddies_new['type'][j]:
                continue
            
            new_x = eddies_new['x1'][j]
            new_y = eddies_new['y1'][j]
            new_rmax = eddies_new['rmax1'][j] if not np.isnan(eddies_new['rmax1'][j]) else 50
            new_step = eddies_new['step']
            
            # Calculate distance
            if params.grid_ll:
                d = sw_dist2(np.array([last_y, new_y]), np.array([last_x, new_x]))[0]
            else:
                d = np.sqrt((new_x - last_x)**2 + (new_y - last_y)**2)
            
            # Maximum search distance
            dt = new_step - last_step
            V_search = params.V_eddy if params.V_eddy > 0 else rmax_mean
            D = V_search * (1 + dt) / 2 + rmax_mean + new_rmax
            
            # Only consider if within search radius
            if d <= D and dt <= params.Dt:
                # Calculate normalized differences
                d_norm = d / D if D > 0 else np.inf
                dR_norm = np.abs(new_rmax - last_rmax) / last_rmax if last_rmax > 0 else 0
                
                # Ro = rmax/Rd (resolution)
                Ro_old = rmax_mean / track.get('Rd', [50])[-1] if len(track.get('Rd', [50])) > 0 else 1
                Ro_new = new_rmax / eddies_new.get('Rd', [50])[j] if j < len(eddies_new.get('Rd', [50])) else 1
                dRo_norm = np.abs(Ro_new - Ro_old) / Ro_old if Ro_old > 0 else 0
                
                dt_norm = dt / (params.Dt / 2)
                
                # Cost function
                cost_matrix[i, j] = np.sqrt(d_norm**2 + dR_norm**2 + dRo_norm**2 + dt_norm**2)
    
    return cost_matrix


def mod_eddy_tracks(centers2_list, shapes1_list, shapes2_list, warn_shapes2_list,
                    params, path_out='./output/', update=0):
    """
    Compute eddy tracking from detected eddies.
    
    Connects eddies across time steps using an assignment algorithm that
    minimizes a cost function based on distance, radius change, and time.
    
    Parameters
    ----------
    centers2_list : list of dict
        List of validated centers for each time step
    shapes1_list : list of dict
        List of single eddy shapes for each time step
    shapes2_list : list of dict
        List of double eddy shapes for each time step
    warn_shapes2_list : list of dict
        List of warning flags for each time step
    params : EDDYParams
        Parameters object
    path_out : str, optional
        Output path for saving tracks
    update : int, optional
        Number of steps backward for update mode
        
    Returns
    -------
    tracks : list of dict
        List of eddy tracks with all features
    warn_tracks : list of dict
        Warning information for tracks
    """
    print('Tracking eddies...')
    print()
    
    stepF = len(centers2_list)
    
    # Initialize or load tracks
    if update > 0 and os.path.exists(os.path.join(path_out, 'eddy_tracks.pkl')):
        with open(os.path.join(path_out, 'eddy_tracks.pkl'), 'rb') as f:
            data = pickle.load(f)
            tracks = data['tracks']
            warn_tracks = data['warn_tracks']
        step0 = stepF - update + 1
    else:
        tracks = []
        warn_tracks = []
        step0 = 0
    
    # Track eddies through time
    for i in range(step0, stepF):
        centers2 = centers2_list[i]
        shapes1 = shapes1_list[i]
        shapes2 = shapes2_list[i]
        warn_shapes2 = warn_shapes2_list[i]
        
        if len(centers2.get('type', [])) == 0:
            continue
        
        stp = centers2.get('step', i + 1)
        print(f' Searching step {stp} %------------- ')
        
        # Create eddy structure for current step
        eddy = create_eddy_structure(centers2, shapes1, shapes2, warn_shapes2, params)
        
        # First time step: all eddies start new tracks
        if i == 0 or len(tracks) == 0:
            for i2 in range(len(eddy['type'])):
                track = create_new_track(eddy, i2)
                tracks.append(track)
                
                # Initialize warnings
                warn = create_new_warning(eddy, i2, params)
                warn_tracks.append(warn)
            
            print(f'  -> {len(tracks)} total eddies')
        
        else:
            # Find active tracks (not closed)
            active_tracks = []
            active_indices = []
            for idx, track in enumerate(tracks):
                last_step = track['step'][-1]
                if stp - last_step <= params.Dt:
                    active_tracks.append(track)
                    active_indices.append(idx)
            
            if len(active_tracks) == 0:
                # No active tracks, start all as new
                for i2 in range(len(eddy['type'])):
                    track = create_new_track(eddy, i2)
                    tracks.append(track)
                    warn = create_new_warning(eddy, i2, params)
                    warn_tracks.append(warn)
            else:
                # Compute cost matrix
                cost_matrix = compute_cost_matrix(active_tracks, eddy, params)
                
                if cost_matrix.size > 0:
                    # Solve assignment problem
                    row_ind, col_ind = linear_sum_assignment(cost_matrix)
                    
                    # Track which new eddies are assigned
                    assigned_new = set()
                    
                    # Update tracks with assignments
                    for old_idx, new_idx in zip(row_ind, col_ind):
                        if cost_matrix[old_idx, new_idx] < np.inf:
                            # Valid assignment
                            track_idx = active_indices[old_idx]
                            append_to_track(tracks[track_idx], eddy, new_idx)
                            assigned_new.add(new_idx)
                    
                    # Start new tracks for unassigned eddies
                    for i2 in range(len(eddy['type'])):
                        if i2 not in assigned_new:
                            track = create_new_track(eddy, i2)
                            tracks.append(track)
                            warn = create_new_warning(eddy, i2, params)
                            warn_tracks.append(warn)
        
        print(f'  -> {len(tracks)} total tracks ({len([t for t in tracks if stp - t["step"][-1] <= params.Dt])} active)')
        print()
    
    # Save tracks
    os.makedirs(path_out, exist_ok=True)
    with open(os.path.join(path_out, 'eddy_tracks.pkl'), 'wb') as f:
        pickle.dump({'tracks': tracks, 'warn_tracks': warn_tracks}, f)
    
    print(f'Saved {len(tracks)} tracks')
    
    return tracks, warn_tracks


def create_eddy_structure(centers2, shapes1, shapes2, warn_shapes2, params):
    """Create eddy structure for current time step."""
    n_eddies = len(centers2.get('type', []))
    
    eddy = {
        'step': centers2.get('step', 0),
        'type': centers2.get('type', np.array([])),
        'x1': centers2.get('x1', np.array([])),
        'y1': centers2.get('y1', np.array([])),
        'x2': centers2.get('x2', np.array([])),
        'y2': centers2.get('y2', np.array([])),
        'dc': centers2.get('dc', np.array([])),
        'ind2': centers2.get('ind2', np.array([])),
    }
    
    # Add shapes1 features
    for key in ['velmax', 'deta', 'taumin', 'nrho', 'rmax', 'aire', 
                'xbary', 'ybary', 'ellip', 'theta']:
        eddy[key + '1'] = shapes1.get(key, np.full(n_eddies, np.nan))
    
    eddy['shapes1'] = shapes1.get('xy', [None] * n_eddies)
    eddy['shapes3'] = shapes1.get('xy_end', [None] * n_eddies)
    eddy['velmax3'] = shapes1.get('vel_end', np.full(n_eddies, np.nan))
    eddy['deta3'] = shapes1.get('deta_end', np.full(n_eddies, np.nan))
    eddy['nrho3'] = shapes1.get('nrho_end', np.full(n_eddies, np.nan))
    eddy['rmax3'] = shapes1.get('r_end', np.full(n_eddies, np.nan))
    eddy['aire3'] = shapes1.get('aire_end', np.full(n_eddies, np.nan))
    
    # Add shapes2 features
    for key in ['velmax', 'deta', 'taumin', 'nrho', 'rmax', 'aire',
                'xbary', 'ybary', 'ellip', 'theta']:
        eddy[key + '2'] = shapes2.get(key, np.full(n_eddies, np.nan))
    
    eddy['shapes2'] = shapes2.get('xy', [None] * n_eddies)
    
    # Add warning flags
    for key in ['f', 'Rd', 'gama', 'calcul_curve', 'large_curve1', 'large_curve2', 'too_weak2']:
        eddy[key] = warn_shapes2.get(key.replace('_curve', '').replace('calcul', 'calcul_curve'), 
                                     np.full(n_eddies, np.nan))
    
    return eddy


def create_new_track(eddy, idx):
    """Create a new track from an eddy."""
    track = {}
    
    for key in eddy.keys():
        if isinstance(eddy[key], (list, np.ndarray)):
            if key in ['shapes1', 'shapes2', 'shapes3']:
                track[key] = [eddy[key][idx]]
            elif isinstance(eddy[key], np.ndarray) and len(eddy[key].shape) > 0:
                track[key] = [eddy[key][idx]] if idx < len(eddy[key]) else [np.nan]
            else:
                track[key] = [eddy[key]]
        else:
            track[key] = [eddy[key]]
    
    # Initialize interaction fields
    track['interaction'] = [np.nan]
    track['interaction2'] = [np.nan]
    track['ind'] = [idx]
    
    return track


def append_to_track(track, eddy, idx):
    """Append new detection to existing track."""
    for key in eddy.keys():
        if key not in track:
            track[key] = []
        
        if isinstance(eddy[key], (list, np.ndarray)):
            if key in ['shapes1', 'shapes2', 'shapes3']:
                track[key].append(eddy[key][idx])
            elif isinstance(eddy[key], np.ndarray) and len(eddy[key].shape) > 0:
                track[key].append(eddy[key][idx] if idx < len(eddy[key]) else np.nan)
            else:
                track[key].append(eddy[key])
        else:
            track[key].append(eddy[key])
    
    # Update interaction
    if 'interaction' not in track:
        track['interaction'] = []
    track['interaction'].append(np.nan)
    
    if 'interaction2' not in track:
        track['interaction2'] = []
    track['interaction2'].append(np.nan)


def create_new_warning(eddy, idx, params):
    """Create warning structure for new track."""
    warn = {
        'step': [eddy.get('step', 0)],
        'last': 0,
        'ind': idx,
        'can': np.zeros(params.N_can),
        'd': np.full(params.N_can, np.inf),
        'D': np.zeros(params.N_can),
        'C': np.full(params.N_can, np.inf),
        'interaction': eddy.get('interaction', [np.nan])[idx] if 'interaction' in eddy else np.nan,
        'interaction2': eddy.get('interaction2', [np.nan])[idx] if 'interaction2' in eddy else np.nan,
        'far1': np.nan,
        'far2': np.nan
    }
    return warn


def filter_short_tracks(tracks, params):
    """
    Filter out tracks shorter than cut_off period.
    
    Parameters
    ----------
    tracks : list of dict
        All eddy tracks
    params : EDDYParams
        Parameters object
        
    Returns
    -------
    filtered_tracks : list of dict
        Tracks longer than cut_off
    short_tracks : list of dict
        Tracks removed by filtering
    """
    filtered_tracks = []
    short_tracks = []
    
    for track in tracks:
        # Calculate duration
        if len(track['step']) > 0:
            duration = track['step'][-1] - track['step'][0]
            
            # Check against cut_off
            if params.cut_off == 0:
                # Use turnover time
                min_tau = np.nanmin(track['taumin1']) if 'taumin1' in track else 1
                threshold = 2 * min_tau
            elif params.cut_off == 1:
                # Keep all
                threshold = 0
            else:
                # Use specified cut_off
                threshold = params.cut_off
            
            if duration >= threshold:
                filtered_tracks.append(track)
            else:
                short_tracks.append(track)
    
    return filtered_tracks, short_tracks
