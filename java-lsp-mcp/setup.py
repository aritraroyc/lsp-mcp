"""
Setup script for Java Error Checker MCP Service
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="java-error-checker-mcp",
    version="1.0.0",
    description="MCP server for checking Java compilation errors using JDTLS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="MCP Contributors",
    license="MIT",
    packages=find_packages(),
    install_requires=[
        "mcp>=0.9.0",
        "aiohttp>=3.9.0",
        "starlette>=0.35.0",
        "uvicorn>=0.25.0",
        "python-dotenv>=1.0.0",
    ],
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "java-error-checker=server:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
