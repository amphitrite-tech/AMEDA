"""
Data loading functions for various oceanographic data sources.

Provides loaders for AVISO, ROMS, NEMO and generic NetCDF data.
"""

import numpy as np
from scipy.interpolate import RegularGridInterpolator, RectBivariateSpline
import netCDF4 as nc


def load_fields_generic(filepath, stp, var_names, resolution=1, deg=1, 
                       grid_ll=True, type_detection=3):
    """
    Generic NetCDF field loader.
    
    Parameters
    ----------
    filepath : str or dict
        Path to NetCDF file, or dict with paths for different variables
    stp : int
        Time step to load
    var_names : dict
        Dictionary mapping variable types to NetCDF variable names:
        {'x': 'lon', 'y': 'lat', 'u': 'u', 'v': 'v', 'ssh': 'ssh', 'mask': 'mask'}
    resolution : int, optional
        Interpolation factor (1=no interpolation)
    deg : int, optional
        Degradation factor
    grid_ll : bool, optional
        True if lat/lon grid
    type_detection : int, optional
        Detection type (1=psi, 2=ssh, 3=both)
        
    Returns
    -------
    x, y : ndarray
        Grid coordinates
    mask : ndarray
        Ocean mask (1=ocean, 0=land)
    u, v : ndarray
        Velocity fields (m/s)
    ssh : ndarray or None
        Sea surface height (m)
    """
    # Open NetCDF file(s)
    if isinstance(filepath, dict):
        # Different files for different variables
        ds_dict = {key: nc.Dataset(path, 'r') for key, path in filepath.items()}
        ds_x = ds_dict.get('dim', ds_dict.get('u'))
        ds_u = ds_dict.get('u')
        ds_v = ds_dict.get('v')
        ds_ssh = ds_dict.get('ssh', None)
    else:
        # Single file
        ds_x = ds_u = ds_v = ds_ssh = nc.Dataset(filepath, 'r')
    
    print(f'Loading grid and velocities field at step {stp}...')
    
    # Load coordinates
    x_var = var_names.get('x', 'lon')
    y_var = var_names.get('y', 'lat')
    
    lon0 = np.array(ds_x.variables[x_var][:])
    lat0 = np.array(ds_x.variables[y_var][:])
    
    # Ensure 2D grids
    if lon0.ndim == 1 and lat0.ndim == 1:
        lon0, lat0 = np.meshgrid(lon0, lat0)
    elif lon0.ndim == 1:
        lon0 = np.tile(lon0, (len(lat0), 1))
    elif lat0.ndim == 1:
        lat0 = np.tile(lat0[:, np.newaxis], (1, lon0.shape[1]))
    
    # Load velocity fields
    u_var = var_names.get('u', 'u')
    v_var = var_names.get('v', 'v')
    
    u0 = np.array(ds_u.variables[u_var][stp, ...]).squeeze()
    v0 = np.array(ds_v.variables[v_var][stp, ...]).squeeze()
    
    # Transpose if needed to match (lat, lon) convention
    if u0.shape != lon0.shape:
        u0 = u0.T
        v0 = v0.T
    
    # Load or create mask
    mask_var = var_names.get('mask', None)
    if mask_var and mask_var in ds_x.variables:
        mask0 = np.array(ds_x.variables[mask_var][:]).squeeze()
        if mask0.shape != lon0.shape:
            mask0 = mask0.T
    else:
        # Create mask from valid data
        mask0 = (~np.isnan(u0) & ~np.isnan(v0)).astype(int)
    
    # Load SSH if needed
    if type_detection >= 2 and ds_ssh is not None:
        ssh_var = var_names.get('ssh', 'ssh')
        if ssh_var in ds_ssh.variables:
            ssh0 = np.array(ds_ssh.variables[ssh_var][stp, ...]).squeeze()
            if ssh0.shape != lon0.shape:
                ssh0 = ssh0.T
        else:
            ssh0 = None
    else:
        ssh0 = None
    
    # Close datasets
    if isinstance(filepath, dict):
        for ds in ds_dict.values():
            ds.close()
    else:
        ds_x.close()
    
    # Apply degradation
    if deg != 1:
        print(f'  Fields degraded by factor {deg}')
        x = lon0[::deg, ::deg]
        y = lat0[::deg, ::deg]
        mask = mask0[::deg, ::deg]
        u = u0[::deg, ::deg]
        v = v0[::deg, ::deg]
        ssh = ssh0[::deg, ::deg] if ssh0 is not None else None
    else:
        x, y, mask, u, v = lon0, lat0, mask0, u0, v0
        ssh = ssh0
    
    N, M = x.shape
    
    # Apply interpolation if needed
    if resolution == 1:
        print('NO INTERPOLATION')
        
        # Set land to NaN
        u[mask == 0] = np.nan
        v[mask == 0] = np.nan
        
        # Enlarge mask into land by 1 pixel
        print('Enlarging coastal mask by 1 pixel...')
        for i in range(N):
            for j in range(M):
                if mask[i, j] == 0:
                    neighbors = mask[max(i-1, 0):min(i+2, N), max(j-1, 0):min(j+2, M)]
                    if np.sum(neighbors) > 0:
                        u[i, j] = 0
                        v[i, j] = 0
                        if ssh is not None and np.isnan(ssh[i, j]):
                            ssh_neighbors = ssh[max(i-1, 0):min(i+2, N), max(j-1, 0):min(j+2, M)]
                            ssh[i, j] = np.nanmean(ssh_neighbors)
    else:
        print(f'Interpolating by factor {resolution}')
        
        # Interpolate grid
        Ni = resolution * (N - 1) + 1
        Mi = resolution * (M - 1) + 1
        
        dy = (y[1, 0] - y[0, 0]) / resolution
        dx = (x[0, 1] - x[0, 0]) / resolution
        
        xi = np.arange(Mi) * dx + x.min()
        yi = np.arange(Ni) * dy + y.min()
        xi, yi = np.meshgrid(xi, yi)
        
        # Interpolate mask
        from scipy.interpolate import RectBivariateSpline
        mask_interp = RectBivariateSpline(y[:, 0], x[0, :], mask, kx=1, ky=1)
        maski = mask_interp(yi[:, 0], xi[0, :])
        maski[maski < 0.5] = 0
        maski[maski >= 0.5] = 1
        
        # Interpolate velocities (set land to 0 first)
        u[mask == 0] = 0
        v[mask == 0] = 0
        
        u_interp = RectBivariateSpline(y[:, 0], x[0, :], u, kx=3, ky=3)
        v_interp = RectBivariateSpline(y[:, 0], x[0, :], v, kx=3, ky=3)
        
        ui = u_interp(yi[:, 0], xi[0, :])
        vi = v_interp(yi[:, 0], xi[0, :])
        
        # Interpolate SSH if present
        if ssh is not None:
            ssh_interp = RectBivariateSpline(y[:, 0], x[0, :], np.nan_to_num(ssh, 0), kx=3, ky=3)
            sshi = ssh_interp(yi[:, 0], xi[0, :])
        else:
            sshi = None
        
        # Apply mask
        ui[maski == 0] = np.nan
        vi[maski == 0] = np.nan
        if sshi is not None:
            sshi[maski == 0] = np.nan
        
        x, y, mask, u, v, ssh = xi, yi, maski, ui, vi, sshi
    
    return x, y, mask, u, v, ssh


