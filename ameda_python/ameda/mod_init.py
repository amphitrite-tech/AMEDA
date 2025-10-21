"""
Initialize or update structure arrays for AMEDA detection.
"""

import numpy as np
import os
import pickle


def mod_init(stepF, update=0, path_out='./output/', streamlines=True, extended_diags=False):
    """
    Preallocate structure arrays and mat-files or prepare for update.
    
    This function initializes all the data structures needed for AMEDA:
    - detection_fields: Fields like LNAM, OW, vorticity
    - centers0, centers, centers2: Eddy center structures
    - shapes1, shapes2: Eddy shape structures
    - warn_shapes, warn_shapes2: Warning/diagnostic structures
    - profil2: Streamline profiles (if streamlines=True)
    
    Parameters
    ----------
    stepF : int
        Final time step of the computed series
    update : int, optional
        Number of time steps backward to consider for update
        0 (default) computes all time series from scratch
    path_out : str, optional
        Output path for saved structures
    streamlines : bool, optional
        Whether to include streamline profiles
    extended_diags : bool, optional
        Whether to include extended diagnostics in shapes
        
    Returns
    -------
    step0 : int
        First time step to be computed
        (For update==0, step0=1)
        
    Notes
    -----
    Structures are saved as Python pickle files:
    - fields.pkl
    - fields_inter.pkl
    - eddy_centers.pkl
    - eddy_shapes.pkl
    """
    # Ensure output directory exists
    os.makedirs(path_out, exist_ok=True)
    
    if update > 0:
        # Update mode: load existing and extend
        step0 = stepF - update + 1
        
        # Load existing structures
        try:
            with open(os.path.join(path_out, 'fields.pkl'), 'rb') as f:
                detection_fields_ni = pickle.load(f)
            with open(os.path.join(path_out, 'fields_inter.pkl'), 'rb') as f:
                detection_fields = pickle.load(f)
            with open(os.path.join(path_out, 'eddy_centers.pkl'), 'rb') as f:
                data = pickle.load(f)
                centers0 = data['centers0']
                centers = data['centers']
                centers2 = data['centers2']
            with open(os.path.join(path_out, 'eddy_shapes.pkl'), 'rb') as f:
                data = pickle.load(f)
                shapes1 = data['shapes1']
                shapes2 = data['shapes2']
                warn_shapes = data['warn_shapes']
                warn_shapes2 = data['warn_shapes2']
                if streamlines and 'profil2' in data:
                    profil2 = data['profil2']
                else:
                    profil2 = []
        except FileNotFoundError:
            print("Warning: Could not load existing files, starting fresh")
            update = 0
        
        if update > 0:
            # Keep only steps before update
            detection_fields_ni = detection_fields_ni[:step0]
            detection_fields = detection_fields[:step0]
            centers0 = centers0[:step0]
            centers = centers[:step0]
            centers2 = centers2[:step0]
            shapes1 = shapes1[:step0]
            shapes2 = shapes2[:step0]
            warn_shapes = warn_shapes[:step0]
            warn_shapes2 = warn_shapes2[:step0]
            if streamlines and profil2:
                profil2 = profil2[:step0]
            
            # Extend to stepF
            for _ in range(step0, stepF + 1):
                detection_fields_ni.append(create_empty_fields())
                detection_fields.append(create_empty_fields())
                centers0.append(create_empty_centers())
                centers.append(create_empty_centers())
                centers2.append(create_empty_centers2())
                shapes1.append(create_empty_shapes(extended_diags, streamlines))
                shapes2.append(create_empty_shapes2())
                warn_shapes.append(create_empty_warnings())
                warn_shapes2.append(create_empty_warnings())
                if streamlines:
                    profil2.append(create_empty_profil())
    else:
        # Fresh start
        step0 = 1
        
        # Preallocate structures
        detection_fields_ni = [create_empty_fields() for _ in range(stepF)]
        detection_fields = [create_empty_fields() for _ in range(stepF)]
        centers0 = [create_empty_centers() for _ in range(stepF)]
        centers = [create_empty_centers() for _ in range(stepF)]
        centers2 = [create_empty_centers2() for _ in range(stepF)]
        shapes1 = [create_empty_shapes(extended_diags, streamlines) for _ in range(stepF)]
        shapes2 = [create_empty_shapes2() for _ in range(stepF)]
        warn_shapes = [create_empty_warnings() for _ in range(stepF)]
        warn_shapes2 = [create_empty_warnings() for _ in range(stepF)]
        
        if streamlines:
            profil2 = [create_empty_profil() for _ in range(stepF)]
        else:
            profil2 = []
    
    # Save structures
    with open(os.path.join(path_out, 'fields.pkl'), 'wb') as f:
        pickle.dump(detection_fields_ni, f)
    
    with open(os.path.join(path_out, 'fields_inter.pkl'), 'wb') as f:
        pickle.dump(detection_fields, f)
    
    with open(os.path.join(path_out, 'eddy_centers.pkl'), 'wb') as f:
        pickle.dump({
            'centers0': centers0,
            'centers': centers,
            'centers2': centers2
        }, f)
    
    shapes_data = {
        'shapes1': shapes1,
        'shapes2': shapes2,
        'warn_shapes': warn_shapes,
        'warn_shapes2': warn_shapes2
    }
    if streamlines:
        shapes_data['profil2'] = profil2
    
    with open(os.path.join(path_out, 'eddy_shapes.pkl'), 'wb') as f:
        pickle.dump(shapes_data, f)
    
    print(f"Initialized structures for {stepF} time steps")
    print(f"Starting computation from step {step0}")
    
    return step0


