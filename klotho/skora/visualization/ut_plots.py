# import cairo
# from klotho.chronos.temporal_units.temporal import TemporalUnit

# def save_temporal_unit_image(temporal_unit: TemporalUnit, filename: str, width: int = 500, height: int = 25) -> None:
#     """
#     Saves a temporal unit visualization as a PDF image.
    
#     Args:
#         temporal_unit: The TemporalUnit to visualize
#         filename: Path where to save the image (should end in .pdf)
#         width: Width in points (1/72 inch)
#         height: Height in points
#     """
#     # Colors (RGB values from 0 to 1)
#     BLACK = (0, 0, 0)
#     GRAY = (0.5, 0.5, 0.5)
#     WHITE = (1, 1, 1)
#     BORDER = 1
    
#     # Create PDF surface
#     surface = cairo.PDFSurface(filename, width, height)
#     ctx = cairo.Context(surface)
    
#     # Calculate total duration and positions
#     total_duration = sum(abs(d) for d in temporal_unit.durations)
#     current_x = 0
    
#     for duration in temporal_unit.durations:
#         # Calculate width for this segment
#         block_width = (abs(duration) / total_duration) * width
#         if block_width == 0:
#             continue
        
#         # Set fill color and draw rectangle
#         if duration < 0:
#             ctx.set_source_rgb(*GRAY)
#         else:
#             ctx.set_source_rgb(*BLACK)
        
#         ctx.rectangle(current_x, 0, block_width, height)
#         ctx.fill()
        
#         # Draw white border
#         if current_x > 0:  # Draw left border if not first segment
#             ctx.set_source_rgb(*WHITE)
#             ctx.set_line_width(BORDER)
#             ctx.move_to(current_x, 0)
#             ctx.line_to(current_x, height)
#             ctx.stroke()
        
#         current_x += block_width
    
#     # Clean up
#     surface.finish()
