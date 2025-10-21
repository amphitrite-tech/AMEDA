"""
Distance calculations between lat/lon coordinates.
Adapted from CSIRO sw_dist function.
"""

import numpy as np


def sw_dist2(lat, lon):
    """
    Calculate distance between two lat,lon coordinates in km using Plane Sailing method.
    
    Parameters
    ----------
    lat : array-like
        Latitude in decimal degrees (+ve N, -ve S) [-90..+90]
    lon : array-like
        Longitude in decimal degrees (+ve E, -ve W) [-180..+180]
        
    Returns
    -------
    dist : ndarray
        Distance between consecutive positions in km
        
    References
    ----------
    The PLANE SAILING method as described in "CELESTIAL NAVIGATION" 1989 by
    Dr. P. Gormley. The Australian Antarctic Division.
    """
    # Constants
    DEG2RAD = 2 * np.pi / 360
    DEG2NM = 60  # Nautical miles per degree
    NM2KM = 1.8520  # Nautical miles to kilometers
    
    lat = np.asarray(lat)
    lon = np.asarray(lon)
    
    # Calculate differences
    dlon = np.diff(lon)
    
    # Handle wrapping around 180 degrees
    if np.any(np.abs(dlon) > 180):
        flag = np.abs(dlon) > 180
        dlon[flag] = -np.sign(dlon[flag]) * (360 - np.abs(dlon[flag]))
    
    # Convert to radians
    latrad = np.abs(lat * DEG2RAD)
    
    # Calculate departure
    ind = np.arange(len(lat) - 1)
    dep = np.cos((latrad[ind + 1] + latrad[ind]) / 2) * dlon
    
    # Calculate latitude difference
    dlat = np.diff(lat)
    
    # Calculate distance in nautical miles
    dist = DEG2NM * np.sqrt(dlat**2 + dep**2)
    
    # Convert to kilometers
    dist = dist * NM2KM
    
    return dist
