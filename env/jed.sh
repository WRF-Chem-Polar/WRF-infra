#!/bin/sh
#
# Copyright (c) 2025 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).
#
# Environment for WRF on Jed (EPFL HPC server).
#
# This file is meant to be sourced, not executed.
#

module purge

# --- loading flex library
ml flex/2.6.1-y4a5vd2
export FLEX_LIB_DIR="/ssoft/spack/pinot-noir/jed/v2/spack/opt/spack/linux-rhel9-x86_64_v3/gcc-11.4.1/flex-2.6.1-y4a5vd2zgmnkdott7mvp6ogiv56khlw3/lib/"

# --- loading gcc and openmpi
module load gcc/13.2.0
module load openmpi/5.0.3

# loading the netcedf-fortran set of modules (custom installation)
export MODULEPATH=$MODULEPATH:/work/eerl/apdasilv/wrf-chem-polar/software/libraries/gcc-v13.2.0/module_files
module --ignore_cache load zlib-v1.3.1.module
module --ignore_cache load hdf5-v1.14.6_zlib-v1.3.1.module
module --ignore_cache load netcdf-fortran-v4.6.2_netcdf-c-v4.9.3_hdf5-v1.14.6_zlib-v1.3.1.module


conda_run="/work/eerl/apdasilv/wrf-chem-polar/software/micromamba/micromamba
           run
           --root-prefix=/work/eerl/apdasilv/wrf-chem-polar/software/conda-envs/shared
           --name=WRF-Chem-Polar"
