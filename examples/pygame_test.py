import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))


import pygame
import sys
from fractions import Fraction
import colorsys
import cv2
import numpy as np
from typing import List

from allopy.chronos.temporal_units import TemporalUnit as UT

def fraction_to_tuple(frac):
    return (int(frac.numerator), int(frac.denominator))

def generate_distinct_colors(n):
    hue_step = 0.618033988749895  # Golden ratio conjugate
    saturation_range = (0.4, 1.0)
    value_range = (0.7, 1.0)

    colors = []
    hue = 0
    for i in range(n):
        hue = (hue + hue_step) % 1
        saturation = saturation_range[0] + (i / (n-1)) * (saturation_range[1] - saturation_range[0])
        value = value_range[0] + ((i + 0.5) / n) * (value_range[1] - value_range[0])
        
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        colors.append((int(r * 255), int(g * 255), int(b * 255)))

    return colors

def create_color_map(proportions):
    unique_fractions = list(set(fraction_to_tuple(f) for f in proportions))
    colors = generate_distinct_colors(len(unique_fractions))
    return dict(zip(unique_fractions, colors))

def animate_proportions(uts: List[UT], save_video=False):
    pygame.init()

    width = 1200
    height = 100 * len(uts)

    all_rects = []
    all_frames = []
    border_size = 1

    # Generate a global color map for all UTs
    all_proportions = [fraction for ut in uts for fraction in ut.ratios]
    global_color_map = create_color_map(all_proportions)

    for ut_index, ut in enumerate(uts):
        proportions, durations = ut.ratios, ut.durations
        total_proportion = sum(float(f) for f in proportions)

        rects = []
        left = 0
        ut_height = 100
        ut_top = ut_index * ut_height

        for fraction in proportions:
            rect_width = int((float(fraction) / total_proportion) * width)
            color = global_color_map[fraction_to_tuple(fraction)]
            inner_rect = pygame.Rect(left + border_size, ut_top + border_size, 
                                     rect_width - 2*border_size, ut_height - 2*border_size)
            rects.append((pygame.Rect(left, ut_top, rect_width, ut_height), inner_rect, color))
            left += rect_width

        last_outer_rect, last_inner_rect, last_color = rects[-1]
        last_outer_rect.width = width - last_outer_rect.left
        last_inner_rect.width = last_outer_rect.width - 2*border_size
        rects[-1] = (last_outer_rect, last_inner_rect, last_color)

        all_rects.append(rects)
        all_frames.append(durations)

    if save_video:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video = cv2.VideoWriter('stacked_proportion_animation.mp4', fourcc, 1000, (int(width), int(height)))
        surface = pygame.Surface((width, height))
    else:
        screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Stacked Proportion Animation")

    alpha_surface = pygame.Surface((width, height), pygame.SRCALPHA)

    # Calculate total animation time
    total_time = max(sum(ut.durations) for ut in uts)
    
    running = True
    clock = pygame.time.Clock()
    elapsed_time = 0

    while running and (elapsed_time < total_time or not save_video):
        if not save_video:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

        alpha_surface.fill((0, 0, 0, 0))

        for ut_index, (rects, durations) in enumerate(zip(all_rects, all_frames)):
            ut_elapsed_time = elapsed_time % sum(durations)
            current_block = 0
            block_start_time = 0
            for i, duration in enumerate(durations):
                if ut_elapsed_time < block_start_time + duration:
                    current_block = i
                    break
                block_start_time += duration

            for i, (outer_rect, inner_rect, color) in enumerate(rects):
                if i == current_block:
                    pygame.draw.rect(alpha_surface, (*color, 255), inner_rect)
                else:
                    pygame.draw.rect(alpha_surface, (*color, 64), inner_rect)

        if save_video:
            surface.fill((0, 0, 0))
            surface.blit(alpha_surface, (0, 0))
            pygame_surface = surface
        else:
            screen.fill((0, 0, 0))
            screen.blit(alpha_surface, (0, 0))
            pygame.display.flip()
            pygame_surface = pygame.display.get_surface()

        if save_video:
            frame_data = pygame.image.tostring(pygame_surface, 'RGB')
            frame_array = np.frombuffer(frame_data, dtype=np.uint8).reshape((height, width, 3))
            video.write(cv2.cvtColor(frame_array, cv2.COLOR_RGB2BGR))

        elapsed_time += 0.001  # Increment by 1ms
        clock.tick(1000)  # 1000 FPS

    if save_video:
        video.release()
        print("Video saved as 'stacked_proportion_animation.mp4'")
    
    pygame.quit()
    if not save_video:
        sys.exit()


from allopy.chronos.rhythm_trees.rt_algorithms import rhythm_pair as rp
from allopy.topos import autoref
# ut = UT(tempus='4/4', duration=1, prolatio=autoref((3,5,7,11)), tempo=28, beat='1/8')
tempus='4/4'
beat = '1/4'
bpm = 60
utseq = (
        UT(tempus=tempus, prolatio=(1,1,1,1), tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio=(3,1,1,1), tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio=(3,1,2,1), tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio=(3,5,2,1), tempo=bpm, beat=beat),)

# print(ut.duration)
animate_proportions(utseq, True)