from setuptools import setup, find_packages
import re

with open('klotho/__init__.py', 'r') as f:
    version = re.search(r"__version__\s+=\s+'(.*)'", f.read()).group(1)

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='klotho-cac',
    version=version,
    author='Ryan Millett',
    author_email='rmillett@mat.ucsb.edu',
    # Scoped deliberately. A bare find_packages() picks up ANY directory with
    # an __init__.py, and it was picking up `benchmarks/` -- which is
    # gitignored, tracked nowhere, and shipped in klotho-cac 10.18.0 as a
    # TOP-LEVEL package in every user's site-packages (verified against the
    # published wheel, 2026-08-30). Seven files reproducible from no clone.
    packages=find_packages(include=['klotho', 'klotho.*']),
    include_package_data=True,
    install_requires=[
        'numpy',
        'sympy',
        'pandas',
        'scipy',
        'matplotlib',
        'plotly',
        'tabulate',
        'networkx',
        'rustworkx',
        'scikit-learn>=1.8',
        'IPython',
    ],
    extras_require={
        'sampling': [
            'diversipy',
        ],
        'docs': [
            'sphinx>=7.0.0',
            'sphinx-rtd-theme',
            'numpydoc',
            'sphinx-autodoc-typehints',
            'sphinx-copybutton',
        ],
        'dev': [
            'pytest',
            'sphinx>=7.0.0',
            'sphinx-rtd-theme',
            'numpydoc',
            'sphinx-autodoc-typehints',
            'sphinx-copybutton',
        ],
    },
    description='Graph-Oriented Computer-Assisted Composition in Python',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/kr4g/Klotho',
    license='CC-BY-SA-4.0',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: Other/Proprietary License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Artistic Software',
    ],
    python_requires='>=3.11',
)
