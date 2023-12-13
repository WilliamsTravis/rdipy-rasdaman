# -*- coding: utf-8 -*-
"""Core rasdaman/rasdapy database access methods.

Author: travis
Date: Wed Nov 22 07:31:27 PM MST 2023
"""
import json
import os
import subprocess as sp

from pathlib import Path

import xarray as xr

from osgeo import gdal
from rasdapy.db_connector import DBConnector
from rasdapy.query_executor import QueryExecutor

from rdipy_rasdaman import GEODAMAN_DIR


RMANHOME = os.getenv("RMANHOME")
DATA_DIR = GEODAMAN_DIR.joinpath("data")
SAMPLE = GEODAMAN_DIR.parent.joinpath("tests/data/pdsi_1895_10_sample.nc")

USR = "rasadmin"
PW = "rasadmin"
GROUPS = [
    "RAS_STRUCT_TYPES",
    "RAS_MARRAY_TYPES",
    "RAS_SET_TYPES"
]
TYPE_MAP = {
    "Float32": "float"
}
POSSIBLE_LATS = ["y", "ylat", "latitude", "lat"]
POSSIBLE_LONS = ["x", "xlon", "xlong", "longitude", "lon", "long"]


class RasdamanQueryError(Exception):
    """"Errors from running with rasdapy.QueryExecutor."""


class RasdamanDropError(Exception):
    """"Errors from dropping objects with rasdapy.QueryExecutor."""


class RDBC:
    """Rasdaman Database Control object."""

    def __init__(self):
        """Initialize an RDBC object."""
        self.db = DBConnector("localhost", 7001, "rasadmin", "rasadmin")
        self.qe = QueryExecutor(self.db)
        self.db.open()

    def __del__(self):
        """Close database connection on object destruction."""
        self.db.close()

    def __enter__(self):
        """Open database connection with context management."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close database connection with context management."""
        self.db.close()

    def __repr__(self):
        """Return an RDBC object representation string."""
        address = hex(id(self))
        name = self.__class__.__name__
        msgs = [f"\n   {k}={v}" for k, v in self.__dict__.items()]
        msg = " ".join(msgs)
        return f"<{name} object at {address}>: {msg}"

    @property
    def collections(self):
        """Return list of collections in database."""
        query = "select c from RAS_COLLECTIONNAMES as c"
        out = self.read(query)
        return out.data

    def drop(self, query):
        """Drop data from the database with a query.

        Parameters
        ----------
        query : str
            String representation of database SQL query.

        Returns
        -------
        rasdapy.query_result.QueryResult : A rasdapy output object.
        """
        out = self.qe.execute_write(query)
        if "with_error" in out.__dict__:
            if out.with_error:
                msg = out.error_message()
                raise RasdamanQueryError(f"Read Error: {msg}")
        return out

    def dropcol(self, collection):
        """Drop collection from database."""
        query = f"drop collection {collection}"
        out = self.drop(query)
        return out

    def list(self, collection=None):
        """List collections in db.

        Parameters
        ----------
        collection : bool
            Return contents of specified collection, else return list of
            collections.

        Returns
        -------
        list : List of items, with the type depending on user arguments.
        """
        if not collection:
            contents = self.qe.execute_read(
                "select c from RAS_COLLECTIONNAMES as c"
            )
        else:
            contents = self.qe.execute_read(
                f"select c from RAS_COLLECTIONNAMES.{collection} as c"  # ?
            )

        return contents.data

    def read(self, query):
        """Read data from the database with a query.

        Parameters
        ----------
        query : str
            String representation of database SQL query.

        Returns
        -------
        rasdapy.query_result.QueryResult : A rasdapy output object.
        """
        out = self.qe.execute_read(query)
        if "with_error" in out.__dict__:
            if out.with_error:
                msg = out.error_message()
                raise RasdamanQueryError(f"Read Error: {msg}")
        return out

    @property
    def types(self):
        """List available database types."""
        types = {}
        for group in GROUPS:
            gtypes = self.read(f"select t from {group} as t")
            types[group] = gtypes.data
        return types

    def write(self, query):
        """Write items to a database with a query.

        Parameters
        ----------
        query : str
            String representation of database SQL query.

        Returns
        -------
        rasdapy.query_result.QueryResult : A rasdapy output object.
        """
        out = self.qe.execute_write(query)
        if "with_error" in out.__dict__:
            if out.with_error:
                msg = out.error_message()
                raise RasdamanQueryError(f"Write Error: {msg}")
        return out


