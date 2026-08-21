# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Create the variable EROD_HL in wrfinput file.

This variable contains the S-function/dust erodibility data including high-latitude sources,
to use instead of the EROD variable.

"""

# -------- Imports --------
import numpy as np
import os
import sys
from netCDF4 import Dataset
from hldust_utilities import get_wrf_proj, calc_wrf_grid_edges
from hldust_create_cdo_wrfgridfile import create_cdo_wrfgridfile
import subprocess


wrfinput_src = sys.argv[1]
erodfile = "/proju/wrf-chem/input-data/natural_emissions/terrestrial/dust/sfunc_0_1deg.nc"


# -------- Initialize --------
# ---- Open WRF grid
wrf_proj = get_wrf_proj(wrfinput_src)

# Define land points
with Dataset(wrfinput_src) as ncfile:
    ncfile.set_auto_mask(False)
    wrf_xland = np.squeeze(ncfile.variables["XLAND"][:])
    wrf_xice = np.squeeze(ncfile.variables["SEAICE"][:])

# Include sea ice as ocean, not land
wrf_xland[wrf_xice > 0.0] = 2.0

# Calculate WRF grid edges
wrf_lat_edge, wrf_lon_edge = calc_wrf_grid_edges(wrf_proj)
minlat = np.min(wrf_lat_edge) - 1.0
maxlat = np.max(wrf_lat_edge) + 1.0
minlon = np.min(wrf_lon_edge) - 1.0
maxlon = np.max(wrf_lon_edge) + 1.0
if minlat < -85:
    minlat = -90
if maxlat > 85:
    maxlat = 90
if minlon < -175:
    minlon = -180
if maxlon > 175:
    maxlon = 180

# ---- CDO conservative regridding of erodibility to WRF grid
cdo_wrfgrid_file = os.path.join(
    os.path.dirname(wrfinput_src), "cdo_wrfgrid.txt"
)
erodfile_regrid = f"{wrfinput_src}_erod"
for file in (cdo_wrfgrid_file, erodfile_regrid):
    try:
        os.remove(file)
    except FileNotFoundError:
        pass

create_cdo_wrfgridfile(wrfinput_src)
# Extract subset
cmd = [
    "cdo",
    f"sellonlatbox,{minlon},{maxlon},{minlat},{maxlat}",
    erodfile,
    "ERODFILE_subset.nc",
]
print(f"Extract subset from {erodfile}:", " ".join(cmd))
if subprocess.run(cmd).returncode:
    msg = "CDO sellonlatbox command failed."
    raise RuntimeError(msg)
# Regrid
cmd = [
    "cdo",
    f"remapcon,{cdo_wrfgrid_file}",
    "ERODFILE_subset.nc",
    erodfile_regrid,
]
print("Regrid file to WRF grid:", " ".join(cmd))
if subprocess.run(cmd).returncode:
    msg = "CDO remapcon command failed."
    raise RuntimeError(msg)

# ---- Write regridded data to wrfinput file
# Open the erodibility data from the regridded file
print("Open regridded erodibility data")
with Dataset(erodfile_regrid) as ncfile:
    erod_regrid = ncfile.variables["sfunc"][:]
wrf_erod = np.copy(erod_regrid)
# Remove invalid data
wrf_erod[wrf_xland > 1.5] = 0
wrf_erod[wrf_erod > 1] = 1
wrf_erod[wrf_erod < 0] = 0
# Write to wrfinput
print(f"Write new erodibility data to {wrfinput_src}")
with Dataset(wrfinput_src, "a") as ncfile:
    ncfile.variables["EROD_HL"][0, :, :] = wrf_erod[:, :]
# Delete temporary files
for file in (erodfile_regrid, cdo_wrfgrid_file, "ERODFILE_subset.nc"):
    try:
        os.remove(file)
    except FileNotFoundError:
        pass
