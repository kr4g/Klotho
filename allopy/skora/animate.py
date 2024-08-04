from fractions import Fraction
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter

import cv2
from matplotlib.backends.backend_agg import FigureCanvasAgg

from allopy.chronos.temporal_units import TemporalUnit

# def animate_proportions(proportions, durations):
#     if len(proportions) != len(durations):
#         raise ValueError("The number of proportions must match the number of durations")

#     # Calculate total width and time
#     total_width = sum(float(f) for f in proportions)
#     total_time = sum(durations)
    
#     # Assign unique colors to unique fractions
#     unique_fractions = list(set(proportions))
#     colors = plt.cm.rainbow(np.linspace(0, 1, len(unique_fractions)))
#     color_map = dict(zip(unique_fractions, colors))
    
#     # Create the plot
#     fig, ax = plt.subplots(figsize=(12, 2))
#     ax.set_xlim(0, total_width)
#     ax.set_ylim(0, 1)
#     ax.axis('off')
    
#     # Set background color to black
#     fig.patch.set_facecolor('black')
#     ax.set_facecolor('black')
    
#     # Create patches and texts
#     patches = []
#     texts = []
#     left = 0
#     for fraction in proportions:
#         width = float(fraction)
#         color = color_map[fraction]
#         patch = plt.Rectangle((left, 0), width, 1, facecolor=color, alpha=0.5)
#         ax.add_patch(patch)
#         patches.append(patch)
        
#         text = ax.text(left + width/2, 0.5, str(fraction), ha='center', va='center', color='white')
#         texts.append(text)
        
#         left += width
    
#     # Create a list of frames for each millisecond
#     frames = []
#     for i, duration in enumerate(durations):
#         frames.extend([i] * int(duration * 1000))  # Convert seconds to milliseconds
    
#     def animate(frame):
#         current_block = frames[frame]
#         for i, patch in enumerate(patches):
#             if i == current_block:
#                 patch.set_alpha(1.0)  # Make current block fully opaque
#             else:
#                 patch.set_alpha(0.5)  # Set others to half opacity
#         return patches
    
#     anim = FuncAnimation(fig, animate, frames=len(frames), interval=1, blit=True)
    
#     plt.tight_layout()
#     plt.show()

# def animate_proportions(proportions, durations):
#     if len(proportions) != len(durations):
#         raise ValueError("The number of proportions must match the number of durations")
    
#     total_width = sum(float(f) for f in proportions)
#     total_time = sum(durations)
    
#     unique_fractions = list(set(proportions))
#     colors = plt.cm.rainbow(np.linspace(0, 1, len(unique_fractions)))
#     color_map = dict(zip(unique_fractions, colors))
    
#     fig, ax = plt.subplots(figsize=(12, 2))
#     ax.set_xlim(0, total_width)
#     ax.set_ylim(0, 1)
#     ax.axis('off')
    
#     fig.patch.set_facecolor('black')
#     ax.set_facecolor('black')
    
#     patches = []
#     texts = []
#     left = 0
#     for fraction in proportions:
#         width = float(fraction)
#         color = color_map[fraction]
#         patch = plt.Rectangle((left, 0), width, 1, facecolor=color, alpha=0.5)
#         ax.add_patch(patch)
#         patches.append(patch)
        
#         text = ax.text(left + width/2, 0.5, str(fraction), ha='center', va='center', color='white')
#         texts.append(text)
        
#         left += width
    
#     frames = []
#     for i, duration in enumerate(durations):
#         frames.extend([i] * int(duration * 1000))  # Convert seconds to milliseconds
    
#     # Set up video writer
#     fps = 1000
#     fourcc = cv2.VideoWriter_fourcc(*'mp4v')
#     video = cv2.VideoWriter('proportion_animation.mp4', fourcc, fps, (int(fig.get_figwidth() * fig.dpi), int(fig.get_figheight() * fig.dpi)))
    
#     canvas = FigureCanvasAgg(fig)
    
#     for frame in frames:
#         for i, patch in enumerate(patches):
#             if i == frame:
#                 patch.set_alpha(1.0)
#             else:
#                 patch.set_alpha(0.5)
        
#         canvas.draw()
#         img = np.frombuffer(canvas.tostring_rgb(), dtype='uint8').reshape(int(fig.get_figheight() * fig.dpi), int(fig.get_figwidth() * fig.dpi), 3)
#         img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
#         video.write(img)
    
#     video.release()
#     plt.close(fig)

def animate_temporal_unit(ut:TemporalUnit, save_mp4=False):
    proportions = [Fraction(int(f.numerator), int(f.denominator)) for f in ut.ratios]
    durations = ut.durations
    
    total_width = sum(float(f) for f in proportions)
    
    unique_fractions = list(set(proportions))
    colors = plt.cm.rainbow(np.linspace(0, 1, len(unique_fractions)))
    color_map = dict(zip(unique_fractions, colors))
    
    fig, ax = plt.subplots(figsize=(18, 1))
    ax.set_xlim(0, total_width)
    ax.set_ylim(0, 1)
    ax.axis('off')
    
    fig.patch.set_facecolor('black')
    ax.set_facecolor('black')
    
    patches = []
    texts = []
    left = 0
    for fraction in proportions:
        width = float(fraction)
        color = color_map[fraction]
        patch = plt.Rectangle((left, 0), width, 1, facecolor=color, alpha=0.5)
        ax.add_patch(patch)
        patches.append(patch)
        
        text = ax.text(left + width/2, 0.5, str(fraction), ha='center', va='center', color='white')
        texts.append(text)
        
        left += width
    
    frames = []
    for i, duration in enumerate(durations):
        frames.extend([i] * int(duration * 1000))  # Convert seconds to milliseconds
    
    def animate(frame):
        current_block = frames[frame]
        for i, patch in enumerate(patches):
            if i == current_block:
                patch.set_alpha(1.0)  # Make current block fully opaque
            else:
                patch.set_alpha(0.5)  # Set others to half opacity
        return patches
    
    anim = FuncAnimation(fig, animate, frames=len(frames), interval=1, blit=True)
    
    # if save_mp4:
    #     # Set up video writer
    #     fps = 1000
    #     fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    #     video = cv2.VideoWriter('proportion_animation.mp4', fourcc, fps, (int(fig.get_figwidth() * fig.dpi), int(fig.get_figheight() * fig.dpi)))
        
    #     canvas = FigureCanvasAgg(fig)
        
    #     for frame in range(len(frames)):
    #         animate(frame)
    #         canvas.draw()
    #         img = np.frombuffer(canvas.tostring_rgb(), dtype='uint8').reshape(int(fig.get_figheight() * fig.dpi), int(fig.get_figwidth() * fig.dpi), 3)
    #         img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    #         video.write(img)
        
    #     video.release()
    #     print("MP4 file saved as 'proportion_animation.mp4'")
    
    plt.tight_layout()
    plt.show()