class Importer(RDBC):
    """Methods for building WCST recipes for importing data."""

    def __init__(self):
        """Initialize Importer object."""
        super().__init__()
        self.rasdir = Path(RMANHOME)
        self.recipe_dir = self.rasdir.joinpath("share/rasdaman/wcst_import/"
                                               "recipes_custom")
        self.wcst_import = self.rasdir.joinpath("bin/wcst_import.sh")

    def get_driver(self, path):
        """Return the appropriate driver for a file (must be GDAL-compatible).

        Parameters
        ----------
        path : str | pathlib.PosixPathtif
        -------
        str : A string representation of the driver appropriate to this file.
        """
        obj = gdal.Open(path)
        driver = obj.GetDriver().LongName
        return driver

    def get_crs(self, path):
        """Return the appropriate CRS ingredient string for a file."""

    def help(self):
        """Print help text for wcst import method."""
        sp.run([self.wcst_import, "--help"], shell=False,
               executable="/bin/bash", check=True)

    def load(self, path, mock=False):
        """Import file into Rasdaman database.

        Parameters
        ----------
        path : str | PosixPath
            Path to file to load into Rasdaman. 
        mock : bool
            If true, no data will be loaded, the process will only be
            checked for validity.
        """
        # Write temporary ingredients file
        dst = "./tmp_ingredients.json"
        ingredients = self.make_ingredients(path, mock=mock)
        with open(dst, "w", encoding="utf-8") as file:
            file.write(json.dumps(ingredients, indent=4))

        # Call the import wcst script
        _ = sp.run(f"{str(self.wcst_import)} {dst}", shell=True, check=False,
                   executable="/bin/bash")
        os.remove(dst)

    def make_ingredients(self, path, mock=False):
        """Make an ingredients JSON for a file.

        Parameters
        ----------
        path : str | PosixPath
            Path to file to load into Rasdaman.
        mock : bool
            If true, no data will be loaded, the process will only be
            checked for validity.
        """
        driver = self.get_driver(path)
        if driver == "Network Common Data Format":
            ingredients = self._ingredients_nc(path, mock=mock)
        else:
            raise NotImplementedError(f"Haven't figured {driver} method out"
                                      "yet")
        return ingredients

    @property
    def sample(self, type="netcdf"):
        """Read in a sample ingredients file"""
        sample_dir = self.rasdir.joinpath("share/rasdaman/wcst_import/"
                                          "ingredients")
        path = list(sample_dir.glob(f"*{type}.json"))[0]
        with open(path, "r", encoding="utf-8") as file:
            config = json.load(file)
        return config

    @property
    def template(self):
        """Return the template ingredients file with descriptions."""
        sample_dir = self.rasdir.joinpath("share/rasdaman/wcst_import/"
                                          "ingredients")
        path = sample_dir.joinpath("possible_ingredients.json")
        with open(path, "r", encoding="utf-8") as file:
            config = json.load(file)
        return config

    def _ingredients_nc(self, path, variable, mock=False):
        """Create an ingedients JSON for a NetCDF file (a specific format)."""
        # Make sure this path is a Posix path
        path = Path(path)
        collection = f"{path.stem}_nc"

        # Create a collection
        if collection not in self.collections:
            query = f"create collection {collection} FloatSet3"
            self.write(query)


        # Retrieve information from file
        ds = xr.open_dataset(path, decode_times=True)
        variables = [v for v in ds if v != "crs"]
        time_var = ds[variables[0]].dims[0]
        time = [str(t) for t in ds[time_var].data]

        # Build initial config
        config = {
            "service_url": "http://localhost:8080/rasdaman/ows",
            "tmp_directory": "/tmp/",
            "automated": True,  # Human input required, turn on to avoid
            "mock": mock,
            "track_files": False,
            "subset_correction": False
        }

        # Build initial input
        inputs = {
            "coverage_id": collection,
            "paths": [str(path)]
        }

        # Define axes
        axes = {
            "ansi": {
                "min": time[0],
                "max": time[-1],
                "directPositions": str(list(time)),
                "irregular": True,
                "resolution": "1",
                "gridOrder": 0,
                "type": "ansidate"
            },
            "Lat": {
                "min": "${netcdf:variable:latitude:min}",
                "max": "${netcdf:variable:latitude:max}",
                "resolution": "${netcdf:variable:latitude:resolution}",
                "gridOrder": 1
            },
            "Lon": {
                "min": "${netcdf:variable:longitude:min}",
                "max": "${netcdf:variable:longitude:max}",
                "resolution": "${netcdf:variable:longitude:resolution}",
                "gridOrder": 2
            }
        }

        # Build recipe
        recipe = {
            "name": "general_coverage",
            "options": {
                "tiling": "ALIGNED [0:0, 0:1023, 0:1023] TILE SIZE 4000000",
                "coverage": {
                    "crs": "OGC:AnsiDate+EPSG:4326",
                    "metadata": {
                        "type": "xml",
                        "global": {}
                    },
                    "slicer": {
                        "type": "netcdf",
                        "pixelIsPoint": True,
                        "bands": [
                            {
                                "name": var.title(),
                                "identifier": var,
                                "variable": var
                            } for var in variables
                        ],
                        "axes": axes
                    }
                }
            }
        }

        # Initialize recipe
        ingredients = {
            "config": config,
            "input": inputs,
            "recipe": recipe
        }

        return ingredients


if __name__ == "__main__":
    path = str(SAMPLE)
    collection = None
    mock = False
    self = Importer()
    self.load(path, mock=False)
