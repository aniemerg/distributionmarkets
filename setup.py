from setuptools import setup, find_packages

setup(
    name="distributionmarkets",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy",
        "scipy",
        "matplotlib",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
        ],
    },
)
