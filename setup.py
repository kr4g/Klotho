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
    packages=find_packages(),
    install_requires=[
        'pandas',
        'numpy',
        'sympy',
        'regex',
        'matplotlib',
        'tabulate',
        'networkx',
        'rustworkx',
        'scipy',
        'python-osc',
        'abjad',
        'mido',
        'pyfluidsynth',
        'soundfile',
        'IPython',
        'panel',
        'bokeh',
        'jupyter_bokeh',
        'diversipy'
    ],
    extras_require={
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
        ]
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
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Artistic Software',
    ],
    python_requires='>=3.10',
)
