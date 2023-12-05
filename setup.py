# -*- coding: utf-8 -*-
"""Install rdipy-rasdaman.

Note:
    - Please confirm that GDAL is installed on your system or run
      `install_gdal.sh` before installating this package.
    - If you are having problems with the Python GDAL package, try installing
      with the `--no-cache-dir` option.
    - Still having problems? Are you a Windows user? Even if not, perhaps your
      GDAL is not in /usr/include/? Change lines 16 and 17 to point to your
      GDAL executable.
    - Operating in a conda environment and getting something like:
        "GLIBCXX 3.4.30 not found in conda environment"? Try linking the
        offending library from your system-level directories to the
        corresponding conda env libraries, as in this example:
        https://askubuntu.com/questions/1418016/glibcxx-3-4-30-not-found-in-\
            conda-environment

Author: travis
Date: Wed Nov 22 07:31:27 PM MST 2023
"""
import os
import subprocess as sp

from setuptools import setup

os.environ["CPLUS_INCLUDE_PATH"] = "/usr/include/gdal"
os.environ["C_INCLUDE_PATH"] = "/usr/include/gdal"


REPO_DIR = os.path.abspath(os.path.dirname(__file__))
VERSION_FILE = os.path.join(REPO_DIR, "geodaman", "version.py")
DESCRIPTION = "A description of the package."


def get_gdal_version():
    """Return system GDAL version."""
    process = sp.Popen(
        ["gdal-config", "--version"],
        stdout=sp.PIPE,
        stderr=sp.PIPE
    )

    sto, ste = process.communicate()

    if ste:
        print(ste)
        raise OSError("GDAL is causing problems again. Make sure you can run "
                      "'gdal-config --version' successfully in your terminal")

    version = sto.decode().replace("\n", "")

    return version


def get_requirements():
    """Get requirements and update gdal version number."""
    with open("requirements.txt", encoding="utf-8") as file:
        reqs = file.readlines()

    gdal_version = get_gdal_version()
    gdal_line = f"gdal=={gdal_version}\n"
    reqs.append(gdal_line)

    return reqs


with open(os.path.join(REPO_DIR, "README.md"), encoding="utf-8") as f:
    README = f.read()


setup(
    name="rdipy_rasdaman",
    version="0.0.1",
    description=DESCRIPTION,
    long_description=README,
    author="Travis Williams",
    author_email="Travis.Williams@nrel.gov",
    packages=["rdipy_rasdaman"],
    zip_safe=False,
    keywords="rdipy-rasdaman",
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
    install_requires=get_requirements()
)
