"""Setup script for the Auriga Data Factory."""

from setuptools import setup, find_packages

setup(
    name="auriga-data-factory",
    version="1.0.0",
    description=(
        "Auriga Data Factory — offline-first research infrastructure for "
        "ingesting, validating, versioning, and approving fiducial datasets."
    ),
    author="Project Auriga",
    python_requires=">=3.9",
    packages=find_packages(exclude=["*.tests", "*.tests.*"]),
    entry_points={
        "console_scripts": [
            "auriga-factory=auriga_data_factory.cli.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
