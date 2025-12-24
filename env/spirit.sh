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

module purge
module load gcc/11.2.0
module load openmpi/4.0.7
module load /proju/wrf-chem/software/libraries/gcc-v11.2.0/netcdf-fortran-v4.6.2_netcdf-c-v4.9.3_hdf5-v1.14.6_zlib-v1.3.1.module
