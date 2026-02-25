"""
Field function abstractions for parameter field evaluation.

This module provides ``FieldFunction``, an abstract base class for functions
that are evaluated over parameter field lattice coordinates, along with
concrete implementations (Identity, Sigmoid, Gaussian, Polynomial) and
a composition utility.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Union, Tuple
import numpy as np

class FieldFunction(ABC):
    """
    Abstract base class for field functions with variable input/output dimensionality.
    
    Subclasses implement ``_raw_function``; the ``__call__`` wrapper handles
    dimensionality validation, reshaping, and output-range clipping.
    
    Parameters
    ----------
    input_dim : int, optional
        Expected number of input dimensions (default is 1).
    output_dim : int, optional
        Number of output dimensions (default is 1).
    output_range : tuple of float, optional
        ``(min, max)`` clipping range for output values
        (default is ``(-inf, inf)``).
    parameters : dict, optional
        Arbitrary named parameters accessible as ``self.parameters``.
    """

    def __init__(self, input_dim: int = 1, output_dim: int = 1, 
                 output_range: Tuple[float, float] = (float('-inf'), float('inf')),
                 parameters: Dict[str, Any] = None):
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.output_range = output_range
        self.parameters = parameters or {}

    @abstractmethod
    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        """
        Core function logic to be implemented by subclasses.
        
        Parameters
        ----------
        x : numpy.ndarray
            Input array with last dimension matching ``input_dim``.
            
        Returns
        -------
        numpy.ndarray
            Raw (unclipped) output values.
        """
        pass

    def __call__(self, x: Union[float, list, np.ndarray]) -> Union[float, np.ndarray]:
        """
        Evaluate the function on input *x*.
        
        Validates input dimensionality, applies the raw function, reshapes
        multi-dimensional output, and clips to ``output_range``.
        
        Parameters
        ----------
        x : float, list, or numpy.ndarray
            Input value(s).
            
        Returns
        -------
        float or numpy.ndarray
            Clipped function output.
            
        Raises
        ------
        ValueError
            If the last dimension of *x* does not match ``input_dim``.
        """
        x = np.atleast_1d(x)
        if x.shape[-1] != self.input_dim:
            raise ValueError(f"Input dimensionality {x.shape[-1]} does not match expected {self.input_dim}")
        
        result = self._raw_function(x)
        
        if self.output_dim > 1:
            result = result.reshape(-1, self.output_dim)
        
        return np.clip(result, self.output_range[0], self.output_range[1])

    @staticmethod
    def compose(*functions: 'FieldFunction') -> 'FieldFunction':
        """
        Compose multiple FieldFunctions into a single callable.
        
        Functions are applied right-to-left: ``compose(f, g)(x)`` computes
        ``f(g(x))``. Adjacent output/input dimensions must match.
        
        Parameters
        ----------
        *functions : FieldFunction
            Two or more FieldFunction instances to compose.
            
        Returns
        -------
        FieldFunction
            A composed function with the input dimension of the last function
            and the output dimension/range of the first.
            
        Raises
        ------
        ValueError
            If fewer than two functions are given or dimensions are incompatible.
        """
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
        """
        Update the function's named parameters.
        
        Parameters
        ----------
        **kwargs
            Parameter names and values to set or update.
        """
        self.parameters.update(kwargs)


class Identity(FieldFunction):
    """Identity function that returns its input unchanged."""
    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        return x

class Sigmoid(FieldFunction):
    """
    Sigmoid (logistic) function mapping inputs to the (0, 1) range.
    
    Parameters
    ----------
    input_dim : int, optional
        Number of input dimensions (default is 1).
    """
    def __init__(self, input_dim: int = 1):
        super().__init__(input_dim, 1, (0, 1))
    
    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        return 1 / (1 + np.exp(-x))

class Gaussian(FieldFunction):
    """
    Gaussian (bell curve) function.
    
    Parameters
    ----------
    input_dim : int, optional
        Number of input dimensions (default is 1).
    mu : float, optional
        Mean of the Gaussian (default is 0).
    sigma : float, optional
        Standard deviation (default is 1).
    """
    def __init__(self, input_dim: int = 1, mu: float = 0, sigma: float = 1):
        super().__init__(input_dim, 1, (0, 1), {'mu': mu, 'sigma': sigma})
    
    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        return np.exp(-((x - self.parameters['mu']) ** 2) / (2 * self.parameters['sigma'] ** 2))

class Polynomial(FieldFunction):
    """
    Polynomial function defined by a list of coefficients.
    
    Evaluates ``c[0] + c[1]*x + c[2]*x^2 + ...``
    
    Parameters
    ----------
    coefficients : list of float
        Polynomial coefficients in ascending order of degree.
    input_dim : int, optional
        Number of input dimensions (default is 1).
    """
    def __init__(self, coefficients: list, input_dim: int = 1):
        super().__init__(input_dim, 1, parameters={'coefficients': coefficients})
    
    def _raw_function(self, x: np.ndarray) -> np.ndarray:
        return sum(c * x**i for i, c in enumerate(self.parameters['coefficients']))
