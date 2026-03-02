import math
import numpy as np


def bezier_2d(p0, p1, control, n_points=20):
    ts = np.linspace(0, 1, n_points)
    xs = (1 - ts) ** 2 * p0[0] + 2 * (1 - ts) * ts * control[0] + ts ** 2 * p1[0]
    ys = (1 - ts) ** 2 * p0[1] + 2 * (1 - ts) * ts * control[1] + ts ** 2 * p1[1]
    return xs, ys


def bezier_3d(p0, p1, control, n_points=20):
    ts = np.linspace(0, 1, n_points)
    xs = (1 - ts) ** 2 * p0[0] + 2 * (1 - ts) * ts * control[0] + ts ** 2 * p1[0]
    ys = (1 - ts) ** 2 * p0[1] + 2 * (1 - ts) * ts * control[1] + ts ** 2 * p1[1]
    zs = (1 - ts) ** 2 * p0[2] + 2 * (1 - ts) * ts * control[2] + ts ** 2 * p1[2]
    return xs, ys, zs


def rodrigues_rotate(v, axis, theta):
    axis = axis / np.linalg.norm(axis)
    return (
        v * math.cos(theta)
        + np.cross(axis, v) * math.sin(theta)
        + axis * np.dot(axis, v) * (1 - math.cos(theta))
    )


def get_perp(edge_dir):
    up = np.array([0.0, 0.0, 1.0])
    perp = np.cross(edge_dir, up)
    perp_len = np.linalg.norm(perp)
    if perp_len < 1e-9:
        up = np.array([0.0, 1.0, 0.0])
        perp = np.cross(edge_dir, up)
        perp_len = np.linalg.norm(perp)
    return perp / perp_len


def unpack3(c):
    if len(c) >= 3:
        return c[0], c[1], c[2]
    if len(c) == 2:
        return c[0], c[1], 0
    return c[0], 0, 0
