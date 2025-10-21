"""
Resolve merging and splitting interactions from eddy tracks.

Identifies and flags merging/splitting events in eddy trajectories.
"""

import numpy as np
import pickle
import os


def mod_merging_splitting(tracks, warn_tracks, params, path_out='./output/'):
    """
    Resolve merging and splitting interactions and apply time filtering.
    
    This function:
    1. Identifies merging events (two eddies combine into one)
    2. Identifies splitting events (one eddy splits into two)
    3. Filters tracks shorter than cut_off duration
    4. Handles simultaneous merge-split cases
    
    Parameters
    ----------
    tracks : list of dict
        Eddy tracks from mod_eddy_tracks
    warn_tracks : list of dict
        Warning information for tracks
    params : EDDYParams
        Parameters object
    path_out : str, optional
        Output path for saving results
        
    Returns
    -------
    tracks2 : list of dict
        Filtered tracks with merge/split flags
    short_tracks : list of dict
        Tracks removed by time filtering
    """
    print('Resolving merging and splitting interactions...')
    print()
    
    if len(tracks) == 0:
        return [], []
    
    # Get time range
    stepI = min(track['step'][0] for track in tracks if len(track['step']) > 0)
    stepF = max(track['step'][-1] for track in tracks if len(track['step']) > 0)
    
    print(f'Processing {len(tracks)} tracks from step {stepI} to {stepF}')
    
    # Initialize merge/split flags
    for j in range(len(tracks)):
        n_steps = len(tracks[j]['step'])
        tracks[j]['split'] = np.full(n_steps, np.nan)
        tracks[j]['merge'] = np.full(n_steps, np.nan)
        tracks[j]['split2'] = np.full(n_steps, np.nan)
        tracks[j]['merge2'] = np.full(n_steps, np.nan)
        
        # Flag first interaction
        if 'interaction' in tracks[j]:
            ind = ~np.isnan(tracks[j]['interaction'])
            if np.any(ind):
                ind_indices = np.where(ind)[0]
                inds = ind_indices[0] if len(ind_indices) > 0 else None
                indm = ind_indices[-1] if len(ind_indices) > 0 else None
                
                # Flag as splitting if eddy starts within Dt/2 of first interaction
                if inds is not None:
                    for idx in ind_indices:
                        if tracks[j]['step'][idx] - params.Dt/2 <= tracks[j]['step'][0]:
                            tracks[j]['split'][idx] = 0
                    if tracks[j]['step'][inds] - params.Dt/2 <= tracks[j]['step'][0]:
                        tracks[j]['split'][inds] = 1
                
                # Flag as merging if eddy ends within Dt/2 of last interaction
                if indm is not None:
                    for idx in ind_indices:
                        if tracks[j]['step'][idx] + params.Dt/2 >= tracks[j]['step'][-1]:
                            tracks[j]['merge'][idx] = 0
                    if tracks[j]['step'][indm] + params.Dt/2 >= tracks[j]['step'][-1]:
                        tracks[j]['merge'][indm] = 1
        
        # Flag second interaction (for triple interactions)
        if 'interaction2' in tracks[j]:
            ind2 = ~np.isnan(tracks[j]['interaction2'])
            if np.any(ind2):
                ind2_indices = np.where(ind2)[0]
                inds = ind2_indices[0] if len(ind2_indices) > 0 else None
                indm = ind2_indices[-1] if len(ind2_indices) > 0 else None
                
                if inds is not None:
                    for idx in ind2_indices:
                        if tracks[j]['step'][idx] - params.Dt/2 <= tracks[j]['step'][0]:
                            tracks[j]['split2'][idx] = 0
                    if tracks[j]['step'][inds] - params.Dt/2 <= tracks[j]['step'][0]:
                        tracks[j]['split2'][inds] = 1
                
                if indm is not None:
                    for idx in ind2_indices:
                        if tracks[j]['step'][idx] + params.Dt/2 >= tracks[j]['step'][-1]:
                            tracks[j]['merge2'][idx] = 0
                    if tracks[j]['step'][indm] + params.Dt/2 >= tracks[j]['step'][-1]:
                        tracks[j]['merge2'][indm] = 1
    
    # Extend tracks when merging with child eddy just split
    print('Extending tracks for simultaneous merge-split events...')
    
    for j in range(len(tracks)):
        trymoreconcat = True
        
        while trymoreconcat:
            trymoreconcat = False
            
            if 'merge' in tracks[j]:
                merge_ind = np.where(np.array(tracks[j]['merge']) == 1)[0]
                
                if len(merge_ind) > 0 and 'interaction' in tracks[j]:
                    merge_idx = merge_ind[0]
                    Nind = tracks[j]['interaction'][merge_idx]
                    
                    if not np.isnan(Nind) and 0 <= int(Nind) < len(tracks):
                        Nind = int(Nind)
                        
                        if 'split' in tracks[Nind]:
                            split_ind = np.where(np.array(tracks[Nind]['split']) == 1)[0]
                            
                            if len(split_ind) > 0:
                                split_idx = split_ind[0]
                                
                                if 'interaction' in tracks[Nind]:
                                    Ninds = tracks[Nind]['interaction'][split_idx]
                                    
                                    # Check if split eddy merges back with parent
                                    if (not np.isnan(Ninds) and int(Ninds) == j and
                                        tracks[j]['step'][merge_idx] < tracks[Nind]['step'][split_idx] + params.Dt):
                                        
                                        # Concatenate the split eddy's continuation
                                        Tind = tracks[j]['step'][-1]
                                        Tind1 = np.array(tracks[Nind]['step']) > Tind
                                        
                                        if np.any(Tind1):
                                            # Remove merge flag
                                            tracks[j]['merge'][merge_idx] = 0
                                            
                                            # Append continuation
                                            for key in tracks[j].keys():
                                                if key in tracks[Nind] and isinstance(tracks[j][key], list):
                                                    continuation = [tracks[Nind][key][i] for i in range(len(tracks[Nind][key])) if Tind1[i]]
                                                    tracks[j][key].extend(continuation)
                                            
                                            print(f'Extended track {j} by concatenating with split child {Nind}')
                                            trymoreconcat = True
    
    # Filter short tracks
    print('Filtering short tracks...')
    tracks2 = []
    short_tracks = []
    
    for track in tracks:
        duration = track['step'][-1] - track['step'][0] if len(track['step']) > 0 else 0
        
        # Determine threshold
        if params.cut_off == 0:
            # Use 2x turnover time
            min_tau = np.nanmin(track.get('taumin1', [1]))
            threshold = 2 * min_tau
        elif params.cut_off == 1:
            threshold = 0  # Keep all
        else:
            threshold = params.cut_off
        
        if duration >= threshold:
            tracks2.append(track)
        else:
            short_tracks.append(track)
    
    print(f'Kept {len(tracks2)} tracks, removed {len(short_tracks)} short tracks')
    
    # Save filtered tracks
    os.makedirs(path_out, exist_ok=True)
    with open(os.path.join(path_out, 'eddy_tracks_filtered.pkl'), 'wb') as f:
        pickle.dump({'tracks': tracks2, 'short_tracks': short_tracks}, f)
    
    return tracks2, short_tracks


