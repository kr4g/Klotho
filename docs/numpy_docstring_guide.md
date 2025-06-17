# NumPy Docstring Style Guide for Klotho

This guide provides templates and examples for documenting Klotho code using NumPy-style docstrings.

## Basic Template

```python
def function_name(param1, param2, param3=None):
    """
    Brief one-line description of the function.

    Longer description providing more detail about what the function does,
    any important algorithmic details, mathematical background, or usage notes.
    Keep this concise but informative.

    Parameters
    ----------
    param1 : type
        Description of the first parameter.
    param2 : type
        Description of the second parameter.
    param3 : type, optional
        Description of the optional parameter (default is None).

    Returns
    -------
    return_type
        Description of what is returned.

    Raises
    ------
    ValueError
        Description of when this exception is raised.
    TypeError
        Description of when this exception is raised.

    See Also
    --------
    related_function : Brief description of relationship.
    AnotherClass.method : Brief description of relationship.

    Notes
    -----
    Any important mathematical formulas, algorithmic details, or implementation
    notes. Use LaTeX for mathematical expressions:
    
    .. math:: f(x) = \\sum_{i=0}^{n} a_i x^i

    References
    ----------
    .. [1] Author, A. "Title of Paper." Journal Name, Volume(Issue), pp. 123-456, Year.
    .. [2] Author, B. "Book Title." Publisher, Year.

    Examples
    --------
    >>> import klotho
    >>> result = function_name('example', 42)
    >>> print(result)
    Expected output here
    """
    pass
```

## Class Template

```python
class ExampleClass:
    """
    Brief one-line description of the class.

    Longer description of the class, its purpose, and how it fits into
    the larger Klotho ecosystem. Mention any important mathematical
    concepts or musical theory that applies.

    Parameters
    ----------
    param1 : type
        Description of the first constructor parameter.
    param2 : type, optional
        Description of the optional constructor parameter.

    Attributes
    ----------
    attr1 : type
        Description of the first attribute.
    attr2 : type
        Description of the second attribute.

    Methods
    -------
    method1(arg1, arg2)
        Brief description of what method1 does.
    method2(arg1)
        Brief description of what method2 does.

    See Also
    --------
    RelatedClass : Brief description of relationship.

    Notes
    -----
    Any important implementation details or mathematical background.

    Examples
    --------
    >>> obj = ExampleClass(param1_value)
    >>> result = obj.method1(arg1_value, arg2_value)
    >>> print(result)
    Expected output here
    """
    
    def __init__(self, param1, param2=None):
        """
        Initialize the ExampleClass.

        Parameters
        ----------
        param1 : type
            Description of param1.
        param2 : type, optional
            Description of param2 (default is None).
        """
        pass

    def method1(self, arg1, arg2):
        """
        Brief description of method1.

        Parameters
        ----------
        arg1 : type
            Description of arg1.
        arg2 : type
            Description of arg2.

        Returns
        -------
        type
            Description of return value.
        """
        pass
```

## Property Template

```python
@property
def example_property(self):
    """
    Brief description of the property.
    
    Returns
    -------
    type
        Description of what the property returns.
        
    Examples
    --------
    >>> obj = ExampleClass()
    >>> value = obj.example_property
    >>> print(value)
    Expected output here
    """
    return self._internal_value
```

## Common Types for Klotho

Use these consistent type descriptions:

- `Pitch` - A Klotho Pitch object
- `PitchCollection` - A collection of pitch intervals
- `TemporalUnit` - A Klotho temporal structure
- `RhythmTree` - A Klotho rhythm tree
- `list of float` - List containing float values
- `list of Fraction` - List containing Fraction objects
- `numpy.ndarray` - NumPy array
- `pandas.DataFrame` - Pandas DataFrame
- `Union[int, float]` - Can be either int or float
- `Optional[str]` - Can be string or None

## Musical Examples

For musical functions, provide musically meaningful examples:

```python
def transpose_pitch(pitch, interval):
    """
    Transpose a pitch by a given interval.

    Parameters
    ----------
    pitch : Pitch
        The pitch to transpose.
    interval : Union[str, float, Fraction]
        The interval to transpose by. Can be a ratio string ('3/2'),
        a decimal (1.5), or a Fraction object.

    Returns
    -------
    Pitch
        The transposed pitch.

    Examples
    --------
    Transpose A4 up by a perfect fifth:
    
    >>> a4 = Pitch('A', 4)
    >>> perfect_fifth = '3/2'
    >>> a4_fifth = transpose_pitch(a4, perfect_fifth)
    >>> print(a4_fifth.pitchclass, a4_fifth.octave)
    E 5
    """
```

## Key Guidelines

1. **First line**: Always a brief, imperative description
2. **Parameters**: Always describe type and meaning
3. **Returns**: Always describe what is returned
4. **Examples**: Include realistic musical examples when possible
5. **Math**: Use LaTeX notation for mathematical expressions
6. **Types**: Be specific about Klotho types vs. standard Python types
7. **Units**: Always specify units for musical quantities (Hz, cents, seconds, etc.)
8. **References**: Include academic references for algorithms or theory 