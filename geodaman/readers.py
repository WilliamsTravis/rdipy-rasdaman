# -*- coding: utf-8 -*-
"""Dataset readers

Currently trying to get this command to work:

rasql -q 'insert into test_spei6 decode($1, "netcdf", "{ \"formatParameters\": { \"variables\": \"[ \"index\" ]\")' --file ./test.nc --mddtype FloatCube --mddtype float --user rasadmin --passwd rasadmin

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

from geodaman import GEODAMAN_DIR


RMANHOME = os.getenv("RMANHOME")
DATA_DIR = GEODAMAN_DIR.joinpath("data")
SAMPLE = "/home/travis/scratch/rasdaman/sresa1b_ncar_ccsm3-example.nc"
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


class RasdamanQueryError(Exception):
    """"Errors from running with rasdapy.QueryExecutor."""


class RasdamanDropError(Exception):
    """"Errors from dropping objects with rasdapy.QueryExecutor."""


class Importer:
    """Methods for building WCST recipes for importing data."""

    def __init__(self):
        """Initialize Importer object."""
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
        with xr.open_dataset(path) as ds:
            epsg = ds["crs"].attrs["spatial_ref"]
        code = epsg.split(":")[-1]
        crs = f"EPSG/0/{code}@OGC/0/AnsiDate"
        return crs

    def help(self):
        """Print help text for wcst import method."""
        sp.run([self.wcst_import, "--help"], shell=False,
               executable="/bin/bash", check=True)

    def load(self, path):
        """Import file into Rasdaman database."""
        # Write temporary ingredients file
        dst = "./tmp_ingredients.json"
        ingredients = self.make_ingredients(path)
        with open(dst, "w", encoding="utf-8") as file:
            file.write(json.dumps(ingredients, indent=4))

        # Call the import wcst script
        out = sp.run(f"{str(self.wcst_import)} {dst}", shell=True, check=False,
                     executable="/bin/bash")

    def make_ingredients(self, path):
        """Make an ingredients JSON for a file."""
        driver = self.get_driver(path)
        if driver == "Network Common Data Format":
            ingredients = self._ingredients_nc(path)
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

    def _ingredients_nc(self, path):
        """Create an ingedients JSON for a NetCDF file."""
        # Make sure this path is a Posix path
        path = Path(path)
        tag = path.stem
        ds = xr.open_dataset(path)
        res = float(abs(ds["lat"][0] - ds["lat"][1]))

        # Build initial config
        config = {
            "service_url": "http://localhost:8080/rasdaman/ows",
            "tmp_directory": "/tmp/",
            "crs_resolver": "http://localhost:8080/def/",
            "default_crs": "http://localhost:8080/def/OGC/0/Index2D",
            "mock": False,
            "automated": False,  # Human input required, turn on to avoid
            "track_files": False,
            "subset_correction": False
        }

        # Build initial input
        inputs = {
            "coverage_id": tag,
            "paths": [str(path)]
        }

        # Define axes
        axes = {
            "time": {
                "min": "datetime(${netcdf:variable:time:min} * 24 * 3600)",
                "max": "datetime(${netcdf:variable:time:max} * 24 * 3600)",
                "resolution": 1,
                "gridOrder": 0,
                "type": "ansidate",
                "irregular": True
            },
            "lat": {
                "min": str(float(ds["lat"].min())),
                "max": str(float(ds["lat"].max())),
                "gridOrder": 1,
                "resolution": res
            },
            "lon": {
                "min": str(float(ds["lon"].min())),
                "max": str(float(ds["lon"].max())),
                "gridOrder": 2,
                "resolution": res
            }
        }

        # Build recipe
        recipe = {
            "name": "time_series_regular",
            "options": {
                "time_start": "2000-05-16T12:00:00",
                "time_format": "auto",
                "time_crs": "http://localhost:8080/def/crs/OGC/0/AnsiDate",
                "time_step": "30 days 0 minutes 0 seconds",
                "tiling": "ALIGNED [0:2, 0:100, 0:100]",
                "coverage": {
                    "slicer": {
                        "type": "netcdf",
                        "bands": [
                            {
                                "name": "spei6_20yr",
                                "variable": "index",
                                "indentifier": "index"
                            }
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


class RDBC(Importer):
    """Rasdaman Database Control object."""

    def __init__(self):
        """Initialize an RDBC object."""
        super().__init__()
        self.db = DBConnector("localhost", 7001, "rasadmin", "rasadmin")
        self.qe = QueryExecutor(self.db)
        self.db.open()

    def __enter__(self):
        """Open database conection with context management."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close database connection with context management."""
        self.db.close()

    def __repr__(self):
        """Return an RDBC object representation string."""
        address = hex(id(self))
        name = self.__class__.__name__
        msgs = [f"\n   {k}={v}" for k, v in self.__dict__.items()]
        msg = ", ".join(msgs)
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
        q : str
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

    def drop_collection(self, collection):
        """Drop collection from database."""
        query = f"drop collection {collection}"
        out = self.drop(query)
        return out

    def insert_file(self, path, collection=None):
        """Insert a file into to a database with a query.

        Parameters
        ----------
        q : str
            String representation of database SQL query.
        path : str
            Path to file insert into object.
        collection : str
            Name of collection to insert `file` into. If no collection is given
            a new collection specific to the data in this file will be created.

        Returns
        -------
        rasdapy.query_result.QueryResult : A rasdapy output object.
        """
        # Get the appropriate driver for this file
        driver = self.get_driver(path)

        # Use the appropriate method to insert file
        if driver == "GeoTIFF":
            out = self._insert_tiff(path, collection)
        else:
            raise NotImplementedError(f"{driver} driver not implemented yet.")


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

    def read(self, q):
        """Read data from the database with a query.

        Parameters
        ----------
        q : str
            String representation of database SQL query.

        Returns
        -------
        rasdapy.query_result.QueryResult : A rasdapy output object.
        """
        out = self.qe.execute_read(q)
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

    def write(self, q):
        """Write items to a database with a query.

        Parameters
        ----------
        q : str
            String representation of database SQL query.

        Returns
        -------
        rasdapy.query_result.QueryResult : A rasdapy output object.
        """
        out = self.qe.execute_write(q)
        if "with_error" in out.__dict__:
            if out.with_error:
                msg = out.error_message()
                raise RasdamanQueryError(f"Write Error: {msg}")
        return out

    def _get_tiff_types(self, path):
        """Return a a dictionary of data types associated with a GeoTiff."""
        # Open data set and get the first band
        path = str(path)
        ds = gdal.Open(path)
        band = ds.GetRasterBand(1)

        # Get the base type
        gdaltype = gdal.GetDataTypeName(band.DataType)
        basetype = TYPE_MAP[gdaltype]

        # Get MDArray type
        mdtypes = [t for t in self.types["RAS_MARRAY_TYPES"] if basetype in t]
        bands = ds.RasterCount
        if bands > 1:
            mdtype = [t for t in mdtypes if "Cube4" in t][0]
        else:
            md
        return types

    def _insert_tiff(self, path, collection=None, overwrite=True):
        """Insert a GeoTIFF into the database."""
        # Get the data types appropriate for the data in this file
        dtypes = self._get_tiff_types(path)
        path = Path(path)

        # Create collection if needed
        if not collection:e = [t for t in settypes if f"({mdtype})" in t][0]
        settype = settype.split()[2]

        # Collect types
        types = {
            "basetype": basetype,
            "mdtype": mdtype,
            "settype": settype
        }
        del ds

        return types

    def _insert_tiff(self, path, collection=None, overwrite=True):
        """Insert a GeoTIFF into the database."""
        # Get the data types appropriate for the data in this file
        dtypes = self._get_tiff_types(path)
        path = Path(path)

        # Create collection if needed
        if not collection:
            collection = path.stem
            if collection in self.collections:
                if overwrite:
                    self.drop_collection(collection)
                    query = f"create {collection} {dtypes['settype']}"
                    dtypes = self._get_tiff_types(path)
                    self.write(query)
                else:
                    raise RasdamanQueryError(
                        f"Cannot create new collection {collection} for {path}"
                        f", {collection} exists."
                    )

        query = f"insert into {collection} values decode($1)"
        path = str(path)
        out = self.qe.execute_update_from_file(query, path)
        if "with_error" in out.__dict__:
            if out.with_error:
                msg = out.error_message()
                raise RasdamanQueryError(f"Insert Error: {msg}")

        return out

    def _encode_ncvar(self, ds, name, coordinate=False, time=False):
        """Translate NetCDF4 variable into encoding entry."""
        if ds[name].dtype == "float32":
            dtype = "float"
        elif ds[name].dtype == "float64":
            dtype = "double"
        else:
            dtype = ds[name].dtype

        vattr = {
            "name": name,
            "metadata": ds[name].attrs,
            "dtype": dtype
        }

        if coordinate:
            vattr["data"] = list(ds[name].data)

        if name == "time":
            data = list(range(ds[name].data.shape[0]))
            vattr["data"] = data
            vattr["type"] = "int"

        return vattr


if __name__ == "__main__":
    path = str(SAMPLE)
    collection = None
    self = RDBC()
    self.load(path)
