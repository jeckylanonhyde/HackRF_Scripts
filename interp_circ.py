import numpy as np
from numpy.polynomial import Polynomial
import matplotlib.pyplot as plt

def rodrigues_rot(P, n0, n1):
    """
    Rotates a set of points P from vector n0 to vector n1 using Rodrigues' rotation formula.
    """
    P = np.atleast_2d(P)  # Ensure P is at least 2D for consistency
    n0 = n0 / np.linalg.norm(n0)
    n1 = n1 / np.linalg.norm(n1)
    k = np.cross(n0, n1)
    k_norm = np.linalg.norm(k)
    if k_norm != 0:
        k /= k_norm
    theta = np.arccos(np.clip(np.dot(n0, n1), -1.0, 1.0))

    cos_theta = np.cos(theta)
    sin_theta = np.sin(theta)
    k_outer = np.outer(k, k)
    k_cross = np.array([[0, -k[2], k[1]],
                        [k[2], 0, -k[0]],
                        [-k[1], k[0], 0]])

    rot_matrix = cos_theta * np.eye(3) + sin_theta * k_cross + (1 - cos_theta) * k_outer
    return np.dot(P, rot_matrix.T)

def linear_interpolation(y, t, t0, plot=False):
    """
    Linear interpolation of y over time t to find value at t0.
    """
    model = np.polyfit(t, y, 1)
    p = np.poly1d(model)
    y0 = p(t0)

    if plot:
        plt.plot(t, y, "-*", label="Data Points")
        plt.scatter([t0], [y0], label=f"Interpolated Point at t={t0}", color="red")
        t_fit = np.linspace(t[0], t[-1], 100)
        plt.plot(t_fit, p(t_fit), label="Linear Fit")
        plt.legend()
        plt.show()

    return y0

def quadratic_interpolation(y, t, t0, plot=False):
    """
    Quadratic interpolation of y over time t to find value at t0.
    """
    p = Polynomial.fit(t, y, deg=2)
    y0 = p(t0)

    if plot:
        plt.plot(t, y, "-*", label="Data Points")
        plt.scatter([t0], [y0], label=f"Interpolated Point at t={t0}", color="red")
        t_fit = np.linspace(t[0], t[-1], 100)
        plt.plot(t_fit, p(t_fit), label="Quadratic Fit")
        plt.legend()
        plt.show()

    return y0

def interpolate_on_circle(P, T, t_target, plot=False):
    """
    Interpolates the position of a point on a circle at a specific time.
    """
    P = np.array(P)

    # Calculate radii at each time step
    R = np.linalg.norm(P, axis=0)
    r_target = linear_interpolation(R, T, t_target, plot)

    # Compute the plane normal
    _, _, V = np.linalg.svd(P.T)
    normal = V[2, :]

    # Rotate points onto the XY plane
    P_xy = rodrigues_rot(P.T, normal, [0, 0, 1])

    # Compute angles and unwrap to remove discontinuities
    angles = np.unwrap(np.arctan2(P_xy[:, 1], P_xy[:, 0]))

    # Interpolate angle at the target time
    angle_target = linear_interpolation(angles, T, t_target, plot)

    # Compute the interpolated point on the circle
    x_target = np.cos(angle_target) * r_target
    y_target = np.sin(angle_target) * r_target
    z_target = 0  # Assume Z is zero in the plane

    # Rotate back to the original plane
    rotated_point = rodrigues_rot(np.array([x_target, y_target, z_target]), [0, 0, 1], normal).flatten()
    return rotated_point

# Alias functions for backward compatibility
lin_interp = linear_interpolation
quad_interp = quadratic_interpolation
interp = interpolate_on_circle