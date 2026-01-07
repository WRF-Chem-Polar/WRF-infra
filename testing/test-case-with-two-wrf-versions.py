# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Run and compare the results of the test case for two versions of WRF."""

import argparse
import os

parser = argparse.ArgumentParser(
    description="Run and compare test case for two versions of WRF.",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "--wrf-commit-1",
    help="First Git commit to use for WRF (any valid Git reference).",
    default="HEAD~1",
)
parser.add_argument(
    "--wrf-commit-2",
    help="Second Git commit to use for WRF (any valid Git reference).",
    default="HEAD",
)
parser.add_argument(
    "--wps-commit",
    help="Git commit to use for WPS (any valid Git reference).",
    default="4.6.0",
)
parser.add_argument(
    "--work-dir",
    help="Work directory (must not already exist).",
    default=os.path.join(os.getcwd(), os.path.basename(__file__)[:-3]),
)
args = parser.parse_args()
