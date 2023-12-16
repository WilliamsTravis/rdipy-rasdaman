# -*- coding: utf-8 -*-
"""Module Name.

Module description.

Author: travis
Date: Wed Dec 13 03:55:17 PM MST 2023
"""
from pathlib import Path

import h5py
import matplotlib.animation as ani
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

from scipy.spatial import cKDTree
from revruns.rraster import to_grid
from revruns import rr


HOME = Path("/data/rdi")
FILE = HOME.joinpath("reference_2030_moderate_115hh_170rd_bespoke.h5")


def animate(array, time_index):
    """Run a quick animation of the dataset."""
    fig, ax = plt.subplots()
    frame = 0
    im = plt.imshow(array[frame], animated=True)
    title = ax.text(0.5, 0, time_index[frame], transform=ax.transAxes,
                    ha="center")
    plt.colorbar(shrink=0.5)

    def update(*args):
        global frame
        title.set_text(time_index[frame])
        im.set_array(array[frame])
        frame += 1
        frame %= len(array)
        return im,

    _ = ani.FuncAnimation(fig, update, interval=250)
    plt.show()


class NREL_HDF5:
    """Methods for converting NREL HDF5 file formats in RDI."""

    def __init__(self, file, format="netcdf"):
        """Initialize a NREL_HDF5 object."""
        self.file = file
        self.format = format
        self.ds = self._open()

    def __del__(self):
        """Close NREL_HDF5 object on object destruction."""
        self.ds.close()

    def __enter__(self):
        """Open NREL_HDF5 object with context management."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close NREL_HDF5 object with context management."""
        self.ds.close()

    def __repr__(self):
        """Return an NREL_HDF5 object representation string."""
        address = hex(id(self))
        name = self.__class__.__name__
        msgs = [f"\n   {k}={v}" for k, v in self.__dict__.items()]
        msg = " ".join(msgs)
        return f"<{name} object at {address}>: {msg}"

    @property
    def meta(self):
        """Return formatted meta object as geodataframe object."""
        meta = pd.DataFrame(self.ds["meta"][:])
        meta.rr.decode()
        meta = meta.rr.to_geo()
        return meta

    def make_grid(self, variable="cf_profile-2012", crs="esri:102008"):
        """Convert HDF5 file to grid."""
        # Get meta object
        meta = self.meta

        # Get the target values and time index
        data = self.ds[variable][:] / self.ds[variable].attrs["scale_factor"]
        time_index = [t.decode() for t  in self.ds["time_index"]]

        # I happen to know that the resolution should be about 11.5 km 
        resolution = 0.16

        # Get the ndarray and geotransform
        array, transform = to_grid(meta, data, resolution)

        plt.imshow(array)
        plt.show()

    def _open(self):
        """Return open file object."""
        return h5py.File(self.file)


if __name__ == "__main__":
    file = FILE
    self = NREL_HDF5(file=file)
    self.make_grid()