def create_empty_fields():
    """Create empty detection fields structure."""
    return {
        'step': None,
        'ke': None,
        'div': None,
        'vort': None,
        'OW': None,
        'LOW': None,
        'LNAM': None
    }


def create_empty_centers():
    """Create empty centers structure."""
    return {
        'step': None,
        'type': np.array([]),
        'x': np.array([]),
        'y': np.array([]),
        'i': np.array([]),
        'j': np.array([])
    }


def create_empty_centers2():
    """Create empty centers2 structure."""
    return {
        'step': None,
        'type': np.array([]),
        'x1': np.array([]),
        'y1': np.array([]),
        'x2': np.array([]),
        'y2': np.array([]),
        'dc': np.array([]),
        'ind2': np.array([])
    }


def create_empty_shapes(extended_diags=False, streamlines=False):
    """Create empty shapes1 structure."""
    shape = {
        'step': None,
        'xy': [],
        'velmax': np.array([]),
        'deta': np.array([]),
        'taumin': np.array([]),
        'nrho': np.array([]),
        'rmax': np.array([]),
        'aire': np.array([]),
        'xbary': np.array([]),
        'ybary': np.array([]),
        'ellip': np.array([]),
        'theta': np.array([]),
        'xy_end': [],
        'vel_end': np.array([]),
        'deta_end': np.array([]),
        'nrho_end': np.array([]),
        'r_end': np.array([]),
        'aire_end': np.array([])
    }
    
    if streamlines:
        shape.update({
            'alpha': np.array([]),
            'rsquare': np.array([]),
            'rmse': np.array([])
        })
    
    if extended_diags:
        shape.update({
            'ke': np.array([]),
            'vort': np.array([]),
            'vortM': np.array([]),
            'OW': np.array([]),
            'LNAM': np.array([])
        })
    
    return shape


def create_empty_shapes2():
    """Create empty shapes2 structure."""
    return {
        'step': None,
        'xy': [],
        'velmax': np.array([]),
        'deta': np.array([]),
        'taumin': np.array([]),
        'nrho': np.array([]),
        'rmax': np.array([]),
        'aire': np.array([]),
        'xbary': np.array([]),
        'ybary': np.array([]),
        'ellip': np.array([]),
        'theta': np.array([])
    }


def create_empty_warnings():
    """Create empty warnings structure."""
    return {
        'no_curve': np.array([]),
        'f': np.array([]),
        'Rd': np.array([]),
        'gama': np.array([]),
        'bx': np.array([]),
        'calcul_curve': np.array([]),
        'large_curve1': np.array([]),
        'large_curve2': np.array([]),
        'too_weak2': np.array([])
    }


def create_empty_profil():
    """Create empty profil structure."""
    return {
        'step': None,
        'nc': [],
        'eta': [],
        'rmoy': [],
        'vel': [],
        'tau': [],
        'nrhoi': [],
        'myfit': []
    }