def load_fields_AVISO(nc_files, stp, resolution=1, deg=1, type_detection=3):
    """
    Load AVISO satellite altimetry data.
    
    Parameters
    ----------
    nc_files : dict
        Dictionary with NetCDF file paths:
        {'dim': path, 'u': path, 'v': path, 'ssh': path}
    stp : int
        Time step
    resolution : int
        Interpolation factor
    deg : int
        Degradation factor
    type_detection : int
        Detection type
        
    Returns
    -------
    x, y, mask, u, v, ssh : ndarray
        Grid and fields
    """
    var_names = {
        'x': 'longitude',
        'y': 'latitude',
        'u': 'u',
        'v': 'v',
        'ssh': 'adt',
        'mask': None
    }
    
    return load_fields_generic(nc_files, stp, var_names, resolution, deg, 
                              grid_ll=True, type_detection=type_detection)


def load_fields_ROMS(nc_files, stp, resolution=1, deg=1, type_detection=3):
    """
    Load ROMS model output.
    
    Parameters
    ----------
    nc_files : dict
        Dictionary with NetCDF file paths
    stp : int
        Time step
    resolution : int
        Interpolation factor
    deg : int
        Degradation factor
    type_detection : int
        Detection type
        
    Returns
    -------
    x, y, mask, u, v, ssh : ndarray
        Grid and fields
    """
    var_names = {
        'x': 'lon_rho',
        'y': 'lat_rho',
        'u': 'u',
        'v': 'v',
        'ssh': 'zeta',
        'mask': 'mask_rho'
    }
    
    return load_fields_generic(nc_files, stp, var_names, resolution, deg,
                              grid_ll=True, type_detection=type_detection)


