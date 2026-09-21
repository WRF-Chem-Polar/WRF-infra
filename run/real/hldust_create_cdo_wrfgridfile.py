# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Create WRF grid file for the CDO remapcon operator, i.e. cdo_wrfgrid.txt in:

cdo remapcon,cdo_wrfgrid.txt input.nc output.nc

"""

import numpy as np
import os
import math
import pandas as pd
from netCDF4 import Dataset
import glob
import re
from hldust_utilities import get_wrf_proj, wrf_ijll


def create_cdo_wrfgridfile(wrfout_domain_file):
    """Create WRF grid file for the CDO remapcon operator.

    This function creates a file named cdo_wrfgrid.txt in the same directory
    as the input file. The created file can be used as the grid file when using
    the CDO remapcon operator, for instance:

    cdo remapcon,cdo_wrfgrid.txt input.nc output.nc

    Parameters
    ----------
    wrfout_domain_file: str
        Path to the wrfout file.

    """

    # Get grid information
    with Dataset(wrfout_domain_file) as ncfile:
        if "XLAT" in ncfile.variables:
            wrf_xlat = np.squeeze(ncfile.variables["XLAT"][:])
        else:
            wrf_xlat = np.squeeze(ncfile.variables["XLAT_M"][:])
        if "XLONG" in ncfile.variables:
            wrf_xlong = np.squeeze(ncfile.variables["XLONG"][:])
        else:
            wrf_xlong = np.squeeze(ncfile.variables["XLONG_M"][:])
    wrf_proj = get_wrf_proj(wrfout_domain_file)

    # Create WRF grid description file for CDO conservative regridding
    cdo_wrfgrid_file = os.path.join(
        os.path.dirname(wrfout_domain_file), "cdo_wrfgrid.txt"
    )
    with open(cdo_wrfgrid_file, mode="w") as file:
        file.write(
            f"# WRF grid for CDO remapcon, from file {wrfout_domain_file}\n"
        )
        file.write("gridtype  = curvilinear\n")
        file.write(f"gridsize = {wrf_proj.imax * wrf_proj.jmax}\n")
        file.write(f"xsize    = {wrf_proj.imax}\n")
        file.write(f"ysize    = {wrf_proj.jmax}\n")
        # Write xvals (lon)
        valindex = 0
        file.write("xvals     =  ")
        for jj in range(wrf_proj.jmax):
            for ii in range(wrf_proj.imax):
                file.write(f"{wrf_xlong[jj, ii]:.5f}  ")
                valindex += 1
                if valindex == 10:
                    file.write("\n             ")
                    valindex = 0
        # Write xbounds (lon of cell corners)
        valindex = 0
        file.write("\nxbounds   =  ")
        for jj in range(wrf_proj.jmax):
            for ii in range(wrf_proj.imax):
                wrflat_ll, wrflon_ll = wrf_ijll(
                    [ii + 1 - 0.5], [jj + 1 - 0.5], wrf_proj
                )
                wrflat_lr, wrflon_lr = wrf_ijll(
                    [ii + 1 + 0.5], [jj + 1 - 0.5], wrf_proj
                )
                wrflat_ul, wrflon_ul = wrf_ijll(
                    [ii + 1 - 0.5], [jj + 1 + 0.5], wrf_proj
                )
                wrflat_ur, wrflon_ur = wrf_ijll(
                    [ii + 1 + 0.5], [jj + 1 + 0.5], wrf_proj
                )
                file.write(
                    f"{wrflon_lr[0]:.5f} {wrflon_ur[0]:.5f} "
                    f"{wrflon_ul[0]:.5f} {wrflon_ll[0]:.5f}"
                )
                valindex += 1
                if valindex == 1:
                    file.write("\n             ")
                    valindex = 0
        # Write yvals (lat)
        valindex = 0
        file.write("yvals     =  ")
        for jj in range(wrf_proj.jmax):
            for ii in range(wrf_proj.imax):
                file.write(f"{wrf_xlat[jj, ii]:.5f}  ")
                valindex += 1
                if ii == wrf_proj.imax and jj == wrf_proj.jmax:
                    file.write("\n")
                    valindex = 0
                elif valindex == 10:
                    file.write("\n             ")
                    valindex = 0
        # Write ybounds (lat of cell corners)
        valindex = 0
        file.write("\nybounds   =  ")
        for jj in range(wrf_proj.jmax):
            for ii in range(wrf_proj.imax):
                wrflat_ll, wrflon_ll = wrf_ijll(
                    [ii + 1 - 0.5], [jj + 1 - 0.5], wrf_proj
                )
                wrflat_lr, wrflon_lr = wrf_ijll(
                    [ii + 1 + 0.5], [jj + 1 - 0.5], wrf_proj
                )
                wrflat_ul, wrflon_ul = wrf_ijll(
                    [ii + 1 - 0.5], [jj + 1 + 0.5], wrf_proj
                )
                wrflat_ur, wrflon_ur = wrf_ijll(
                    [ii + 1 + 0.5], [jj + 1 + 0.5], wrf_proj
                )
                file.write(
                    f"{wrflat_lr[0]:.5f} {wrflat_ur[0]:.5f} "
                    f"{wrflat_ul[0]:.5f} {wrflat_ll[0]:.5f}"
                )
                valindex += 1
                if valindex == 1:
                    file.write("\n             ")
                    valindex = 0
