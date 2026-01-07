# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Run and compare the results of the test case for two versions of WRF."""

import argparse
import os
import re
import commons


def get_job_id(stdout):
    """Get the ID of the job that has just been sent to the queue.

    Parameters
    ----------
    stdout: [str]
        The standard output (one string per line) of the command or script that
        sent the job to the queue. This text can contain other output, as long
        as there is a single line among it that corresponds to the output of
        the scheduler adding the job to the queue.

    Returns
    -------
    str
        The job ID of the job that has just been sent to the queue.

    """
    matches = [
        line
        for line in stdout
        if re.fullmatch("Submitted batch job [0-9]+", line) is not None
    ]
    if len(matches) != 1:
        raise RuntimeError("Could not determine unique job ID.")
    return matches[0].split[-1]


parser = argparse.ArgumentParser(
    description="Run and compare test case for two versions of WRF.",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "--wps-commit",
    help="Git commit to use for WPS (any valid Git reference).",
    default="4.6.0",
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
    "--work-dir",
    help="Work directory (must not already exist).",
    default=os.path.join(os.getcwd(), os.path.basename(__file__)[:-3]),
)
parser.add_argument(
    "--wps-repository",
    help="URL of the WPS repository (remote or local).",
    default=commons.URL_WPS,
)
parser.add_argument(
    "--wrf-repository",
    help="URL of the WRF repository (remote or local).",
    default=commons.URL_WRFCHEMPOLAR,
)
parser.add_argument(
    "--git",
    help="Git command (useful to use a non-default installation).",
    default="git",
)
args = parser.parse_args()

if os.path.lexists(args.work_dir):
    raise RuntimeError("Work directory already exists.")
commons.run(["mkdir", "-v", "-p", args.work_dir])

# Install first version of WRF
dir_compile = os.path.join(commons.path_of_repo(), "compile")
cmd_wrf = [
    os.path.join(dir_compile, "compile_WRF.py"),
    "--repository",
    args.wrf_repository,
    "--git",
    args.git,
]
dir_wrf = os.path.join(args.work_dir, "WRF_1")
stdout = commons.run_stdout(
    cmd_wrf + ["--destination", dir_wrf, "--commit", args.wrf_commit_1]
)
jobid_wrf_1 = get_job_id(stdout)

# Install second version of WRF
dir_wrf = os.path.join(args.work_dir, "WRF_2")
stdout = commons.run_stdout(
    cmd_wrf + ["--destination", dir_wrf, "--commit", args.wrf_commit_2]
)
jobid_wrf_2 = get_job_id(stdout)
