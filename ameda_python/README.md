# AMEDA - Python Implementation

**Angular Momentum Eddy Detection Algorithm**

This is a complete Python translation of the AMEDA algorithm from MATLAB.

## Overview

AMEDA (Angular Momentum Eddy Detection Algorithm) is a method for detecting and tracking mesoscale ocean eddies from velocity fields or SSH data.

See [Le Vu et al. 2018](https://doi.org/10.1175/JTECH-D-17-0010.1) for details about the method.

## Features

This Python implementation includes:

- **Field Computation** (`mod_fields`): Computes LNAM, Okubo-Weiss, vorticity, and other fields
- **Center Detection** (`mod_eddy_centers`): Detects potential eddy centers
- **Shape Detection** (`mod_eddy_shapes`): Determines eddy boundaries and characteristics
- **Helper Functions**: 
  - `compute_psi`: Streamfunction computation
  - `eddy_dim`: Eddy dimension calculation
  - `max_curve`: Maximum velocity contour finding
  - `mean_radius`: Radius and area calculations
  - `compute_ellip`: Ellipse fitting
  - `compute_curve`: Curvature computation
  - `sw_dist`: Distance calculations for lat/lon coordinates

## Installation

```bash
cd ameda_python
pip install -r requirements.txt
```

## Usage

```python
import numpy as np
from ameda import mod_fields, utilities

# Load or create velocity data
u = ...  # zonal velocity (m/s)
v = ...  # meridional velocity (m/s)
x, y = ...  # coordinates
mask = ...  # ocean mask

# Set parameters
params = utilities.EDDYParams()
b = 2  # box size parameter
f = 4 * np.pi / 86400 * np.sin(np.deg2rad(y))  # Coriolis

# Compute fields
fields = mod_fields.mod_fields(x, y, mask, u, v, b, f, grid_ll=True)

# Access results
lnam = fields['LNAM']  # Local Normalized Angular Momentum
okubo_weiss = fields['OW']  # Okubo-Weiss parameter
vorticity = fields['vort']  # Vorticity field
```

## Module Structure

```
ameda/
├── __init__.py           # Package initialization
├── utilities.py          # Utility functions and parameters
├── sw_dist.py           # Distance calculations
├── compute_psi.py       # Streamfunction computation
├── mean_radius.py       # Radius calculations
├── compute_ellip.py     # Ellipse fitting
├── compute_curve.py     # Curvature computation
├── scan_lines.py        # Contour line processing
├── integrate_vel.py     # Velocity integration
├── max_curve.py         # Maximum velocity contour
├── eddy_dim.py          # Eddy dimension computation
├── mod_fields.py        # Field computation module
├── mod_eddy_centers.py  # Center detection (to be completed)
└── mod_eddy_shapes.py   # Shape detection (to be completed)
```

## Testing

Run the comprehensive test suite:

```bash
cd ameda_python
python -m pytest tests/ -v
```

Or run the test script directly:

```bash
python tests/test_ameda.py
```

## Algorithm Steps

1. **Compute Fields**: Calculate LNAM, Okubo-Weiss, vorticity
2. **Find Centers**: Detect eddy centers from LNAM extrema
3. **Determine Shapes**: Find eddy boundaries using streamlines
4. **Track Eddies**: Follow eddies through time (future work)
5. **Handle Interactions**: Resolve merging/splitting events (future work)

## Parameters

Key parameters in `EDDYParams`:

- `K`: LNAM threshold (default: 0.7)
- `DH`: SSH spacing for streamlines (default: 0.002 m)
- `n_min`: Minimum points for contour (default: 6)
- `k_vel_decay`: Velocity decay coefficient (default: 0.97)
- `nR_lim`: Size limit in deformation radii (default: 100)
- `nrho_lim`: Curvature limit (default: 0.2)

## License

CC BY-NC-SA 4.0 International

## Reference

Le Vu, B., Stegner, A., & Arsouze, T. (2018). Angular Momentum Eddy Detection and tracking Algorithm (AMEDA) and its application to coastal eddy formation. *Journal of Atmospheric and Oceanic Technology*, 35(4), 739-762.

## Status

This is a working implementation with:
- ✅ Complete utility functions
- ✅ Field computation (mod_fields)
- ✅ Helper functions (compute_psi, eddy_dim, max_curve, etc.)
- ✅ Comprehensive test suite
- ⏳ Center detection (partial)
- ⏳ Shape detection (partial)
- ⏳ Tracking (future work)
- ⏳ Merging/splitting (future work)
