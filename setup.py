from setuptools import setup, find_namespace_packages
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

requirements = [
    "numpy",
    "pandas",
    "vedo>=2020.3.3",
    "vtk",
    "allensdk",
    "tqdm",
    "pyyaml>=5.3",
    "scikit-image",
    "neurom",
    "bg_atlasapi",
]

setup(
    name="morphapi",
    version="0.1.1.6",
    description="A lightweight python package to download neuronal morphologies",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=requirements,
    extras_require={
        "nb": ["jupyter", "k3d"],
        "dev": [
            "pytest-cov",
            "pytest",
            "coveralls",
            "coverage<=4.5.4",
            "pytest-sugar",
        ],
    },
    python_requires=">=3.6",
    packages=find_namespace_packages(
        exclude=("Installation", "Meshes", "Metadata", "Screenshots")
    ),
    include_package_data=True,
    url="https://github.com/brainglobe/morphapi",
    author="Federico Claudi",
    zip_safe=False,
)
