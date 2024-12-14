from setuptools import setup, find_packages
import re

with open('klotho/__init__.py', 'r') as f:
    version = re.search(r"__version__\s+=\s+'(.*)'", f.read()).group(1)

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='klotho',
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
        'hypernetx',
        'python-osc',
        'opencv-python',
        'tqdm',
    ],
    # tests_require=[
    #     'pytest',
    # ],
    description='An open source computer-assisted composition toolkit implemented in Python',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/kr4g/Klotho',
    license='CC-BY-SA-4.0',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Creative Commons License',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3 :: Only',
    ],
    python_requires='>=3.10',
)
