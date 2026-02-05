#!/bin/bash
#
# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).
#
# Jobscript to analyze the results of one or more WRF runs.

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=00:30:00

echo "Running analyse-results.job script"
