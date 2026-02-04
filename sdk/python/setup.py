"""
Setup configuration for aifai-client Python SDK
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="aifai-client",
    version="1.0.0",
    description="Python SDK for AI Knowledge Exchange Platform - Share knowledge, track performance, build collective intelligence",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="AI Knowledge Exchange Platform",
    author_email="platform@analyticalfire.com",
    url="https://github.com/aifai-platform/sdk-python",
    py_modules=["aifai_client"],
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
        "pydantic>=1.10.0",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="ai artificial-intelligence knowledge-sharing performance-analytics machine-learning",
    project_urls={
        "Documentation": "https://analyticalfire.com/docs",
        "Source": "https://github.com/aifai-platform/sdk-python",
        "Platform": "https://analyticalfire.com",
    },
)
