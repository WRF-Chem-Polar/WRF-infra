#!/bin/sh
#
# Copyright (c) 2025 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).
#
# Environment for WRF on Spirit.
#
# This file is meant to be sourced, not executed.
#

version_gcc=$(gcc --version | head -n 1 | awk '{print $NF}')
version_gfortran=$(gfortran --version | head -n 1 | awk '{print $NF}')
if [[ "$version_gcc" != "$version_gfortran" ]]; then
    echo "Error: GCC and GFORTRAN versions mismatch."
    exit 1
fi
dir_libs=/proju/wrf-chem/software/libraries
which_netcdf=netcdf-fortran-v4.6.2_netcdf-c-v4.9.3_hdf5-v1.14.6_zlib-v1.3.1.module

module purge
module load ${dir_libs}/gcc-v${version_gcc}/${which_netcdf}

unset version_gcc
unset version_gfortran
unset dir_libs
unset which_netcdf
