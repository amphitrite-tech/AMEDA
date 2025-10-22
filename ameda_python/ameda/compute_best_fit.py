"""
Compute best fit for eddy velocity profile.

Fits the theoretical eddy velocity profile:
    V/Vmax = (R/Rmax) * exp((1 - (R/Rmax)^alpha) / alpha)

where alpha is the eddy degree (alpha=2 for Gaussian).
"""

import numpy as np
from scipy.optimize import curve_fit
import warnings


def eddy_profile_model(r_normalized, alpha):
    """
    Theoretical eddy velocity profile.
    
    Parameters
    ----------
    r_normalized : array-like
        Normalized radius R/Rmax
    alpha : float
        Eddy degree parameter (2 for Gaussian)
        
    Returns
    -------
    v_normalized : ndarray
        Normalized velocity V/Vmax
    """
    # Avoid division by zero
    alpha = max(alpha, 0.01)
    
    # V/Vmax = (R/Rmax) * exp((1 - (R/Rmax)^alpha) / alpha)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = r_normalized * np.exp((1 - r_normalized**alpha) / alpha)
    
    # Handle any NaN or inf values
    result = np.nan_to_num(result, nan=0.0, posinf=1.0, neginf=0.0)
    
    return result


def compute_best_fit(lines, rmax, rend, velmax):
    """
    Compute best fit over an eddy velocity profile V/Vmax = f(R/Rmax).
    
    The curve to fit has the form:
        Vr = Ro * exp((1 - Ro^alpha) / alpha)
    
    where:
        Vr = V / Vmax (normalized velocity)
        Ro = R / Rmax (normalized radius)
        alpha is the eddy degree to be fitted (alpha=2 for Gaussian)
    
    The curve is maximal for Vr=1 at Ro=1.
    
    Parameters
    ----------
    lines : ndarray
        Profile lines from max_curve with columns:
        [nc, eta, rmoy, vel, tau, nrho]
    rmax : float
        Radius at maximum velocity (km)
    rend : float
        End radius (km)
    velmax : float
        Maximum velocity (m/s)
        
    Returns
    -------
    curve : dict or None
        Fitted curve parameters: {'a': alpha, 'model': function}
    err : dict or None
        Error statistics: {'rsquare': R², 'rmse': RMSE, 'chi2': χ²}
    """
    # Initialize
    curve = None
    err = None
    
    if lines.size == 0 or len(lines.shape) < 2:
        return curve, err
    
    # Read profile lines
    nc = lines[:, 0]    # number of centers
    eta = lines[:, 1]   # ssh level
    rmoy = lines[:, 2]  # mean radius
    vel = lines[:, 3]   # velocity
    tau = lines[:, 4]   # turnover time
    
    # Resize rmoy and vel (only use points within rend)
    mask = rmoy <= rend
    vel = vel[mask]
    rmoy = rmoy[mask]
    nc_filtered = nc[mask]
    
    if len(rmoy) <= 5:
        return curve, err
    
    # Take part of profile with no gap between points
    # Skip potential gap at beginning
    if len(rmoy) > 6:
        diffs = np.diff(rmoy[5:])
        mean_diff = np.mean(np.diff(rmoy))
        gap_idx = np.where(diffs > 2 * mean_diff)[0]
        
        if len(gap_idx) > 0:
            indx = gap_idx[0] + 5
        else:
            indx = len(rmoy)
    else:
        indx = len(rmoy)
    
    # Need decreasing points
    indx1 = np.where(rmoy[:indx] < rmax)[0]  # points before rmax
    indx2 = np.where(rmoy[:indx] > rmax)[0]  # points after rmax
    
    # Choose profile with 1 center, long enough, with decreasing part
    if (nc_filtered[indx-1] < 2 and 
        len(indx1) > 6 and 
        len(indx2) > 0.25 * len(indx1) and
        np.min(vel[indx2]) < 0.95 * velmax and 
        np.max(vel[indx2]) < 1.01 * velmax):
        
        # Curve fitting
        x = rmoy[:indx] / rmax  # [0-2]*rmax normalized
        y = vel[:indx] / velmax  # [0-1]*velmax normalized
        
        # Ensure column vectors
        x = x.flatten()
        y = y.flatten()
        
        try:
            # Fit the model
            # Use curve_fit with bounds to ensure reasonable alpha
            popt, pcov = curve_fit(
                eddy_profile_model, 
                x, 
                y, 
                p0=[2.0],  # Start with Gaussian (alpha=2)
                bounds=([0.5], [10.0]),  # Reasonable bounds for alpha
                maxfev=5000
            )
            
            alpha = popt[0]
            
            # Compute fitted values
            y_fit = eddy_profile_model(x, alpha)
            
            # Calculate error statistics
            residuals = y - y_fit
            ss_res = np.sum(residuals**2)
            ss_tot = np.sum((y - np.mean(y))**2)
            
            # R-squared
            rsquare = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            # RMSE (Root Mean Square Error)
            rmse = np.sqrt(np.mean(residuals**2))
            
            # Chi-squared
            # Assuming unit variance for simplicity
            chi2 = ss_res / len(y) if len(y) > 1 else 0
            
            # Store results
            curve = {
                'a': alpha,
                'model': lambda r: eddy_profile_model(r, alpha),
                'params': popt,
                'covariance': pcov
            }
            
            err = {
                'rsquare': rsquare,
                'rmse': rmse,
                'chi2': chi2,
                'residuals': residuals
            }
            
        except (RuntimeError, ValueError) as e:
            # Fitting failed
            curve = None
            err = None
    
    return curve, err
