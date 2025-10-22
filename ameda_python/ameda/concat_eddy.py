"""
Concatenate eddy detection results from multiple time periods.

Used for multi-year computations to combine results.
"""

import numpy as np
import pickle
import os


def concat_eddy(names, path_out, streamlines=True):
    """
    Horizontally concatenate mod_fields and mod_eddy results.
    
    Combines detection results from multiple time periods identified by 'names'.
    This is useful for multi-year computations.
    
    Parameters
    ----------
    names : list of str
        List of identifiers for different time periods (e.g., years)
    path_out : str
        Output path where results are stored
    streamlines : bool, optional
        Whether to concatenate streamline profiles
        
    Returns
    -------
    None
        Results are saved to disk
        
    Notes
    -----
    This function concatenates:
    - detection_fields (if needed)
    - centers0, centers, centers2
    - shapes1, shapes2
    - warn_shapes, warn_shapes2
    - profil2 (if streamlines=True)
    
    The step values are adjusted to be sequential across all periods.
    """
    print(f'Concatenating results from {names[0]}...')
    
    # Initialize with first period
    if streamlines:
        profil2_file = os.path.join(path_out, f'eddy_profil_{names[0]}.pkl')
        if os.path.exists(profil2_file):
            with open(profil2_file, 'rb') as f:
                profil2_1 = pickle.load(f)
        else:
            profil2_1 = []
    
    # Load and concatenate from remaining periods
    for name in names[1:]:
        print(f'Concatenating results from {name}...')
        
        if streamlines:
            profil2_file = os.path.join(path_out, f'eddy_profil_{name}.pkl')
            if os.path.exists(profil2_file):
                with open(profil2_file, 'rb') as f:
                    profil2_2 = pickle.load(f)
                
                # Concatenate
                if isinstance(profil2_1, list) and isinstance(profil2_2, list):
                    profil2_1 = profil2_1 + profil2_2
                elif isinstance(profil2_1, np.ndarray) and isinstance(profil2_2, np.ndarray):
                    profil2_1 = np.concatenate([profil2_1, profil2_2])
    
    # Straighten step values
    if streamlines and isinstance(profil2_1, list):
        N = len(profil2_1)
        for i in range(N):
            if isinstance(profil2_1[i], dict) and 'step' in profil2_1[i]:
                profil2_1[i]['step'] = i + 1
    
    # Save concatenated results
    if streamlines and profil2_1:
        output_file = os.path.join(
            path_out, 
            f'eddy_profil_{names[0]}_{names[-1]}.pkl'
        )
        with open(output_file, 'wb') as f:
            pickle.dump(profil2_1, f)
        
        print(f'Concatenated results saved to {output_file}')


def concat_eddy_tracks(track_files, output_file):
    """
    Concatenate eddy tracking results from multiple files.
    
    Parameters
    ----------
    track_files : list of str
        List of file paths containing tracking results
    output_file : str
        Output file path for concatenated results
        
    Returns
    -------
    tracks : list
        Concatenated tracking results
    """
    all_tracks = []
    
    for track_file in track_files:
        if os.path.exists(track_file):
            with open(track_file, 'rb') as f:
                tracks = pickle.load(f)
            
            if isinstance(tracks, list):
                all_tracks.extend(tracks)
            elif isinstance(tracks, np.ndarray):
                if len(all_tracks) == 0:
                    all_tracks = tracks
                else:
                    all_tracks = np.concatenate([all_tracks, tracks])
    
    # Save concatenated results
    if all_tracks:
        with open(output_file, 'wb') as f:
            pickle.dump(all_tracks, f)
        
        print(f'Concatenated {len(all_tracks)} tracks to {output_file}')
    
    return all_tracks
