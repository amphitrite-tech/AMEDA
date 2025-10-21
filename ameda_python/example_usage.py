"""
Example usage of AMEDA Python implementation.

This demonstrates how to use the AMEDA algorithm to detect eddies
from synthetic velocity data.
"""

import numpy as np
import matplotlib.pyplot as plt
from ameda import mod_fields, utilities


def create_synthetic_eddy(n=60, eddy_type='anticyclonic'):
    """
    Create a synthetic Gaussian eddy for testing.
    
    Parameters
    ----------
    n : int
        Grid size
    eddy_type : str
        'anticyclonic' or 'cyclonic'
        
    Returns
    -------
    x, y : ndarray
        Grid coordinates (km)
    u, v : ndarray
        Velocity fields (m/s)
    mask : ndarray
        Ocean mask
    """
    # Create grid (in km)
    x = np.linspace(-200, 200, n)
    y = np.linspace(-200, 200, n)
    x, y = np.meshgrid(x, y)
    
    # Distance from center
    r = np.sqrt(x**2 + y**2)
    r[r == 0] = 1e-10
    
    # Gaussian vortex parameters
    vmax = 0.5  # m/s maximum velocity
    r0 = 50  # km eddy radius
    
    # Velocity field (positive for anticyclonic, negative for cyclonic)
    sign = -1 if eddy_type == 'anticyclonic' else 1
    
    u = sign * (-y / r) * vmax * (r / r0) * np.exp(-r**2 / (2 * r0**2))
    v = sign * (x / r) * vmax * (r / r0) * np.exp(-r**2 / (2 * r0**2))
    
    # Ocean mask (all water)
    mask = np.ones_like(x)
    
    return x, y, u, v, mask


