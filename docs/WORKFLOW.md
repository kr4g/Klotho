# Documentation Workflow Guide

This guide explains how to maintain Klotho's documentation as the codebase evolves.

## 🔄 **What Updates Automatically**

When you run `make html`, Sphinx automatically updates:

- ✅ **Existing docstrings** - Any changes to docstrings
- ✅ **Function signatures** - Parameter names, types, defaults  
- ✅ **Method lists** - New methods in existing classes
- ✅ **Type annotations** - Changes to type hints
- ✅ **Content** - Any documentation content changes

## ⚠️ **What Needs Manual Updates**

You must manually update `.rst` files when:

- 🆕 **New classes/functions** are added to modules
- 🗑️ **Classes/functions are deleted** or moved
- 📦 **New modules** are created
- 🏗️ **Major structural changes** occur

## 🛠️ **Daily Development Workflow**

### 1. **Quick Documentation Check**
```bash
# Check what needs documentation
make check-docs

# Quick rebuild and view
make dev
```

### 2. **When Adding New Code**
After adding a new class or function:

1. **Add NumPy-style docstring** to your new code
2. **Update the appropriate `.rst` file** in `docs/api/`
3. **Rebuild docs** to verify: `make dev`

### 3. **Example: Adding a New Class**

If you add `NewClass` to `klotho/tonos/pitch/pitch.py`:

1. **Add docstring to the class:**
```python
class NewClass:
    """
    Brief description of the class.

    Longer description explaining purpose and usage.

    Parameters
    ----------
    param1 : type
        Description of parameter.
    
    Attributes
    ----------
    attr1 : type
        Description of attribute.
    
    Examples
    --------
    >>> obj = NewClass(param1_value)
    >>> result = obj.method()
    """
```

2. **Update `docs/api/tonos.rst`:**
```rst
.. autoclass:: klotho.tonos.pitch.pitch.NewClass
   :members:
   :show-inheritance:
```

3. **Rebuild:** `make dev`

## 🔧 **Available Commands**

### Documentation Commands
```bash
# Basic Sphinx commands
make html           # Build HTML documentation
make clean          # Clean build directory
make help           # Show all available targets

# Klotho workflow commands
make dev            # Quick build and open in browser
make quick          # Quick clean build (no open)
make open           # Open existing docs in browser
make check-docs     # Check for missing docstrings

# Using scripts directly
./rebuild_docs.sh   # Rebuild with status messages
python ../check_docs.py  # Detailed documentation analysis
```

### File Watching (Optional)
For automatic rebuilds during development:

```bash
# Install sphinx-autobuild (one-time setup)
pip install sphinx-autobuild

# Auto-rebuild on file changes
sphinx-autobuild . _build/html --open-browser
```

## 📋 **Code Review Checklist**

When reviewing code changes, check:

- [ ] **New functions/classes have NumPy-style docstrings**
- [ ] **Documentation builds without errors**: `make html`
- [ ] **New items appear in documentation** (check `make dev`)
- [ ] **No broken cross-references**
- [ ] **Examples work correctly**

## 🚨 **Common Issues & Solutions**

### Missing Functions in Documentation
**Problem**: Added function but doesn't appear in docs
**Solution**: Add `.. autofunction::` directive to appropriate `.rst` file

### Broken Cross-References  
**Problem**: Warnings about unresolved references
**Solution**: Use proper module paths in docstrings (e.g., `klotho.tonos.Pitch`)

### Build Failures
**Problem**: Sphinx build fails with import errors
**Solution**: 
1. Check imports in problematic modules
2. Ensure virtual environment is activated
3. Verify all dependencies are installed

### Namespace Pollution
**Problem**: Utility functions appearing in class documentation
**Solution**: Use specific `.. autoclass::` instead of `.. automodule::`

## 🎯 **Best Practices**

### 1. **Write Docstrings First**
When creating new functions, write the docstring immediately:
```python
def new_function(param):
    """
    TODO: Brief description.
    
    Parameters
    ----------
    param : type
        Description.
    
    Returns
    -------
    type
        Description.
    """
    pass  # Implementation comes after
```

### 2. **Test Documentation Locally**
Always run `make dev` before committing to ensure:
- Documentation builds successfully
- New items appear correctly
- Examples work as expected

### 3. **Keep Examples Current**
Update docstring examples when APIs change:
- Test examples in your development environment
- Use realistic, meaningful examples
- Show both basic and advanced usage

### 4. **Document Edge Cases**
Include information about:
- Error conditions and exceptions
- Parameter constraints and validation
- Performance considerations
- Related functions and classes

## 🔮 **Automation Ideas**

### CI/CD Integration
Consider adding to your development workflow:

```yaml
# Example GitHub Actions step
- name: Build Documentation
  run: |
    cd docs
    make html
    
- name: Check Documentation Coverage
  run: python check_docs.py --fail-on-missing
```

### Pre-commit Hooks
```bash
# Check docs build before commit
pre-commit:
  cd docs && make html > /dev/null
```

## 📚 **Reference**

- [NumPy Docstring Guide](numpy_docstring_guide.md)
- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [numpydoc Style Guide](https://numpydoc.readthedocs.io/) 