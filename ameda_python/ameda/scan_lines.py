"""
Rearrange contour lines into structure array.
"""

import numpy as np


def scan_lines(C):
    """
    Rearrange streamlines from contour matrix into structured array.
    
    Sorts contours by maximum y coordinate. Each element contains all vertices
    of a given contour level.
    
    Parameters
    ----------
    C : ndarray
        Contour matrix from matplotlib.pyplot.contour
        
    Returns
    -------
    lines : list of dict
        List of dictionaries with keys 'x', 'y', 'l' (max y coord)
    lvl : ndarray
        Level values of streamlines
    """
    lines = []
    lvl = []
    
    k = 0  # position in C
    
    while k < C.shape[1]:
        npoints = int(C[1, k])
        level = C[0, k]
        
        if k + npoints < C.shape[1]:
            x_coords = C[0, k+1:k+1+npoints]
            y_coords = C[1, k+1:k+1+npoints]
            
            lines.append({
                'x': x_coords,
                'y': y_coords,
                'l': np.max(y_coords)
            })
            lvl.append(level)
        
        k = k + npoints + 1
    
    # Sort contours by maximum y coordinate
    if lines:
        order = np.argsort([line['l'] for line in lines])
        lines = [lines[i] for i in order]
        lvl = np.array([lvl[i] for i in order])
    else:
        lvl = np.array([])
    
    return lines, lvl
