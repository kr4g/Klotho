import numpy as np
import matplotlib.pyplot as plt


SHAPE_COLORS = ["#90EE90", "#FFD700", "#FF6B6B", "#87CEEB", "#DDA0DD", "#FFA07A"]


def _path_color_array(cmap_name, n):
    cmap = plt.cm.get_cmap(cmap_name)
    return cmap(np.linspace(0.15, 1, n))


def _rgba_to_hex(rgba):
    return "#%02x%02x%02x" % (int(rgba[0] * 255), int(rgba[1] * 255), int(rgba[2] * 255))
