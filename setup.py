
from setuptools import setup, find_packages
import re

with open('allopy/__init__.py', 'r') as f:
    version = re.search(r"__version__\s+=\s+'(.*)'", f.read()).group(1)

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='allopy',
    version=version,
    author='Ryan Millett',
    author_email='rmillett@mat.ucsb.edu',
    packages=find_packages(),
    install_requires=[
        'pandas',
        'numpy',
        'regex',
        'matplotlib',
        'ipywidgets',
        'IPython',
        'tabulate',
        'PySide6',
        'sympy',
        'networkx',
    ],
    # tests_require=[
    #     'pytest',
    # ],
    description='AlloPy is an open source Python package designed to work as both a stand-alone software and in tandem with AlloLib Playground as a computer-assisted toolkit, work environment, notation editor, and general educational resource for the methods, models, works, and frameworks associated with the art and craft of transmodal metacomposition.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/kr4g/AlloPy',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        # 'Intended Audience :: Developers',
        'License :: CC BY-SA 4.0',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)
