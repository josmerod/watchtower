#!/usr/bin/env python3
"""Setup script for Watchtower project."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read requirements from requirements.txt
requirements = []
with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

# Read dev requirements from requirements-dev.txt
dev_requirements = []
try:
    with open("requirements-dev.txt", "r", encoding="utf-8") as f:
        dev_requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
except FileNotFoundError:
    pass

# Read ML requirements from requirements-ml.txt
ml_requirements = []
try:
    with open("requirements-ml.txt", "r", encoding="utf-8") as f:
        ml_requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
except FileNotFoundError:
    pass

# Read web requirements from requirements-web.txt
web_requirements = []
try:
    with open("requirements-web.txt", "r", encoding="utf-8") as f:
        web_requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
except FileNotFoundError:
    pass

setup(
    name="watchtower",
    version="0.1.0",
    author="Watchtower Team",
    author_email="team@watchtower.dev",
    description="A comprehensive monitoring and ETL framework for scraping, aggregating, and visualizing data from diverse online sources",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/watchtower",
    packages=find_packages(include=["src*"]),
    package_dir={"watchtower": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements,
        "ml": ml_requirements,
        "web": web_requirements,
        "all": dev_requirements + ml_requirements + web_requirements,
    },
    entry_points={
        "console_scripts": [
            "watchtower-app=src.web.fullstreamlit.app:main",
            "watchtower-etl=src.etl.base:run_etl_cli",
            "watchtower-watcher=src.watchers.base_watcher:run_watcher_cli",
        ],
    },
    include_package_data=True,
    package_data={
        "watchtower": [
            "web/fullstreamlit/styles/*.css",
            "web/fullstreamlit/assets/*",
            "config/*.json",
            "config/*.yaml",
        ],
    },
    zip_safe=False,
    keywords="data-collection monitoring etl web-scraping streamlit",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/watchtower/issues",
        "Source": "https://github.com/yourusername/watchtower",
        "Documentation": "https://github.com/yourusername/watchtower/docs",
    },
) 