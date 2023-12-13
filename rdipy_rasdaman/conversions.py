# -*- coding: utf-8 -*-
"""Module Name.

Module description.

Author: travis
Date: Wed Dec 13 03:55:17 PM MST 2023
"""
from pathlib import Path

import h5py
import pandas as pd
import xarray as xr


HOME = Path("/data/rdi")
FILE = HOME.joinpath("reference_2030_moderate_115hh_170rd_bespoke.h5")


class Conversions:
    """Methods for converting particular file formats in RDI."""

    def __init__(self, file, format="netcdf"):
        """Initialize a Conversions object."""
        self.file = file
        self.format = format
        self.ds = self._open(file)

    def __del__(self):
        """Close Conversions file on object destruction."""
        self.ds.close()

    def __enter__(self):
        """Open Conversions file with context management."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close Conversions file with context management."""
        self.ds.close()

    def __repr__(self):
        """Return an Conversions object representation string."""
        address = hex(id(self))
        name = self.__class__.__name__
        msgs = [f"\n   {k}={v}" for k, v in self.__dict__.items()]
        msg = " ".join(msgs)
        return f"<{name} object at {address}>: {msg}"

    def _infer_driver(self, file):
        """Return an appropriatefile driver."""

    def _open(self, file):
        """Return open file object."""


if __name__ == "__main__":
    file = FILE
    self = Conversions(file=file)
