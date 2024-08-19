from klotho.topos.graphs.fields import Field
from klotho.topos.graphs.fields.functions import FieldFunction
import numpy as np
import matplotlib.pyplot as plt

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

# Create the FluidDynamicsFieldFunction
fluid_field_function = FluidDynamicsFieldFunction()

# Create the FieldFunction
quantum_field_function = DynamicQuantumFieldFunction()

quantum_fluid_field_function = FieldFunction.compose(fluid_field_function, quantum_field_function)

# Create the Field
n_points = 50
x = np.linspace(-1, 1, n_points)
y = np.linspace(-1, 1, n_points)
X, Y = np.meshgrid(x, y)
points = np.stack((X.flatten(), Y.flatten()), axis=-1)

values = quantum_fluid_field_function(points)

space_points = {tuple(point): {'field_value': value} for point, value in zip(points, values)}

# space_points = {(float(x), float(y)): {} for x, y in zip(X.flatten(), Y.flatten())}

quantum_field = Field(space_points, quantum_field_function)
quantum_fluid_field = Field(space_points, quantum_fluid_field_function)

# THIS DOESNT WORK
for point in points:
    print(point, quantum_fluid_field[tuple(point)]) # always -0.9640275800758169

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

# Create the brain wave field
neural_fluid_field_function = FieldFunction.compose(fluid_field_function, BrainWaveField())
brain_wave_field = Field(space_points, BrainWaveField())
brain_wave_fluid_field = Field(space_points, neural_fluid_field_function)

def plot_1d_fluid_function(fluid_field_function, resolution: int = 400, title=''):
    # Generate input values
    x = np.linspace(-1, 1, resolution)
    
    # Reshape x to be 2D as required by the function
    X = x.reshape(-1, 1)
    
    # Calculate field values
    field_values = fluid_field_function(X)
    
    # Create the plot
    plt.figure(figsize=(12, 4), facecolor='black')
    plt.gcf().set_facecolor('black')
    plt.gca().set_facecolor('black')
    
    # Plot the horizontal bar
    plt.imshow(field_values.reshape(1, -1), aspect='auto', cmap='plasma', extent=[-1, 1, 0, 1])
    
    # Customize the plot
    plt.title(title, color='white', fontsize=16)
    plt.xlabel('X', color='white')
    plt.yticks([])  # Remove y-axis ticks
    plt.tick_params(colors='white')
    
    # Add colorbar
    cbar = plt.colorbar(orientation='horizontal', pad=0.2)
    cbar.ax.xaxis.label.set_color('white')
    cbar.ax.tick_params(color='white')
    cbar.set_label('Field Value', color='white')
    
    plt.tight_layout()
    plt.show()

# Function to plot the field as a 2D heatmap
def plot_field_heatmap(field: Field, x_range: tuple, y_range: tuple, resolution: int = 400, title=''):
    x = np.linspace(x_range[0], x_range[1], resolution)
    y = np.linspace(y_range[0], y_range[1], resolution)
    X, Y = np.meshgrid(x, y)
    points = np.stack((X.flatten(), Y.flatten()), axis=-1)
    
    Z = field.field_function(points).reshape(X.shape)
    
    plt.figure(figsize=(12, 10), facecolor='black')
    plt.gcf().set_facecolor('black')
    plt.gca().set_facecolor('black')
    
    plt.imshow(Z, extent=[x_range[0], x_range[1], y_range[0], y_range[1]], 
               origin='lower', cmap='plasma')
    cbar = plt.colorbar(label='Field Value')
    cbar.ax.yaxis.label.set_color('white')
    cbar.ax.tick_params(color='white')
    plt.title(title, color='white', fontsize=16)
    plt.xlabel('X', color='white')
    plt.ylabel('Y', color='white')
    plt.tick_params(colors='white')
    
    plt.tight_layout()
    plt.show()

# Plot the field
# plot_field_heatmap(quantum_field, (-1, 1), (-1, 1), title='')
# plot_field_heatmap(quantum_fluid_field, (-1, 1), (-1, 1), title='')
# plot_field_heatmap(brain_wave_field, (-1, 1), (-1, 1), title='')
# plot_field_heatmap(brain_wave_fluid_field, (-1, 1), (-1, 1), title='')