import matplotlib.pyplot as plt
import numpy as np
from klotho.chronos.temporal_units.ut import TemporalUnit

def plot_temporal_units(uts: list[TemporalUnit], figsize=None):
    """Creates a timeline visualization of multiple TemporalUnits, stacked vertically.
    
    Args:
        uts: List of TemporalUnit instances to visualize
        figsize: Optional tuple of (width, height). If None, scales with number of UTs
    """
    if figsize is None:
        figsize = (12, 2 + len(uts))
        
    # Setup the figure with dark background
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor('#1C1C1C')
    ax.set_facecolor('#1C1C1C')

    # Calculate positions
    bar_height = 0.4
    spacing = 1.0  # Vertical space between UTs
    
    # Get all unique metric ratios across all UTs and create color mapping
    all_ratios = set()
    for ut in uts:
        all_ratios.update(event['metric_ratio'] for event in ut)
    unique_ratios = sorted(all_ratios)
    color_map = dict(zip(unique_ratios, plt.cm.Set3(np.linspace(0, 1, len(unique_ratios)))))
    
    # Find global time limits
    global_start = min(ut.time[0] for ut in uts)
    global_end = max(ut.time[1] for ut in uts)
    
    # Plot each UT
    for i, ut in enumerate(uts):
        bar_y = spacing * (len(uts) - 1 - i)  # Stack from top to bottom
        
        # Plot each event in the UT
        for event in ut:
            # Get color based on metric ratio
            color = color_map[event['metric_ratio']]
            
            # Draw the segment
            ax.add_patch(plt.Rectangle(
                (event['start'], bar_y),
                event['duration'],
                bar_height,
                facecolor=color,
                edgecolor='white',
                linewidth=0.5
            ))
            
            # Add metric ratio label in center of segment
            ax.text(
                event['start'] + event['duration']/2,
                bar_y + bar_height/2,
                str(event['metric_ratio']),
                ha='center',
                va='center',
                color='black',
                fontsize=8
            )
        
        # Add UT info on the right
        ax.text(
            global_end + 0.2,
            bar_y + bar_height/2,
            f"T:{ut.tempo}, B:{ut.beat}",
            va='center',
            color='white',
            fontsize=8
        )

    # Set axis limits
    ax.set_xlim(global_start - 0.1, global_end + 1.0)  # Extra space on right for UT info
    ax.set_ylim(-0.1, spacing * (len(uts)) + 0.1)

    # Configure time ruler at top
    ax.xaxis.set_ticks_position('top')
    ax.tick_params(axis='x', colors='white', which='both')
    ax.tick_params(axis='y', which='both', left=False, labelleft=False)
    ax.grid(True, axis='x', linestyle='--', alpha=0.3, color='white')

    # Add title
    ax.set_title("TemporalUnit Timeline", pad=20, color='white')

    plt.tight_layout()
    return fig, ax

def test_visualization():
    # Create several test UTs with different parameters
    ut1 = TemporalUnit(
        span=1,
        tempus='4/4',
        prolatio=(2, 1, 1),
        tempo=60,
        beat='1/4'
    )
    
    ut2 = TemporalUnit(
        span=1,
        tempus='4/4',
        prolatio=(1, 1, 1),
        tempo=60,
        beat='1/4'
    )
    
    ut3 = TemporalUnit(
        span=1,
        tempus='4/4',
        prolatio=(3, 2, 2, 1),
        tempo=60,
        beat='1/4'
    )
    
    # Plot all UTs
    fig, ax = plot_temporal_units([ut1, ut2, ut3])
    plt.show()

if __name__ == "__main__":
    test_visualization()