def detect_eddy():
    """Run AMEDA eddy detection on synthetic data."""
    
    print("=" * 70)
    print("AMEDA Python - Synthetic Eddy Detection Example")
    print("=" * 70)
    print()
    
    # Create synthetic anticyclonic eddy
    print("Creating synthetic anticyclonic eddy...")
    x, y, u, v, mask = create_synthetic_eddy(n=60, eddy_type='anticyclonic')
    
    # Set up parameters
    print("Setting up parameters...")
    params = utilities.EDDYParams()
    
    # Box size for LNAM computation
    b = 3  # pixels
    
    # Coriolis parameter (at ~30°N latitude)
    latitude = 30.0
    f = 4 * np.pi / params.T * np.sin(np.deg2rad(latitude))
    f = np.ones_like(x) * f
    
    print(f"Grid size: {x.shape}")
    print(f"Velocity range: u=[{u.min():.3f}, {u.max():.3f}] m/s")
    print(f"Velocity range: v=[{v.min():.3f}, {v.max():.3f}] m/s")
    print(f"Coriolis parameter: f={f[0,0]:.2e} s^-1")
    print()
    
    # Compute detection fields
    print("Computing detection fields...")
    fields = mod_fields.mod_fields(x, y, mask, u, v, b, f, grid_ll=False)
    print()
    
    # Analyze results
    print("Analysis of computed fields:")
    print("-" * 70)
    
    for field_name, field_data in fields.items():
        valid_data = field_data[~np.isnan(field_data)]
        if len(valid_data) > 0:
            print(f"{field_name:6s}: min={np.min(valid_data):10.6f}, "
                  f"max={np.max(valid_data):10.6f}, "
                  f"mean={np.mean(valid_data):10.6f}")
    
    print()
    
    # Find LNAM maximum (should be near eddy center)
    lnam = fields['LNAM']
    max_lnam_idx = np.unravel_index(np.argmax(np.abs(lnam)), lnam.shape)
    max_lnam_value = lnam[max_lnam_idx]
    
    print("Eddy Detection Results:")
    print("-" * 70)
    print(f"LNAM maximum found at grid point: {max_lnam_idx}")
    print(f"Corresponding coordinates: x={x[max_lnam_idx]:.1f} km, "
          f"y={y[max_lnam_idx]:.1f} km")
    print(f"LNAM value: {max_lnam_value:.6f}")
    print(f"Eddy type: {'Anticyclonic' if max_lnam_value < 0 else 'Cyclonic'}")
    print()
    
    # Check if detection is near center
    distance_from_center = np.sqrt(x[max_lnam_idx]**2 + y[max_lnam_idx]**2)
    print(f"Distance from true center (0, 0): {distance_from_center:.1f} km")
    
    if distance_from_center < 30:  # Within ~30 km
        print("✓ SUCCESS: Eddy center correctly detected!")
    else:
        print("⚠ WARNING: Detection may be inaccurate")
    
    print()
    
    # Plot results
    print("Generating visualization...")
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    # Velocity magnitude
    vel_mag = np.sqrt(u**2 + v**2)
    im1 = axes[0, 0].contourf(x, y, vel_mag, levels=20, cmap='viridis')
    axes[0, 0].quiver(x[::3, ::3], y[::3, ::3], u[::3, ::3], v[::3, ::3], 
                      color='white', alpha=0.5)
    axes[0, 0].plot(x[max_lnam_idx], y[max_lnam_idx], 'r*', markersize=15, 
                    label='Detected center')
    axes[0, 0].set_title('Velocity Magnitude (m/s)')
    axes[0, 0].set_xlabel('X (km)')
    axes[0, 0].set_ylabel('Y (km)')
    axes[0, 0].legend()
    plt.colorbar(im1, ax=axes[0, 0])
    
    # LNAM
    im2 = axes[0, 1].contourf(x, y, lnam, levels=20, cmap='RdBu_r')
    axes[0, 1].plot(x[max_lnam_idx], y[max_lnam_idx], 'k*', markersize=15)
    axes[0, 1].set_title('LNAM')
    axes[0, 1].set_xlabel('X (km)')
    axes[0, 1].set_ylabel('Y (km)')
    plt.colorbar(im2, ax=axes[0, 1])
    
    # Vorticity
    im3 = axes[0, 2].contourf(x, y, fields['vort'], levels=20, cmap='RdBu_r')
    axes[0, 2].set_title('Vorticity (s^-1)')
    axes[0, 2].set_xlabel('X (km)')
    axes[0, 2].set_ylabel('Y (km)')
    plt.colorbar(im3, ax=axes[0, 2])
    
    # Okubo-Weiss
    im4 = axes[1, 0].contourf(x, y, fields['OW'], levels=20, cmap='RdBu_r')
    axes[1, 0].set_title('Okubo-Weiss (s^-2)')
    axes[1, 0].set_xlabel('X (km)')
    axes[1, 0].set_ylabel('Y (km)')
    plt.colorbar(im4, ax=axes[1, 0])
    
    # LOW
    im5 = axes[1, 1].contourf(x, y, fields['LOW'], levels=20, cmap='RdBu_r')
    axes[1, 1].set_title('Local Okubo-Weiss')
    axes[1, 1].set_xlabel('X (km)')
    axes[1, 1].set_ylabel('Y (km)')
    plt.colorbar(im5, ax=axes[1, 1])
    
    # Kinetic Energy
    im6 = axes[1, 2].contourf(x, y, fields['ke'], levels=20, cmap='hot_r')
    axes[1, 2].set_title('Kinetic Energy (m^2/s^2)')
    axes[1, 2].set_xlabel('X (km)')
    axes[1, 2].set_ylabel('Y (km)')
    plt.colorbar(im6, ax=axes[1, 2])
    
    plt.tight_layout()
    
    # Save figure
    output_file = 'eddy_detection_example.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"Figure saved as: {output_file}")
    
    print()
    print("=" * 70)
    print("Example completed successfully!")
    print("=" * 70)
    
    return fields, (x, y, u, v, mask)


if __name__ == '__main__':
    fields, data = detect_eddy()
    
    # Optionally show the plot
    try:
        plt.show()
    except:
        print("(Plot display not available in this environment)")
