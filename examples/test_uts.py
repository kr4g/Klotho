import matplotlib.pyplot as plt
import numpy as np
from klotho.chronos.temporal_units.ut import TemporalUnit
from klotho.topos.graphs.trees.algorithms import factor_children,rotate_children

def plot_temporal_units(uts: list[TemporalUnit], figsize=(12, 8)):
    """Creates a timeline visualization of multiple TemporalUnits, stacked vertically.
    
    Args:
        uts: List of TemporalUnit instances to visualize
        figsize: Figure size (width, height). Default maintains readable size with scrolling
    """
    # Calculate the required width based on the actual time span
    global_start = min(ut.time[0] for ut in uts)
    global_end = max(ut.time[1] for ut in uts)
    time_span = global_end - global_start
    
    # Create figure with fixed display size and minimal margins
    plt.style.use('dark_background')
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111)
    
    # Adjust the margins to maximize plotting area
    fig.tight_layout()
    plt.subplots_adjust(left=0.02, right=0.98, top=0.9, bottom=0.02)
    
    fig.patch.set_facecolor('#1C1C1C')
    ax.set_facecolor('#1C1C1C')

    # Calculate positions
    bar_height = 0.1
    spacing = 0.15
    
    # Get all unique metric ratios and create pastel color mapping
    all_ratios = set()
    for ut in uts:
        all_ratios.update(event['metric_ratio'] for event in ut)
    unique_ratios = sorted(all_ratios)
    
    # Create lighter, more pastel colors
    n_colors = len(unique_ratios)
    colors = []
    base_colors = plt.cm.Pastel1(np.linspace(0, 1, 9))
    
    for i in range(n_colors):
        if i < 9:
            color = base_colors[i]
        else:
            hue = (i * 0.618033988749895) % 1
            color = plt.cm.hsv(hue)
            color = np.array(color) * 0.6 + 0.4
            color[3] = 1.0
        colors.append(color)
    
    color_map = dict(zip(unique_ratios, colors))
    
    # Plot each UT
    for i, ut in enumerate(uts):
        bar_y = spacing * (len(uts) - 1 - i)
        
        for event in ut:
            color = color_map[event['metric_ratio']]
            
            ax.add_patch(plt.Rectangle(
                (event['start'], bar_y),
                event['duration'],
                bar_height,
                facecolor=color,
                edgecolor='white',
                linewidth=0.75
            ))
            
            ax.text(
                event['start'] + event['duration']/2,
                bar_y + bar_height/2,
                str(event['metric_ratio']),
                ha='center',
                va='center',
                color='black',
                fontsize=8
            )
        
        ax.text(
            event['start'] + event['duration'] + 0.2,
            bar_y + bar_height/2,
            f"T:{ut.tempo}, B:{ut.beat}",
            va='center',
            color='white',
            fontsize=8
        )

    # Configure axes for scrolling
    window_size = 8.0  # Show 8 seconds at a time
    
    # Set the full data range that can be scrolled
    ax.set_xbound(global_start - 0.5, global_end + 0.5)
    
    # Set the initial view window to first 8 seconds of the actual data
    ax.set_xlim(0, window_size)
    ax.set_ylim(-0.1, spacing * (len(uts)) + 0.1)

    # Configure time ruler at top
    ax.xaxis.set_ticks_position('top')
    ax.tick_params(axis='x', colors='white', which='both')
    ax.tick_params(axis='y', which='both', left=False, labelleft=False)
    ax.grid(True, axis='x', linestyle='--', alpha=0.3, color='white')

    # Add title
    ax.set_title("TemporalUnit Timeline", pad=20, color='white')
    
    # Make sure the plot doesn't auto-adjust
    plt.autoscale(enable=False)
    
    return fig, ax

def test_visualization():
    # Create several test UTs with different parameters
    S = ((2, (5, (4, (5, 3, 2)))), (3, (5, 4, 3, 2)), 3)
    
    uts = [TemporalUnit(
        span=2,
        tempus='4/4',
        prolatio=rotate_children(S, i),
        tempo=60,
        beat='1/4'
    ) for i in range(len(factor_children(S)))]
    
    # Plot all UTs
    fig, ax = plot_temporal_units(uts)
    plt.show()

if __name__ == "__main__":
    test_visualization()
