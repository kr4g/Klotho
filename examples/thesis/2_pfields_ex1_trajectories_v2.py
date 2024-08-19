from klotho.topos.graphs.fields import Field
from klotho.topos.graphs.fields.algorithms import *
from klotho.topos.graphs.fields.functions import FieldFunction
from klotho.skora.visualization.field_plots import *
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple

class DynamicQuantumFieldFunction(FieldFunction):
    def __init__(self):
        super().__init__(input_dim=2, output_dim=1, output_range=(-1, 1))

    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        x, y = x[..., 0], x[..., 1]
        
        # Dynamic wave functions
        psi1 = np.sin(10*x) * np.cos(10*y) * np.exp(-(x**2 + y**2))
        psi2 = np.cos(15*x - 5*y) * np.sin(15*y - 5*x)
        psi3 = np.sin(20*x*y) * np.exp(-(x**2 + y**2) / 2)
        
        # Potential landscape
        V = 0.5 * (np.sin(5*x) * np.cos(5*y) + np.cos(7*x) * np.sin(7*y))
        
        # Vortices
        r = np.sqrt(x**2 + y**2)
        theta = np.arctan2(y, x)
        vortex = np.sin(5*theta) * (1 - np.exp(-3*r))
        
        # Quantum tunneling effect
        tunneling = 0.2 * np.exp(-((x-0.5)**2 + (y-0.5)**2) / 0.01) * np.sin(30*x + 30*y)
        
        # Combine all elements
        field = (psi1 + psi2 + psi3) * (1 + V) + vortex + tunneling
        
        # Add some non-linear interactions
        field += 0.1 * field**2 - 0.05 * field**3
        
        # Normalize and enhance contrast
        field = field / np.max(np.abs(field))
        field = np.tanh(3 * field)
        
        return field
    
class FluidDynamicsFieldFunction(FieldFunction):
    def __init__(self):
        super().__init__(input_dim=1, output_dim=1, output_range=(-1, 1))

    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        # Convert 1D input to 2D
        r = np.abs(x)
        theta = np.pi * x
        x, y = r * np.cos(theta), r * np.sin(theta)
        
        # Stream function
        psi = np.sin(3*x) * np.cos(3*y)
        
        # Vortices
        r1 = np.sqrt((x-0.5)**2 + (y-0.5)**2)
        r2 = np.sqrt((x+0.5)**2 + (y+0.5)**2)
        vortex1 = 0.5 * np.exp(-10*r1**2) * (y-0.5)
        vortex2 = -0.5 * np.exp(-10*r2**2) * (y+0.5)
        
        # Turbulence
        turbulence = 0.2 * np.sin(20*x) * np.sin(20*y)
        
        # Boundary layer effect
        boundary = 0.5 * (np.tanh(10*(y-0.9)) - np.tanh(10*(y+0.9)))
        
        # Combine all elements
        field = psi + vortex1 + vortex2 + turbulence + boundary
        
        # Add some non-linear interactions
        field += 0.1 * np.sin(10*field)
        
        # Normalize and enhance contrast
        field = field / np.max(np.abs(field))
        field = np.tanh(2 * field)
        
        return field

class BrainWaveField(FieldFunction):
    def __init__(self):
        super().__init__(input_dim=2, output_dim=1, output_range=(-1, 1))

    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        x, y = x[..., 0], x[..., 1]
        
        # Simulate different brain wave frequencies
        delta = 0.3 * np.sin(1 * x) * np.cos(1 * y)  # 0.5-4 Hz
        theta = 0.25 * np.sin(2 * x) * np.cos(2 * y)  # 4-8 Hz
        alpha = 0.2 * np.sin(5 * x) * np.cos(5 * y)  # 8-13 Hz
        beta = 0.15 * np.sin(10 * x) * np.cos(10 * y)  # 13-30 Hz
        gamma = 0.1 * np.sin(20 * x) * np.cos(20 * y)  # 30-100 Hz
        
        # Combine wave patterns
        waves = delta + theta + alpha + beta + gamma
        
        # Add spatial variation to simulate different brain regions
        regions = 0.5 * np.exp(-((x-0.5)**2 + (y-0.5)**2)/0.3) - 0.5 * np.exp(-((x+0.5)**2 + (y+0.5)**2)/0.3)
        
        # Combine waves and regions
        field = waves + 0.3 * regions
        
        # Normalize
        field = field / np.max(np.abs(field))
        
        return field

