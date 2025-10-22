"""
AMEDA - Angular Momentum Eddy Detection Algorithm
Python implementation

Full translation of the AMEDA algorithm for MATLAB to Python.
See Le Vu et al. 2018 (https://doi.org/10.1175/JTECH-D-17-0010.1) for details.

License: CC BY-NC-SA 4.0 International
"""

__version__ = '1.0.0'
__author__ = 'AMEDA Python'

from . import utilities
from . import sw_dist
from . import compute_psi
from . import mean_radius
from . import compute_ellip
from . import compute_curve
from . import scan_lines
from . import integrate_vel
from . import max_curve
from . import eddy_dim
from . import mod_fields
from . import mod_eddy_centers
from . import mod_eddy_shapes
from . import compute_best_fit
from . import min_dist_shapes
from . import concat_eddy
from . import mod_init
from . import mod_eddy_tracks
from . import mod_merging_splitting
from . import load_fields

__all__ = [
    'utilities',
    'sw_dist',
    'compute_psi',
    'mean_radius',
    'compute_ellip',
    'compute_curve',
    'scan_lines',
    'integrate_vel',
    'max_curve',
    'eddy_dim',
    'mod_fields',
    'mod_eddy_centers',
    'mod_eddy_shapes',
    'compute_best_fit',
    'min_dist_shapes',
    'concat_eddy',
    'mod_init',
    'mod_eddy_tracks',
    'mod_merging_splitting',
    'load_fields',
]
