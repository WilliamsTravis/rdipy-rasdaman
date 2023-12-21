# -*- coding: utf-8 -*-
"""RDI Conversions

TODO:
- Use irregular grid and interpolation for WTK-based files.
    - https://stackoverflow.com/questions/26758655/how-to-make-grid-of-the-irregular-data
- Combine years into single time-series

Author: travis
Date: Wed Dec 13 03:55:17 PM MST 2023
"""
import datetime as dt

from cftime import date2num
from dateutil import parser
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

    def make_grid(self, variable="cf_profile-2012"):
        """Convert HDF5 file to grid."""
        # Get meta object
        meta = self.meta

        # Get the target values and time indexgdal geo transform
        data = self.ds[variable][:] / self.ds[variable].attrs["scale_factor"]

        # I happen to know that the resolution should be about 11.5 km   # <--- Variable, infer or parameterize
        resolution = 0.16

        # Get the ndarray and geotransform
        array, geom = to_grid(meta, data, resolution)

        return array, geom, variable

    @property
    def time(self):
        """Return time index in cf-compatible format."""
        time_index = [t.decode() for t in self.ds["time_index"]]
        time = [parser.parse(t) for t in time_index]
        units = 'hours since {:%Y-%m-%d 00:00}'.format(time[0])
        values = date2num(time, units)
        return values, units

    def _open(self):
        """Return open file object."""
        return h5py.File(self.file)

    def main(self):
        """Convert file to NetCDF4 file."""
        # Get the grid and geotransform
        array, geom, variable = self.make_grid()

        # Get the time index and it's units
        time, time_units = self.time

        # Build Data Array
        lats = [geom["ymax"] + (geom["yres"] * i) for i in range(geom["ny"])]
        lons = [geom["xmin"] + (geom["xres"] * i) for i in range(geom["nx"])]
        darray = xr.DataArray(
            array,
            coords=[time, lats, lons],
            dims=["time", "latitude", "longitude"]
        )

        # Data Array Attributes
        darray.attrs["standard_name"] = "capacity_factor"    # <--- Variable, infer or parameterize
        darray.attrs["long_name"] = "Capacity Factor"   # <--- Variable, infer or parameterize
        darray.attrs["missing_value"] = np.finfo(darray.dtype).max
        darray.attrs["_FillValue"] = np.finfo(darray.dtype).max

        darray.attrs["valid_min"] = 0
        darray.attrs["valid_max"] = 1

        darray["latitude"].attrs["standard_name"] = "latitude"
        darray["latitude"].attrs["long_name"] = "latitude"
        darray["latitude"].attrs["units"] = "degrees_north"

        darray["longitude"].attrs["standard_name"] = "longitude"
        darray["longitude"].attrs["long_name"] = "longitude"
        darray["longitude"].attrs["units"] = "degrees_east"

        darray["time"].encoding["units"] = time_units
        darray["time"].attrs["units"] = time_units
        darray["time"].attrs["standard_name"] = "time"
        darray["time"].attrs["long_name"] = "time"

        darray["crs"] = int()
        darray["crs"].attrs["grid_mapping_name"] = "latitude_longitude"
        darray["crs"].attrs["longitude_of_prime_meridian"] = 0.0
        darray["crs"].attrs["semi_major_axis"] = 6378137.0
        darray["crs"].attrs["inverse_flattening"] = 298.257223563
        darray.attrs["grid_mapping"] = "crs"

        # Build Dataset
        var_name = variable.lower().replace("-", "_")
        ds = xr.Dataset(data_vars={var_name: darray})

        # Global Attributes
        ds.attrs["Conventions"] = "CF-1.7"     # <--- Double check the most recent standard version
        ds.attrs["title"] = "reV Rep-Profile Sample"
        ds.attrs["nc.institution"] = "Unidata"
        ds.attrs["source"] = "reV"
        ds.attrs["date"] = str(dt.datetime.utcnow())
        ds.attrs["references"] = ""
        ds.attrs["comment"] = ""

        # Write to file
        ds.to_netcdf("/data/rdi/test.nc", format="NETCDF4")


if __name__ == "__main__":
    file = FILE
    self = NREL_HDF5(file=file)
    self.main()
