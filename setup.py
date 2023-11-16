from os import path

from setuptools import find_namespace_packages
from setuptools import setup

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

requirements = [
    "bg_atlasapi",
    "imagecodecs; python_version>='3.9'",
    "neurom>=3,<4",
    "numpy",
    "pandas",
    "pyyaml>=5.3",
    "retry",
    "rich",
    "vedo>=2023.5.0",
    "vtk",
]

setup(
    name="morphapi",
    description="A lightweight python package to download neuronal morphologies",
    long_description=long_description,
    long_description_content_type="text/markdown",
    use_scm_version=True,
    setup_requires=[
        "setuptools_scm",
    ],
    install_requires=requirements,
    extras_require={
        "nb": ["jupyter", "k3d"],
        "dev": [
            "pytest-cov",
            "pytest",
            "pytest-html",
            "coveralls",
            "coverage<=4.5.4",
            "pytest-sugar",
            "allensdk",
        ],
    },
    python_requires=">=3.8",
    packages=find_namespace_packages(
        exclude=("Installation", "Meshes", "Metadata", "Screenshots")
    ),
    include_package_data=True,
    url="https://github.com/brainglobe/morphapi",
    author="Federico Claudi",
    zip_safe=False,
)
