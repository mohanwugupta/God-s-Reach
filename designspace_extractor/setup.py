"""
Setup configuration for designspace_extractor package.
"""
from setuptools import setup, find_packages

setup(
    name="designspace_extractor",
    version="1.0.0-dev",
    description="Automated Design-Space Parameter Extractor for Motor Adaptation Studies",
    author="Mohan Gupta / Princeton Lab",
    python_requires=">=3.11",
    packages=find_packages(),
    install_requires=[
        "pyyaml>=6.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "sqlalchemy>=2.0.0",
        "pydantic>=2.0.0",
        "scipy>=1.10.0",
        "h5py>=3.8.0",
        "grobid-client-python>=0.0.5",
        "pypdf>=3.0.0",
        "google-api-python-client>=2.0.0",
        "google-auth>=2.0.0",
        "google-auth-oauthlib>=1.0.0",
        "google-auth-httplib2>=0.1.0",
        "anthropic>=0.18.0",
        "openai>=1.0.0",
        "hedtools>=0.4.0",
        "click>=8.1.0",
        "tqdm>=4.65.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
    ],
    entry_points={
        "console_scripts": [
            "designspace-extractor=cli:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.sql"],
    },
)
