"""
Setup configuration for EditPy package.
"""

from setuptools import setup, find_packages

setup(
    name="editpy",
    version="0.1.0",
    description="Advanced Terminal Text Editor and Hex Viewer",
    author="TN3W",
    author_email="tn3w@protonmail.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pygments>=2.19.1",
        "windows-curses>=2.4.1; platform_system == 'Windows'",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "editpy=editpy.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console :: Curses",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
) 