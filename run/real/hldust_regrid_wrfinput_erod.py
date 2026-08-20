# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

# Create the variavle EROD_HL containing the S-function/dust erodibility data
# including High-Latitude sources, to use instead of the EROD variable in
# wrfinput


# -------- Imports --------
import numpy as np
import os
import sys

# NetCDF file manipulation
from netCDF4 import Dataset

# WRF model handling
from wrf_utilities import get_wrf_proj, calc_wrf_grid_edges
from create_cdo_wrfgridfile import create_cdo_wrfgridfile


# -------- Input --------
WRFINPUT_SRC = sys.argv[1]


# -------- Parameters --------
ERODFILE = "/proju/wrf-chem/input-data/natural_emissions/terrestrial/dust/sfunc_0_1deg.nc"


# -------- Initialize --------
# ---- Open WRF grid
wrf_domain_file = WRFINPUT_SRC
wrf_proj = get_wrf_proj(wrf_domain_file)
with Dataset(wrf_domain_file) as ncfile:
    ncfile.set_auto_mask(False)
    wrf_xland = np.squeeze(ncfile.variables["XLAND"][:])
    wrf_xice = np.squeeze(ncfile.variables["SEAICE"][:])
wrf_xland[wrf_xice > 0.0] = 2.0
# Calculate WRF grid edges
wrf_lat_edge, wrf_lon_edge = calc_wrf_grid_edges(wrf_proj)
minlat = np.min(wrf_lat_edge) - 1.0
maxlat = np.max(wrf_lat_edge) + 1.0
minlon = np.min(wrf_lon_edge) - 1.0
maxlon = np.max(wrf_lon_edge) + 1.0
if minlat < -85.0:
    minlat = -90.0
if maxlat > 85.0:
    maxlat = 90.0
if minlon < -175.0:
    minlon = -180.0
if maxlon > 175.0:
    maxlon = 180.0

# ---- CDO conservative regridding of erodibility to WRF grid
cdo_wrfgrid_file = "{}/cdo_wrfgrid.txt".format(os.path.dirname(WRFINPUT_SRC))
erodfile_regrid = "{}_erod".format(WRFINPUT_SRC)
os.system('rm -f "{}"'.format(cdo_wrfgrid_file))
os.system('rm -f "{}"'.format(erodfile_regrid))

create_cdo_wrfgridfile(WRFINPUT_SRC)
# Extract subset
print("Extract subset from {}".format(ERODFILE))
print(
    "cdo sellonlatbox,{},{},{},{} {} ERODFILE_subset.nc".format(
        minlon, maxlon, minlat, maxlat, ERODFILE
    )
)
os.system(
    "cdo sellonlatbox,{},{},{},{} {} ERODFILE_subset.nc".format(
        minlon, maxlon, minlat, maxlat, ERODFILE
    )
)
# Regrid
print("Regrid file to WRF grid")
print(
    "cdo remapcon,{} ERODFILE_subset.nc {}".format(
        cdo_wrfgrid_file, erodfile_regrid
    )
)
error_code = os.system(
    "cdo remapcon,{} ERODFILE_subset.nc {}".format(
        cdo_wrfgrid_file, erodfile_regrid
    )
)

# ---- Write regridded data to wrfinput file
# Open the erodibility data from the regridded file
print("Open regridded erodibility data")
with Dataset(erodfile_regrid) as ncfile:
    erod_regrid = ncfile.variables["sfunc"][:]
wrf_erod = np.copy(erod_regrid)
# Remove invalid data
wrf_erod[wrf_xland > 1.5] = 0.0
wrf_erod[wrf_erod > 1.0] = 1.0
wrf_erod[wrf_erod < 0.0] = 0.0
# Write to wrfinput
print("Write new erodibility data to " + WRFINPUT_SRC)
# Create variable EROD_HL and metadata
with Dataset(WRFINPUT_SRC, "a") as ncfile:
    ncfile.variables["EROD_HL"][0, :, :] = wrf_erod[:, :]
# Delete temp files
os.system(
    'rm -f "{}" "{}" "ERODFILE_subset.nc"'.format(
        erodfile_regrid, cdo_wrfgrid_file
    )
)