def load_fields_NEMO(nc_files, stp, level=0, resolution=1, deg=1, type_detection=3):
    """
    Load NEMO model output.
    
    Parameters
    ----------
    nc_files : dict
        Dictionary with NetCDF file paths
    stp : int
        Time step
    level : int
        Vertical level
    resolution : int
        Interpolation factor
    deg : int
        Degradation factor
    type_detection : int
        Detection type
        
    Returns
    -------
    x, y, mask, u, v, ssh : ndarray
        Grid and fields
    """
    var_names = {
        'x': 'nav_lon',
        'y': 'nav_lat',
        'u': 'vozocrtx',
        'v': 'vomecrty',
        'ssh': 'sossheig',
        'mask': 'tmask'
    }
    
    # NEMO has 3D fields, need to extract level
    # This is simplified - real implementation would handle vertical levels
    
    return load_fields_generic(nc_files, stp, var_names, resolution, deg,
                              grid_ll=True, type_detection=type_detection)


def load_fields_from_arrays(x, y, u, v, ssh=None, mask=None, resolution=1):
    """
    Load fields from numpy arrays (for testing or custom data).
    
    Parameters
    ----------
    x, y : ndarray
        Grid coordinates
    u, v : ndarray
        Velocity fields (m/s)
    ssh : ndarray, optional
        Sea surface height (m)
    mask : ndarray, optional
        Ocean mask (1=ocean, 0=land)
    resolution : int, optional
        Interpolation factor
        
    Returns
    -------
    x, y, mask, u, v, ssh : ndarray
        Processed grid and fields
    """
    if mask is None:
        mask = (~np.isnan(u) & ~np.isnan(v)).astype(int)
    
    if resolution == 1:
        return x, y, mask, u, v, ssh
    else:
        # Apply interpolation
        N, M = x.shape
        Ni = resolution * (N - 1) + 1
        Mi = resolution * (M - 1) + 1
        
        dy = (y[1, 0] - y[0, 0]) / resolution
        dx = (x[0, 1] - x[0, 0]) / resolution
        
        xi = np.arange(Mi) * dx + x.min()
        yi = np.arange(Ni) * dy + y.min()
        xi, yi = np.meshgrid(xi, yi)
        
        # Interpolate fields
        from scipy.interpolate import RectBivariateSpline
        
        u_clean = np.nan_to_num(u, 0)
        v_clean = np.nan_to_num(v, 0)
        
        u_interp = RectBivariateSpline(y[:, 0], x[0, :], u_clean, kx=3, ky=3)
        v_interp = RectBivariateSpline(y[:, 0], x[0, :], v_clean, kx=3, ky=3)
        
        ui = u_interp(yi[:, 0], xi[0, :])
        vi = v_interp(yi[:, 0], xi[0, :])
        
        # Interpolate mask
        mask_interp = RectBivariateSpline(y[:, 0], x[0, :], mask, kx=1, ky=1)
        maski = mask_interp(yi[:, 0], xi[0, :])
        maski[maski < 0.5] = 0
        maski[maski >= 0.5] = 1
        
        # Interpolate SSH if present
        if ssh is not None:
            ssh_clean = np.nan_to_num(ssh, 0)
            ssh_interp = RectBivariateSpline(y[:, 0], x[0, :], ssh_clean, kx=3, ky=3)
            sshi = ssh_interp(yi[:, 0], xi[0, :])
        else:
            sshi = None
        
        # Apply mask
        ui[maski == 0] = np.nan
        vi[maski == 0] = np.nan
        if sshi is not None:
            sshi[maski == 0] = np.nan
        
        return xi, yi, maski, ui, vi, sshi


