# from fractions import Fraction
# import matplotlib.pyplot as plt
# import numpy as np
# from matplotlib.animation import FuncAnimation, PillowWriter, FFMpegWriter
# from PIL import Image

# import hashlib
# import cv2
# from matplotlib.backends.backend_agg import FigureCanvasAgg

# from klotho.chronos.temporal_units import TemporalUnit

# def hash_fraction_to_color(fraction, bias=None):
#     # Create a unique hash for each fraction
#     fraction_hash = hashlib.md5(str(fraction).encode('utf-8')).hexdigest()
#     # Convert the hash to an integer and then to a color
#     color_int = int(fraction_hash[:6], 16)  # Use first 6 digits for RGB
#     r = (color_int >> 16) & 255
#     g = (color_int >> 8) & 255
#     b = color_int & 255
#     if bias:
#         match bias:
#             case 'r':
#                 r = 255
#                 g = g // 2
#                 b = b // 2
#             case 'b':
#                 r = r // 2
#                 g = g // 2
#                 b = 255
            
#     return (r / 255.0, g / 255.0, b / 255.0)

# def animate_temporal_unit(ut:TemporalUnit, save_mp4=False, save_png=False, file_name='proportion_animation', fps=60, bias=None):
#     proportions = [Fraction(int(f.numerator), int(f.denominator)) for f in ut.ratios]
#     durations = ut.durations
    
#     total_width = sum(float(f) for f in proportions)
    
#     unique_fractions = list(set(proportions))
#     # colors = plt.cm.rainbow(np.linspace(0, 1, len(unique_fractions)))
#     colors = [hash_fraction_to_color(fraction, bias=bias) for fraction in unique_fractions]
#     color_map = dict(zip(unique_fractions, colors))
    
#     fig, ax = plt.subplots(figsize=(18, 1))
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
#         patch = plt.Rectangle((left, 0), width, 1, facecolor=color, alpha=0.5, edgecolor='lightgrey')
#         ax.add_patch(patch)
#         patches.append(patch)
        
#         # text = ax.text(left + width/2, 0.5, str(fraction), ha='center', va='center', color='white', fontsize=4)
#         # texts.append(text)
        
#         left += width
    
#     plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
#     if save_png:
#         plt.savefig(f"{file_name}.png", dpi=fig.dpi, bbox_inches='tight')
#         print(f"PNG file saved as '{file_name}.png'")
    
#     frames = []
#     for i, duration in enumerate(durations):
#         frames.extend([i] * int(duration * fps))
    
#     def animate(frame):
#         current_block = frames[frame]
#         for i, patch in enumerate(patches):
#             if i == current_block:
#                 patch.set_alpha(1.0)
#                 # patch.set_edgecolor('white')
#                 # patch.set_linewidth(1)
#             else:
#                 patch.set_alpha(0.25)
#                 # patch.set_alpha(0.05)
#         return patches
    
#     anim = FuncAnimation(fig, animate, frames=len(frames), interval=1000/fps, blit=True)

#     if save_mp4:
#         ext = 'mp4' #'mp4' if save_mp4 else 'gif'
#         plt.tight_layout(pad=0)
#         writer = FFMpegWriter(fps=fps, codec='libx264')
#         anim.save(f"{file_name}.{ext}", writer=writer, dpi=fig.dpi)
#         # anim.save(f"{file_name}.mp4", writer=writer, dpi=fig.dpi)
#         print(f"MP4 file saved as '{file_name}.{ext}'")
    
#     if not save_mp4 and not save_png:
#         plt.tight_layout()
#         plt.show()

# def animate_temporal_units(units: list[TemporalUnit], save_mp4=False, save_png=False, file_name='proportion_animation', fps=60):
#     block_height = 0.7
#     fig, ax = plt.subplots(figsize=(24, block_height * len(units)))
#     ax.axis('off')
#     fig.patch.set_facecolor('black')
#     ax.set_facecolor('black')
    
#     total_height = len(units) * block_height
#     ax.set_ylim(0, total_height)
    
#     y_pos = 0
#     all_patches = []
#     all_frames = []
    
#     for ut in units:
#         proportions = [Fraction(int(f.numerator), int(f.denominator)) for f in ut.ratios]
#         durations = ut.durations
        
#         # Skip units with empty or zero durations
#         if not durations or sum(durations) == 0:
#             y_pos += block_height  # Move up by block_height even for skipped units to maintain consistent placement
#             continue
        
#         total_width = sum(float(f) for f in proportions)
#         unique_fractions = list(set(proportions))
#         # colors = plt.cm.rainbow(np.linspace(0, 1, len(unique_fractions)))
#         colors = [hash_fraction_to_color(fraction) for fraction in unique_fractions]
#         color_map = dict(zip(unique_fractions, colors))
        
#         patches = []
#         left = 0
#         for fraction in proportions:
#             width = float(fraction)
#             color = color_map[fraction]
#             patch = plt.Rectangle((left, y_pos), width, block_height, facecolor=color, alpha=0.5, edgecolor='lightgrey')
#             ax.add_patch(patch)
#             patches.append(patch)
#             left += width
        
#         frames = []
#         for i, duration in enumerate(durations):
#             frames.extend([i] * int(duration * fps))
        
#         all_patches.append(patches)
#         all_frames.append(frames)
#         y_pos += block_height
    
#     plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    
#     if save_png:
#         plt.savefig(f"{file_name}.png", dpi=fig.dpi, bbox_inches='tight')
#         print(f"PNG file saved as '{file_name}.png'")
    
#     def animate(frame):
#         for unit_idx, (patches, frames) in enumerate(zip(all_patches, all_frames)):
#             if not frames:
#                 continue
#             current_block = frames[frame % len(frames)]
#             for i, patch in enumerate(patches):
#                 if i == current_block:
#                     patch.set_alpha(1.0)
#                 else:
#                     patch.set_alpha(0.25)
#                     # patch.set_alpha(0.05)
#         return [patch for sublist in all_patches for patch in sublist]
    
#     total_frames = max(len(frames) for frames in all_frames if frames)
#     anim = FuncAnimation(fig, animate, frames=total_frames, interval=1000/fps, blit=True)

#     if save_mp4:
#         writer = FFMpegWriter(fps=fps, codec='libx264')
#         anim.save(f"{file_name}.mp4", writer=writer, dpi=fig.dpi)
#         print(f"MP4 file saved as '{file_name}.mp4'")
    
#     if not save_mp4 and not save_png:
#         plt.tight_layout()
#         plt.show()

# def create_gif(image_files, gif_file, duration):
#     frames = []
#     for image in image_files:
#         # Ensure each frame is separate and doesn't retain any previous frame information
#         frame = Image.open(image).convert('RGBA')
#         frames.append(frame)
    
#     # Save the frames as a GIF
#     frames[0].save(
#         gif_file, format='GIF', append_images=frames[1:],
#         save_all=True, duration=duration, loop=0
#     )

