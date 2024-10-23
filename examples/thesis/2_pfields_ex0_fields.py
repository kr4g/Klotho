from klotho.topos.graphs.fields import *
from klotho.topos.graphs.fields.algorithms import *
from klotho.topos.graphs.fields.functions import FieldFunction
from klotho.skora.visualization.field_plots import *
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple
import os


class DynamicQuantumFieldFunction(FieldFunction):
    def __init__(self):
        super().__init__(input_dim=2, output_dim=1, output_range=(-1, 1))

    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        x, y = x[..., 0], x[..., 1]
        
        psi1 = np.sin(10*x) * np.cos(10*y) * np.exp(-(x**2 + y**2))
        psi2 = np.cos(15*x - 5*y) * np.sin(15*y - 5*x)
        psi3 = np.sin(20*x*y) * np.exp(-(x**2 + y**2) / 2)
        
        V = 0.5 * (np.sin(5*x) * np.cos(5*y) + np.cos(7*x) * np.sin(7*y))
        
        r = np.sqrt(x**2 + y**2)
        theta = np.arctan2(y, x)
        vortex = np.sin(5*theta) * (1 - np.exp(-3*r))
        
        tunneling = 0.2 * np.exp(-((x-0.5)**2 + (y-0.5)**2) / 0.01) * np.sin(30*x + 30*y)
        
        field = (psi1 + psi2 + psi3) * (1 + V) + vortex + tunneling
        
        field += 0.1 * field**2 - 0.05 * field**3
        
        field = field / np.max(np.abs(field))
        field = np.tanh(3 * field)
        
        return field
    
class FluidDynamicsFieldFunction(FieldFunction):
    def __init__(self):
        super().__init__(input_dim=1, output_dim=1, output_range=(-1, 1))

    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        r = np.abs(x)
        theta = np.pi * x
        x, y = r * np.cos(theta), r * np.sin(theta)
        
        psi = np.sin(3*x) * np.cos(3*y)
        
        r1 = np.sqrt((x-0.5)**2 + (y-0.5)**2)
        r2 = np.sqrt((x+0.5)**2 + (y+0.5)**2)
        vortex1 = 0.5 * np.exp(-10*r1**2) * (y-0.5)
        vortex2 = -0.5 * np.exp(-10*r2**2) * (y+0.5)
        
        turbulence = 0.2 * np.sin(20*x) * np.sin(20*y)
        
        boundary = 0.5 * (np.tanh(10*(y-0.9)) - np.tanh(10*(y+0.9)))
        
        field = psi + vortex1 + vortex2 + turbulence + boundary
        
        field += 0.1 * np.sin(10*field)
        
        field = field / np.max(np.abs(field))
        field = np.tanh(2 * field)
        
        return field

class BrainWaveField(FieldFunction):
    def __init__(self):
        super().__init__(input_dim=2, output_dim=1, output_range=(-1, 1))

    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        x, y = x[..., 0], x[..., 1]
        
        delta = 0.3 * np.sin(1 * x) * np.cos(1 * y)  # 0.5-4 Hz
        theta = 0.25 * np.sin(2 * x) * np.cos(2 * y)  # 4-8 Hz
        alpha = 0.2 * np.sin(5 * x) * np.cos(5 * y)  # 8-13 Hz
        beta = 0.15 * np.sin(10 * x) * np.cos(10 * y)  # 13-30 Hz
        gamma = 0.1 * np.sin(20 * x) * np.cos(20 * y)  # 30-100 Hz
        
        waves = delta + theta + alpha + beta + gamma
        
        regions = 0.5 * np.exp(-((x-0.5)**2 + (y-0.5)**2)/0.3) - 0.5 * np.exp(-((x+0.5)**2 + (y+0.5)**2)/0.3)
        
        field = waves + 0.3 * regions
        
        field = field / np.max(np.abs(field))
        
        return field

