from scipy.optimize import minimize
import numpy as np

def dist(a, b):
    """Calculate the Euclidean distance between two points."""
    return np.linalg.norm(a - b)

def cost_function(approx, deltaranges):
    """
    Cost function for the 3D multilateration problem.
    Computes the squared error between measured and predicted delta ranges.

    Parameters:
        approx (ndarray): Current estimated position.
        deltaranges (list): List of tuples (ref_pos, station_pos, delta_range).

    Returns:
        float: Sum of squared errors.
    """
    return sum((dr[2] - (dist(dr[1], approx) - dist(dr[0], approx)))**2 for dr in deltaranges)

def solve(pseudoranges, guess):
    """
    Solve for the approximate position using pseudorange data and an initial guess.

    Parameters:
        pseudoranges (list): List of tuples (station_position, pseudorange).
        guess (ndarray): Initial guess for the position.

    Returns:
        ndarray: Estimated position.
    """
    ref_position, ref_pseudorange = pseudoranges[0]
    c = 299792458  # Speed of light in m/s

    # Compute delta ranges based on pseudoranges
    deltaranges = [
        (ref_position, station_position, (pseudorange - ref_pseudorange) * c)
        for station_position, pseudorange in pseudoranges[1:]
    ]

    # Minimize the cost function to find the optimal position
    result = minimize(cost_function, guess, args=(deltaranges,), method='L-BFGS-B')
    return result.x