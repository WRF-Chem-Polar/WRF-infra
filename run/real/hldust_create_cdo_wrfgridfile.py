# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Create WRF grid file for the CDO remapcon operator, i.e. cdo_wrfgrid.txt in:

   cdo remapcon,cdo_wrfgrid.txt input.nc output.nc

"""

# Imports
# -------
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
    print("Create CDO WRF grid file for remapcon")
    cdo_wrfgrid_file = os.path.dirname(WRFOUT_DOMAIN_FILE) + "/cdo_wrfgrid.txt"
    if os.path.isfile(cdo_wrfgrid_file):
        os.remove(cdo_wrfgrid_file)
    with open(cdo_wrfgrid_file, "a") as file:
        file.write(
            "# WRF grid for CDO remapcon, from file "
            + WRFOUT_DOMAIN_FILE
            + "\n"
        )
        file.write("gridtype  = curvilinear\n")
        file.write(
            "gridsize  = " + str((wrf_proj.imax) * (wrf_proj.jmax)) + "\n"
        )
        file.write("xsize     = " + str(wrf_proj.imax) + "\n")
        file.write("ysize     = " + str(wrf_proj.jmax) + "\n")
        # Write xvals (lon)
        valindex = 0
        file.write("xvals     =  ")
        for jj in range(wrf_proj.jmax):
            for ii in range(wrf_proj.imax):
                wrf_lon_str = "{:.5f}".format(wrf_xlong[jj, ii])
                file.write(wrf_lon_str + "  ")
                valindex = valindex + 1
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
                wrflon_ll_str = "{:.5f}".format(wrflon_ll[0])
                wrflon_lr_str = "{:.5f}".format(wrflon_lr[0])
                wrflon_ul_str = "{:.5f}".format(wrflon_ul[0])
                wrflon_ur_str = "{:.5f}".format(wrflon_ur[0])
                file.write(
                    wrflon_lr_str
                    + " "
                    + wrflon_ur_str
                    + " "
                    + wrflon_ul_str
                    + " "
                    + wrflon_ll_str
                )
                valindex = valindex + 1
                if valindex == 1:
                    file.write("\n             ")
                    valindex = 0
        # Write yvals (lat)
        valindex = 0
        file.write("yvals     =  ")
        for jj in range(wrf_proj.jmax):
            for ii in range(wrf_proj.imax):
                wrf_lat_str = "{:.5f}".format(wrf_xlat[jj, ii])
                file.write(wrf_lat_str + "  ")
                valindex = valindex + 1
                if (ii == wrf_proj.imax) and (jj == wrf_proj.jmax):
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
                wrflat_ll_str = "{:.5f}".format(wrflat_ll[0])
                wrflat_lr_str = "{:.5f}".format(wrflat_lr[0])
                wrflat_ul_str = "{:.5f}".format(wrflat_ul[0])
                wrflat_ur_str = "{:.5f}".format(wrflat_ur[0])
                file.write(
                    wrflat_lr_str
                    + " "
                    + wrflat_ur_str
                    + " "
                    + wrflat_ul_str
                    + " "
                    + wrflat_ll_str
                )
                valindex = valindex + 1
                if valindex == 1:
                    file.write("\n             ")
                    valindex = 0
