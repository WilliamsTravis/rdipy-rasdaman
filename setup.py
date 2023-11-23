# -*- coding: utf-8 -*-
"""Module Name.

Author: travis
Date: Wed Nov 22 07:31:27 PM MST 2023
"""
import os

from setuptools import setup


REPO_DIR = os.path.abspath(os.path.dirname(__file__))
VERSION_FILE = os.path.join(REPO_DIR, "geodaman", "version.py")
DESCRIPTION = "A description of the package."


with open(os.path.join(REPO_DIR, "README.md"), encoding="utf-8") as f:
    README = f.read()

with open("requirements.txt") as f:
    REQUIREMENTS = f.read().splitlines()


setup(
    name="geodaman",
    version="0.0.1",
    description=DESCRIPTION,
    long_description=README,
    author="Travis Williams",
    author_email="Travis.Williams@nrel.gov",
    packages=["geodaman"],
    zip_safe=False,
    keywords="geodaman",
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10"
    ],
    test_suite="tests",
    include_package_data=True,
    package_data={"data": ["*"]},
    install_requires=REQUIREMENTS
)
