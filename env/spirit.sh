#!/bin/sh
#
# Copyright (c) 2025-2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
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
module load netcdf-c/4.7.4-serial
module load netcdf-fortran/4.5.3-serial

cmd_python="/proju/wrf-chem/software/micromamba/micromamba
            run
            --root-prefix=/proju/wrf-chem/software/conda-envs/shared
            --name=WRF-Chem-Polar
            python"