class WeatherPatternFieldFunction(FieldFunction):
    def __init__(self):
        super().__init__(input_dim=2, output_dim=1, output_range=(-1, 1))

    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        x, y = x[..., 0], x[..., 1]
        
        pressure = 0.5 * (np.sin(3*x + 0.1*y) * np.cos(3*y + 0.1*x) + np.cos(2*x - 0.2*y) * np.sin(2*y - 0.2*x))
        
        temperature = 0.3 * (np.tanh(y) + np.sin(5*x) + 0.2 * np.cos(7*x*y))
        
        humidity = 0.2 * np.sin(7*x*y) * np.exp(-(x**2 + y**2) / 2) + 0.1 * np.cos(10*x - 5*y)
        
        wind_x = 0.4 * np.sin(4*y + 0.3*x) + 0.2 * np.cos(6*x - 0.3*y)
        wind_y = 0.4 * np.cos(4*x - 0.3*y) + 0.2 * np.sin(6*y + 0.3*x)
        wind = np.sqrt(wind_x**2 + wind_y**2)
        
        field = pressure + temperature + humidity + wind
        
        field += 0.1 * field**2 - 0.05 * field**3 + 0.15 * np.sin(15*x*y)
        
        field = field / np.max(np.abs(field))
        field = np.tanh(2.5 * field)
        
        return field

class GravitationalFieldFunction(FieldFunction):
    def __init__(self):
        super().__init__(input_dim=2, output_dim=1, output_range=(-1, 1))

    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        x, y = x[..., 0], x[..., 1]
        
        sources = [
            (0.3, 0.3, 0.8),
            (-0.4, -0.2, 0.6),
            (0.5, -0.5, 0.7),
            (-0.6, 0.4, 0.5),
            (0.1, -0.7, 0.4),
            (-0.2, 0.6, 0.3)
        ]
        
        field = np.zeros_like(x)
        for sx, sy, mass in sources:
            r = np.sqrt((x - sx)**2 + (y - sy)**2)
            field += mass / (r + 0.2)**1.5
        
        field += 0.1 * np.sin(8*x) * np.cos(8*y) * np.exp(-(x**2 + y**2)/2)
        
        field += 0.05 * np.sin(15*x - 15*y) * np.cos(15*y + 15*x)
        
        field = field / np.max(np.abs(field))
        
        field = np.tanh(field)
        
        return field

class SpaceTimeDistortionFieldFunction(FieldFunction):
    def __init__(self):
        super().__init__(input_dim=1, output_dim=1, output_range=(-1, 1))
        self.time = 0 

    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        r = np.abs(x)
        theta = 2 * np.pi * x  
        
        phase_shift = 0.2 * self.time
        
        base_pattern = (
            0.3 * np.sin(3 * theta + 2 * r + phase_shift) +
            0.2 * np.cos(5 * theta - 3 * r - phase_shift) +
            0.15 * np.sin(7 * theta + 4 * r + 2 * phase_shift)
        )
        
        radial_variation = 0.2 * (1 - r) * np.cos(4 * np.pi * r + phase_shift)
        
        field = base_pattern + radial_variation
        
        distortions = 0.1 * np.exp(-((r - 0.3)**2 + (theta - np.pi*np.sin(0.1*self.time))**2) / 0.1)
        field += distortions
        
        quantum_fluctuations = 0.02 * np.random.randn(*field.shape) * (1 - r)  # Stronger near center
        field += quantum_fluctuations
        
        field = field / np.max(np.abs(field))
        
        field = np.tanh(1.2 * field)
        
        self.time += 0.03
        
        return field

class AtmosphericCurrentsFieldFunction(FieldFunction):
    def __init__(self):
        super().__init__(input_dim=1, output_dim=1, output_range=(-1, 1))

    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        r = np.abs(x)
        theta = np.pi * x
        
        jet_stream = 0.5 * np.sin(3*theta + 0.2*r) * (1 - np.exp(-2*r))
        
        hadley_cells = 0.3 * np.sin(2*theta - 0.1*r) * np.exp(-r**2) + 0.2 * np.cos(3*theta + 0.1*r) * (1 - np.exp(-1.5*r))
        
        rossby_waves = 0.2 * np.cos(5*theta + 0.3*r) * np.sin(np.pi*r) + 0.15 * np.sin(7*theta - 0.2*r) * np.cos(np.pi*r/2)
        
        field = jet_stream + hadley_cells + rossby_waves
        
        turbulence = 0.1 * np.sin(20*x) + 0.05 * np.cos(25*x)
        field += turbulence + 0.1 * field**2 - 0.05 * field**3
        
        field = field / np.max(np.abs(field))
        field = np.tanh(2.5 * field)
        
        return field


res = 100
dim = 2

