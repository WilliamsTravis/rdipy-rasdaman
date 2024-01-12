# -*- coding: utf-8 -*-
"""Core rasdaman/rasdapy database access methods.

Author: travis
Date: Wed Nov 22 07:31:27 PM MST 2023
"""
import json
import os
import subprocess as sp

from pathlib import Path

import requests
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
POSSIBLE_DIMS = {
        "latitude": ["y", "ylat", "latitude", "lat"],
        "longitude": ["x", "xlon", "xlong", "longitude", "lon", "long"],
        "time": ["time", "day", "date"]
}


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
        # Drop collection from RASBASE
        query = f"drop collection {collection}"
        out = self.drop(query)

        # Check if collection exists as a geo coverage in SECORE
        host = "http://localhost:8080/rasdaman/admin/coverage"
        query = f"{host}/exist?coverageId={collection}"
        out = requests.request(
            url=query,
            method="GET",
            auth=("rasadmin", "rasadmin"),
            timeout=15
        )
        cov_exists = json.loads(out.content.decode())

        # Drop coverage from petascope
        if cov_exists:
            query = ("http://localhost:8080/rasdaman/ows/?"
                     "SERVICE=WCS&VERSION=2.0.1&REQUEST=DeleteCoverage&"
                     f"COVERAGEID={collection}")
            out = requests.request(
                url=query,
                method="POST",
                auth=("rasadmin", "rasadmin"),
                timeout=15
            )
            
        return out

    def list(self, pattern=None):
        """List collections in db.

        Parameters
        ----------
        pattern : str
            Pattern in collection names used to filter the list of collections
            returned. Defaults to None.

        Returns
        -------
        list : List of items, with the type depending on user arguments.
        """
        out = self.qe.execute_read(
            "select c from RAS_COLLECTIONNAMES as c"
        )
        collections = out.data
        if pattern:
            collections = [col for col in collections if pattern in col]
        return collections

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

    def _find_nc_dim(self, path, dim="latitude"):
        """Find the dataset string associated with a given dimension."""
        # Open dataset and try to infer what the dim is
        candidates = []
        with xr.open_dataset(path) as ds:
            possible = POSSIBLE_DIMS[dim]
            available = list(ds.dims)
            for avail in available:
                if any(p for p in possible if p.startswith(avail)):
                    candidates.append(avail)

        # If nothing is found, alert user
        if len(candidates) != 1:
            raise KeyError(
                f"Could not find a possible {dim} fields. Please rename "
                "field to {dim} and try again."
            )

        return candidates[0]

    def get_driver(self, path):
        """Return the appropriate driver for a file (must be GDAL-compatible).

        Parameters
        ----------
        path : str | pathlib.PosixPathtif
        -------
        str : A string representation of the driver appropriate to this file.
        """
        obj = gdal.Open(str(path))
        driver = obj.GetDriver().LongName
        return driver

    def get_crs(self, path):
        """Return the appropriate CRS ingredient string for a file."""
        # ds = xr.open_dataset(path)
        return "crs"

    def help(self):
        """Print help text for wcst import method."""
        sp.run([self.wcst_import, "--help"], shell=False,
               executable="/bin/bash", check=True)

    def load(self, path, variable=None, mock=False):
        """Import file into Rasdaman database.

        Parameters
        ----------
        path : str | PosixPath
            Path to file to load into Rasdaman.
        variable : str
            String representing variable in `path` to be uploaded. If None,
            this will attempt to load all available datasets.
        mock : bool
            If true, no data will be loaded, the process will only be
            checked for validity.
        """
        # Check if georeferencing information is available
        crs = self.get_crs(path)
        if crs:
            # Write temporary ingredients file
            dst = Path("./tmp_ingredients.json").absolute()
            ingredients = self.make_ingredients(path, variable, mock=mock)
            with open(dst, "w", encoding="utf-8") as file:
                file.write(json.dumps(ingredients, indent=4))

            # Call the import wcst script
            _ = sp.run(
                f"{str(self.wcst_import)} {dst} --identity-file ~/.rasdaman",
                shell=True,
                check=False,
                executable="/bin/bash"
            )
            os.remove(dst)

        else:
            # No need to try and georeference this
            print(f"No CRS object found in {path}, uploading native "
                  "geometries...")
            raise NotImplementedError("I haven't built non-georeferenced "
                                      "netcdfs into the load method yet.")

    def make_ingredients(self, path, variable, mock=False):
        """Make an ingredients JSON for a file.

        Parameters
        ----------
        path : str | PosixPath
            Path to file to load into Rasdaman.
        variable : str
            String representing variable in `path` to be uploaded.
        mock : bool
            If true, no data will be loaded, the process will only be
            checked for validity.
        """
        driver = self.get_driver(path)
        if driver == "Network Common Data Format":
            ingredients = self._ingredients_nc(path, variable, mock=mock)
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
        collection = f"{path.stem}".replace("-", "_")

        # Create a collection
        # if collection not in self.collections:
        #     query = f"create collection {collection} FloatSet3"
        #     self.write(query)

        # Retrieve information from file
        time_var = self._find_nc_dim(path, "time")
        lon_var = self._find_nc_dim(path, "longitude")
        lat_var = self._find_nc_dim(path, "latitude")

        # For now, build the time index explicitly
        with xr.open_dataset(path, decode_times=True) as ds:
            if not variable:
                variables = [v for v in ds if v != "crs"]
            else:
                variables = [variable]
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

        # Get the appropriate time recipe
        time_key, time_recipe = self._time_recipe(time)

        # Define axes
        axes = {
            time_key: time_recipe,
            "Lat": {
                "min": f"${{netcdf:variable:{lat_var}:min}}",
                "max": f"${{netcdf:variable:{lat_var}:max}}",
                "resolution": f"${{netcdf:variable:{lat_var}:resolution}}",
                "gridOrder": 1,
                "crsOrder": 1,
            },
            "Lon": {
                "min": f"${{netcdf:variable:{lon_var}:min}}",
                "max": f"${{netcdf:variable:{lon_var}:max}}",
                "resolution": f"${{netcdf:variable:{lon_var}:resolution}}",
                "gridOrder": 2,
                "crsOrder": 2
                
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

    def _time_recipe(self, time):
        """Return the appropriate time recipe for the ingredients file."""
        key = "ansi"
        recipe = {
            "min": time[0],
            "max": time[-1],
            "directPositions": str(list(time)),
            "irregular": True,
            "resolution": "1",
            "gridOrder": 0,
            "crsOrder": 0,
            "type": "ansidate"
        }

        return key, recipe
