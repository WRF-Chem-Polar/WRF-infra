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
    return matches[0].split()[-1]


parser = argparse.ArgumentParser(
    description="Run and compare test case for two versions of WRF.",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "--wps-commit",
    help="Git commit to use for WPS (any valid Git reference).",
    default="v4.6.0",
)
parser.add_argument(
    "--wrf-commits",
    help=(
        "Git commits to use for WRF (comma-separated list of valid Git "
        "references)."
    ),
    default="HEAD,HEAD~1",
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
parser.add_argument(
    "--python",
    help="Python command (useful to use a non-default installation).",
    default="python",
)
args = parser.parse_args()
wrf_commits = [commit.strip() for commit in args.wrf_commits.split(",")]

# Prepare the work directory
if os.path.lexists(args.work_dir):
    raise RuntimeError("Work directory already exists.")
commons.run(["mkdir", "-v", "-p", args.work_dir])

job_ids = dict()
for i, wrf_commit in enumerate(wrf_commits, start=1):
    print(f"\nProcessing commit {i}: {wrf_commit}...")

    # Install WRF
    dir_wrf = os.path.join(args.work_dir, f"WRF_{i}")
    cmd_wrf = [
        args.python,
        os.path.join(commons.path_of_repo(), "compile", "compile_WRF.py"),
        "--repository",
        args.wrf_repository,
        "--commit",
        wrf_commit,
        "--destination",
        dir_wrf,
        "--git",
        args.git,
    ]
    last_job = f"Install WRF {i}"
    job_ids[last_job] = get_job_id(commons.run_stdout(cmd_wrf))

    # Prepare WPS installation
    dir_wps = os.path.join(args.work_dir, f"WPS_{i}")
    cmd_wps = [
        args.python,
        os.path.join(commons.path_of_repo(), "compile", "compile_WPS.py"),
        "--repository",
        args.wps_repository,
        "--commit",
        args.wps_commit,
        "--destination",
        dir_wps,
        "--wrfdir",
        dir_wrf,
        "--git",
        args.git,
        "--dry",
        "yes",
    ]
    commons.run(cmd_wps)

    # Install WPS
    cmd_wps = ["sbatch", "-d", f"afterok:{job_ids[last_job]}", "compile.job"]
    last_job = f"Install WPS {i}"
    job_ids[last_job] = get_job_id(commons.run_stdout(cmd_wps, cwd=dir_wps))

    # TODO: change the scratch and output directory in simulation.conf

    # Run all model components
    for job in ["WPS", "real", "WRF-Chem"]:
        dir_run = os.path.join(commons.path_of_repo(), "run", job)
        jobscript = f"jobscript_{job.lower().replace('-', '')}.sh"
        cmd_run = [
            "sbatch",
            "-d",
            f"afterok:{job_ids[last_job]}",
            os.path.join(dir_run, jobscript),
        ]
        stdout = commons.run_stdout(cmd_run, cwd=dir_run)
        last_job = f"Run {job} {i}"
        job_ids[last_job] = get_job_id(stdout)

# Launch the job to analyze the results of the simulation
dependencies = ",".join(f"afterok:{job_id}" for job_id in job_ids.values())
dir_job = os.path.join(commons.path_of_repo(), "testing")
cmd_run = ["sbatch", "-d", dependencies, "analyse-results.job"]
last_job = "Analyze results"
job_ids[last_job] = get_job_id(commons.run_stdout(cmd_run, cwd=dir_job))

# Some verbose
print("\nSummary of job IDs:")
for key, value in job_ids.items():
    print(f"    {key}: {value}")
