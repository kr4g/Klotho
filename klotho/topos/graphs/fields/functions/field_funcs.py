from abc import ABC, abstractmethod
from typing import Any, Dict, Union, Tuple
import numpy as np

class FieldFunction(ABC):
    '''Base class for field functions with variable input dimensionality and output range.'''

    def __init__(self, input_dim: int = 1, output_dim: int = 1, 
                 output_range: Tuple[float, float] = (float('-inf'), float('inf')),
                 parameters: Dict[str, Any] = None):
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.output_range = output_range
        self.parameters = parameters or {}

    @abstractmethod
    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        '''Raw function to be implemented by subclasses.'''
        pass

    def __call__(self, x: Union[float, list, np.ndarray]) -> Union[float, np.ndarray]:
        '''Apply the function to input x, ensuring correct dimensionality and range.'''
        x = np.atleast_1d(x)
        if x.shape[-1] != self.input_dim:
            raise ValueError(f"Input dimensionality {x.shape[-1]} does not match expected {self.input_dim}")
        
        result = self._raw_function(x)
        
        if self.output_dim > 1:
            result = result.reshape(-1, self.output_dim)
        
        return np.clip(result, self.output_range[0], self.output_range[1])

    @staticmethod
    def compose(*functions: 'FieldFunction') -> 'FieldFunction':
        '''Compose multiple FieldFunctions.'''
        if len(functions) < 2:
            raise ValueError("At least two functions are required for composition.")
        
        for i in range(len(functions) - 1):
            if functions[i].input_dim != functions[i+1].output_dim:
                raise ValueError(f"Output dimension of function {i+1} must match input dimension of function {i}.")
        
        class ComposedFunction(FieldFunction):
            def __init__(self, *funcs):
                super().__init__(funcs[-1].input_dim, funcs[0].output_dim, funcs[0].output_range)
                self.functions = funcs
            
            def _raw_function(self, x):
                for func in reversed(self.functions):
                    x = func._raw_function(x)
                return x
        
        return ComposedFunction(*functions)

    def set_parameters(self, **kwargs):
        '''Set parameters of the function.'''
        self.parameters.update(kwargs)

# -------------------------------------------

class Identity(FieldFunction):
    '''Identity function.'''
    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        return x

class Sigmoid(FieldFunction):
    '''Sigmoid function.'''
    def __init__(self, input_dim: int = 1):
        super().__init__(input_dim, 1, (0, 1))
    
    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        return 1 / (1 + np.exp(-x))

class Gaussian(FieldFunction):
    '''Gaussian function.'''
    def __init__(self, input_dim: int = 1, mu: float = 0, sigma: float = 1):
        super().__init__(input_dim, 1, (0, 1), {'mu': mu, 'sigma': sigma})
    
    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        return np.exp(-((x - self.parameters['mu']) ** 2) / (2 * self.parameters['sigma'] ** 2))

class Polynomial(FieldFunction):
    '''Polynomial function.'''
    def __init__(self, coefficients: list, input_dim: int = 1):
        super().__init__(input_dim, 1, parameters={'coefficients': coefficients})
    
    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        return sum(c * x**i for i, c in enumerate(self.parameters['coefficients']))