# quantum_field = Field(dim, res, DynamicQuantumFieldFunction())
quantum_fluid_field = Field(dim, res, FieldFunction.compose(FluidDynamicsFieldFunction(), DynamicQuantumFieldFunction()))
# save_field(quantum_fluid_field, 'examples/thesis/quantum_fluid_field.pkl')

# brain_wave_field = Field(dim, res, BrainWaveField())
brain_wave_fluid_field = Field(dim, res, FieldFunction.compose(FluidDynamicsFieldFunction(), BrainWaveField()))
# save_field(brain_wave_fluid_field, 'examples/thesis/brain_wave_fluid_field.pkl')

# weather_field = Field(dim, res, WeatherPatternFieldFunction())
# weather_currents_field = Field(dim, res, FieldFunction.compose(AtmosphericCurrentsFieldFunction(), WeatherPatternFieldFunction()))

# gravitational_field = Field(dim, res, GravitationalFieldFunction())
# gravitational_distortion_field = Field(dim, res, FieldFunction.compose(AtmosphericCurrentsFieldFunction(), SpaceTimeDistortionFieldFunction(), GravitationalFieldFunction()))
gravitational_distortion_field = Field(dim, res, FieldFunction.compose(SpaceTimeDistortionFieldFunction(), GravitationalFieldFunction()))
# save_field(gravitational_distortion_field, 'examples/thesis/gravitational_distortion_field.pkl')

# plot_field_heatmap(quantum_field, title='Field A')
# plot_field_heatmap(quantum_fluid_field, title='Field A', save_path='examples/thesis/field_A.png')
# plot_field_heatmap(brain_wave_field, title='Field B')
# plot_field_heatmap(brain_wave_fluid_field, title='Field B', save_path='examples/thesis/field_B.png')
# plot_field_heatmap(weather_field, title='Field C')
# plot_field_heatmap(weather_currents_field, title='Field C')
# plot_field_heatmap(gravitational_field, title='Field C')
# plot_field_heatmap(gravitational_distortion_field, title='Field C', save_path='examples/thesis/field_C.png')

for node in quantum_fluid_field.nodes:
    if quantum_fluid_field[node] > 0: # NOTHING!!!!!
        print(node, quantum_fluid_field[node])



# # FIELD INTERACTION

# from opensimplex import OpenSimplex


# def get_neighbors_average_with_noise(field: Field, point: Tuple[float, float], seed: int = 42) -> Tuple[float, float]:
#     simplex = OpenSimplex(seed=seed)
#     neighbors = list(field.get_neighbors(point).items())
#     if not neighbors:
#         return 0.0, 0.0  
    
#     neighbor_values = [value for _, value in neighbors]
#     avg_value = np.mean(neighbor_values)
    
#     noise = simplex.noise2(point[0], point[1])
    
#     return avg_value, noise

# def interaction_function(field1: Field, field2: Field, point: Tuple[float, float]) -> float:
#     v1 = field1[point]
#     v2 = field2[point]
    
#     avg1, noise1 = get_neighbors_average_with_noise(field1, point, seed=42)
#     avg2, noise2 = get_neighbors_average_with_noise(field2, point, seed=42)
    
#     combined_value = np.tanh((v1 * avg2 + noise2) + (v2 * avg1 + noise1))
    
#     final_result = (0.5 * np.sin(2 * np.pi * combined_value) + 0.5)
    
#     return final_result

# from klotho.topos.sets import CombinationSet as CS

# aliases = {
#     'A': quantum_fluid_field,
#     'B': brain_wave_fluid_field,
#     # 'C': weather_currents_field,
#     'C': gravitational_distortion_field
# }

# field_cs = CS(aliases.keys(), 2)
# for combo in field_cs.combos:
#     simplex = OpenSimplex(seed=hash(combo))
#     combined_field = Field.interact(aliases[combo[0]], aliases[combo[1]], interaction_function)
#     # save_field(combined_field, f'examples/thesis/field_{combo[0]}_{combo[1]}_interaction.pkl')
#     # plot_field_heatmap(combined_field, title=f'Field {combo[0]} and Field {combo[1]} Interaction', save_path=f'examples/thesis/field_{combo[0]}_{combo[1]}_interaction.png')
#     # plot_field_heatmap(combined_field, title=f'Field {combo[0]} and Field {combo[1]} Interaction')
