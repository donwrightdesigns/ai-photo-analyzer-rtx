#!/usr/bin/env python3
"""
Setup script for AI Image Analyzer
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read requirements
with open('requirements.txt') as f:
    requirements = f.read().splitlines()
    # Filter out comments and empty lines
    requirements = [req for req in requirements if req and not req.startswith('#')]

setup(
    name="ai-image-analyzer",
    version="1.0.0",
    author="Don Wright",
    author_email="your-email@example.com",
    description="AI-powered image analysis and tagging system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ai-image-analyzer",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Photographers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.12",
    install_requires=requirements,
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'black>=22.0.0',
            'flake8>=4.0.0',
        ]
    },
    entry_points={
        'console_scripts': [
            'ai-image-analyzer-gemini=scripts.gemini_analyzer:main',
            'ai-image-analyzer-llava=scripts.llava_analyzer:main',
            'ai-image-analyzer-web=web.app:main',
        ],
    },
    include_package_data=True,
    package_data={
        'web': ['templates/*', 'static/*/*'],
        'lightroom-plugin': ['*.lua'],
    },
)