class DataLoader:
    """
    Flexible data loader for various oceanographic data sources.
    
    Examples
    --------
    >>> # Load from NetCDF
    >>> loader = DataLoader('AVISO')
    >>> loader.set_files(u='u_file.nc', v='v_file.nc', ssh='ssh_file.nc')
    >>> x, y, mask, u, v, ssh = loader.load(stp=0)
    
    >>> # Load from arrays
    >>> loader = DataLoader('custom')
    >>> x, y, mask, u, v, ssh = loader.load_from_arrays(x, y, u, v, ssh)
    """
    
    def __init__(self, source='generic'):
        """
        Initialize data loader.
        
        Parameters
        ----------
        source : str
            Data source type ('AVISO', 'ROMS', 'NEMO', 'custom', 'generic')
        """
        self.source = source
        self.files = {}
        self.var_names = self._get_default_var_names(source)
    
    def _get_default_var_names(self, source):
        """Get default variable names for different sources."""
        defaults = {
            'AVISO': {'x': 'longitude', 'y': 'latitude', 'u': 'u', 'v': 'v', 
                     'ssh': 'adt', 'mask': None},
            'ROMS': {'x': 'lon_rho', 'y': 'lat_rho', 'u': 'u', 'v': 'v',
                    'ssh': 'zeta', 'mask': 'mask_rho'},
            'NEMO': {'x': 'nav_lon', 'y': 'nav_lat', 'u': 'vozocrtx', 
                    'v': 'vomecrty', 'ssh': 'sossheig', 'mask': 'tmask'},
            'generic': {'x': 'lon', 'y': 'lat', 'u': 'u', 'v': 'v',
                       'ssh': 'ssh', 'mask': 'mask'}
        }
        return defaults.get(source, defaults['generic'])
    
    def set_files(self, **kwargs):
        """Set file paths for different variables."""
        self.files.update(kwargs)
    
    def set_var_names(self, **kwargs):
        """Override default variable names."""
        self.var_names.update(kwargs)
    
    def load(self, stp, resolution=1, deg=1, type_detection=3):
        """
        Load fields for given time step.
        
        Parameters
        ----------
        stp : int
            Time step
        resolution : int
            Interpolation factor
        deg : int
            Degradation factor
        type_detection : int
            Detection type
            
        Returns
        -------
        x, y, mask, u, v, ssh : ndarray
            Grid and fields
        """
        if not self.files:
            raise ValueError("No files set. Use set_files() first.")
        
        return load_fields_generic(self.files, stp, self.var_names, 
                                  resolution, deg, True, type_detection)
    
    def load_from_arrays(self, x, y, u, v, ssh=None, mask=None, resolution=1):
        """Load from numpy arrays instead of files."""
        return load_fields_from_arrays(x, y, u, v, ssh, mask, resolution)
