#!/bin/sh
#
# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).
#
# Environment for WRF on Jean Zay.
#
# This file is meant to be sourced, not executed.
#

module purge
module load gcc/13.3.0
module load flex/2.6.4
module load openmpi/4.1.8
module load netcdf-c/4.7.4-mpi
module load netcdf-fortran/4.5.3-mpi
module load git/2.53.0

# Variables required at compile-time
export YACC="bison -d"
export FLEX_LIB_DIR=$(dirname $(dirname $(which flex)))/lib