def identify_merging_events(tracks, params):
    """
    Identify all merging events in tracks.
    
    Parameters
    ----------
    tracks : list of dict
        Eddy tracks
    params : EDDYParams
        Parameters object
        
    Returns
    -------
    merging_events : list of dict
        List of merging events with details
    """
    merging_events = []
    
    for i, track in enumerate(tracks):
        if 'merge' not in track:
            continue
        
        merge_indices = np.where(np.array(track['merge']) == 1)[0]
        
        for idx in merge_indices:
            if 'interaction' in track and idx < len(track['interaction']):
                partner = track['interaction'][idx]
                
                if not np.isnan(partner) and 0 <= int(partner) < len(tracks):
                    event = {
                        'track1': i,
                        'track2': int(partner),
                        'step': track['step'][idx],
                        'x': track['x1'][idx],
                        'y': track['y1'][idx],
                        'type': 'merge'
                    }
                    merging_events.append(event)
    
    return merging_events


def identify_splitting_events(tracks, params):
    """
    Identify all splitting events in tracks.
    
    Parameters
    ----------
    tracks : list of dict
        Eddy tracks
    params : EDDYParams
        Parameters object
        
    Returns
    -------
    splitting_events : list of dict
        List of splitting events with details
    """
    splitting_events = []
    
    for i, track in enumerate(tracks):
        if 'split' not in track:
            continue
        
        split_indices = np.where(np.array(track['split']) == 1)[0]
        
        for idx in split_indices:
            if 'interaction' in track and idx < len(track['interaction']):
                parent = track['interaction'][idx]
                
                if not np.isnan(parent) and 0 <= int(parent) < len(tracks):
                    event = {
                        'track1': int(parent),
                        'track2': i,
                        'step': track['step'][idx],
                        'x': track['x1'][idx],
                        'y': track['y1'][idx],
                        'type': 'split'
                    }
                    splitting_events.append(event)
    
    return splitting_events
