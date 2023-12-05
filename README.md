# geodaman Package

I am experimenting with Rasdaman and storing methods in this repository, though they're going somewhere else soon.

## A few notes to remember from the installation guide:
* The `/opt/rasdaman/data` directory is where Rasdaman stores array tiles and can become very large, so it is recommended that you link this path to a larger disk
* Log files here: `/opt/rasdaman/log`
* Populate the sample dataset with this: `/opt/rasdaman/bin/rasdaman_insertdemo.sh`
* rasmgr is the central rasdaman request dispatcher; clients connect to rasmgr initially and are then assigned to a specific rasserver process which will evaluate queries
* rasserver is the rasdaman server engine, it should not be generally invoked in a standalone manner
* rascontrol allows to interactively control the rasdaman server by communicating with rasmgr
* rasql is the command-line based query tool, explained in detail in the rasdaman Query Language Guide
