from klotho.topos.graphs.fields import Field
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple

def plot_field_heatmap(field: Field, title: str = '', path: List[Tuple[Tuple[float, float], float]] = None, save_path: str = None):
    """
    Plot the field as a heatmap with an optional navigation path overlaid.
    
    :param field: The Field object to plot
    :param title: Title for the plot
    :param path: Optional list of (point, value) tuples representing the navigation path
    """
    points = np.array(list(field.nodes.keys()))
    values = np.array(list(field.nodes.values()))

    grid_shape = (field.resolution,) * field.dimensionality

    Z = values.reshape(grid_shape)

    plt.figure(figsize=(12, 10), facecolor='black')
    plt.gcf().set_facecolor('black')
    plt.gca().set_facecolor('black')

    extent = [-1, 1, -1, 1] 
    plt.imshow(Z, extent=extent, origin='lower', cmap='plasma')
    
    cbar = plt.colorbar(label='Field Value')
    cbar.ax.yaxis.label.set_color('white')
    cbar.ax.tick_params(color='white')
    
    plt.title(title, color='white', fontsize=16)
    plt.xlabel('X', color='white')
    plt.ylabel('Y', color='white')
    plt.tick_params(colors='white')

    if path:
        path_points, path_values = zip(*path)
        path_x, path_y = zip(*path_points)
        plt.plot(path_x, path_y, color='white', linewidth=2, alpha=0.7)
        plt.scatter(path_x[0], path_y[0], color='lime', s=100, label='Start')
        plt.scatter(path_x[-1], path_y[-1], color='red', s=100, label='End')
        plt.legend(loc='upper right', facecolor='black', edgecolor='white', labelcolor='white')

    if save_path:
        plt.savefig(save_path)

    plt.tight_layout()
    plt.show()
    
def plot_path_color_bar(path, title=''):
    """
    Plot the path values as a horizontal color bar.
    
    :param path: List of (point, value) tuples representing the navigation path
    :param title: Title for the plot
    """
    path_values = [value for _, value in path]
    values = np.array(path_values).reshape(1, -1)
    
    plt.figure(figsize=(12, 4), facecolor='black')
    plt.gcf().set_facecolor('black')
    plt.gca().set_facecolor('black')
    
    img = plt.imshow(values, aspect='auto', cmap='plasma', extent=[0, len(path_values), 0, 1])
    
    plt.title(f"{title}", color='white', fontsize=16)
    plt.xlabel('Navigation Steps', color='white')
    plt.yticks([])  # Remove y-axis ticks
    plt.tick_params(colors='white')
    
    # cbar = plt.colorbar(img, orientation='horizontal', pad=0.2)
    # cbar.ax.xaxis.label.set_color('white')
    # cbar.ax.tick_params(color='white')
    # cbar.set_label('Field Value', color='white')
    
    plt.tight_layout()
    plt.show()