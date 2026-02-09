#!/bin/bash
#
# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).
#
# Jobscript to analyze the results of one or more WRF runs.
#
# For documentation, run:
#
# ./analyse-results.job --help
#
# (or look at the variable ${docstring} below).

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=00:30:00

echo "Running analyse-results.job script"

docstring=$(cat <<'EOF'
This script runs our default analysis on one or more WRF-Chem simulations.

This script is intended to be used on the directory produced by the
script plot-vertical-profiles.py.

Options:

--help
    Prints this docstring and exits without error.

--work-dir (mandatory)
    The directory where the outputs of the simulations are. This directory must
    contain sub-directories such as:

     - outputs_1/wrf_...
     - outputs_2/wrf_...

--simulations (default=all)
    Either the keyword "all" or a comma-separated list of simulation numbers
    to analyse (for example 1,2,4 for the first, second, and fourth
    simulations).

EOF
)

# Process command-line arguments

for ((i = 1; i <= $#; i++)); do
    arg=${!i}
    if [[ "${arg}" == "--help" ]]; then
        echo -e "\n${docstring}\n"
        exit 0
    fi
done