# Create the Field
res = 250
dim = 2

quantum_fluid_field_function = FieldFunction.compose(FluidDynamicsFieldFunction(), DynamicQuantumFieldFunction())

quantum_field = Field(dim, res, DynamicQuantumFieldFunction())
quantum_fluid_field = Field(dim, res, quantum_fluid_field_function)

neural_fluid_field_function = FieldFunction.compose(FluidDynamicsFieldFunction(), BrainWaveField())

brain_wave_field = Field(dim, res, BrainWaveField())
brain_wave_fluid_field = Field(dim, res, neural_fluid_field_function)

# plot_field_heatmap(quantum_field, title='Field 1')
# plot_field_heatmap(quantum_fluid_field, title='Field 1: Composed with Fluid Dynamics')
# plot_field_heatmap(brain_wave_field, title='Field 2')
# plot_field_heatmap(brain_wave_fluid_field, title='Field 2: Composed with Fluid Dynamics')

# navigation_path = find_navigation_path(quantum_fluid_field, steps=2000)
# plot_path_color_bar(navigation_path, title="Field Navigation Values")

# plot_field_heatmap(quantum_fluid_field, path=navigation_path, title='Field 1: Navigation Path')

# FIELD INTERACTION

from opensimplex import OpenSimplex

simplex = OpenSimplex(seed=42)

def weighted_aggregation(values: np.ndarray, weights: np.ndarray) -> float:
    """Aggregate values using dynamically calculated weights."""
    return np.sum(values * weights) / np.sum(weights)

def get_neighbors(field: Field, point: Tuple[float, float]) -> np.ndarray:
    """Retrieve neighbor values as a numpy array."""
    return np.array(list(field.get_neighbors(point).values()))

def calculate_weights(neighbors1: np.ndarray, neighbors2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Dynamically calculate weights based on cross-neighborhood influence."""
    weights1 = np.tanh(np.abs(neighbors1 - np.mean(neighbors2)))
    weights2 = np.tanh(np.abs(neighbors2 - np.mean(neighbors1)))
    return weights1, weights2

def structured_noise(value: float, factor: float = 0.1) -> float:
    """Introduce noise based on the value and a scaling factor."""
    return value + factor * simplex.noise2(value, factor)

def interaction_function(field1: Field, field2: Field, point: Tuple[float, float]) -> float:
    v1 = field1[point]
    v2 = field2[point]
    
    # Retrieve neighbors for both fields
    neighbors1 = get_neighbors(field1, point)
    neighbors2 = get_neighbors(field2, point)
    
    # Handle edge cases where neighbors are empty
    if len(neighbors1) == 0 or len(neighbors2) == 0:
        return 0.0
    
    # Calculate cross-influenced weights for neighbors
    weights1, weights2 = calculate_weights(neighbors1, neighbors2)
    
    # Aggregate neighbor values using dynamic weights
    aggregated1 = weighted_aggregation(neighbors1, weights2)
    aggregated2 = weighted_aggregation(neighbors2, weights1)
    
    # Apply structured noise
    noisy_agg1 = structured_noise(aggregated1)
    noisy_agg2 = structured_noise(aggregated2)
    
    # Hierarchical nonlinearity: Apply non-linear functions at multiple stages
    interaction = np.tanh(np.sin(v1 + noisy_agg2) + np.cos(v2 + noisy_agg1))
    
    # Final result combining original values, interaction, and noise
    final_result = np.tanh(interaction + v1 * v2 + noisy_agg1 * noisy_agg2)
    
    return final_result


# Create a new field by interaction
combined_field = Field.interact(quantum_fluid_field, brain_wave_fluid_field, interaction_function)

# # Use the combined field
plot_field_heatmap(combined_field, title='Interacted Quantum-Brain Field')

# navigation_path = find_navigation_path(combined_field, steps=200)
# plot_path_color_bar(navigation_path, title="Field Navigation Values")
# # plot_field_heatmap(combined_field, path=navigation_path, title='Combined Field: Navigation Path')
