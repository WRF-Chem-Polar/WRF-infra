# Copyright (c) 2025-now LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Common Python resources for WRF-infra: resources for compilation."""

import os
import argparse
import json
from . import generic


def prepare_argparser(which):
    """Return the object that parses command-line arguments.

    Parameters
    ----------
    which: "WPS" | "WRF"
        Which model are we trying to compile here?

    Returns
    -------
    argparse.ArgumentParser
        The object that parses command-line arguments.

    """
    # "which"-dependent default values
    if which == "WPS":
        repository = generic.URL_WPS
        commit = "master"
        patches = os.path.join(
            generic.path_of_repo(), "compile", "patches", "WPS", "v4.6.0"
        )
    elif which == "WRF":
        repository = generic.URL_WRFCHEMPOLAR
        commit = "polar/main"
        patches = None
    else:
        msg = f"Invalid choice: {which}."
        raise RuntimeError(msg)

    # Common command-line arguments
    parser = argparse.ArgumentParser(
        description="Compile %s." % which,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--optfile",
        help="File containing compilation options (JSON format).",
        default=None,
    )
    parser.add_argument(
        "--repository",
        help="Git repository containing the WRF model code.",
        default=repository,
    )
    parser.add_argument(
        "--commit",
        help="Git commit to use.",
        default=commit,
    )
    parser.add_argument(
        "--destination",
        help="Directory that will host the installation.",
        default=f"./{which}",
    )
    parser.add_argument(
        "--git",
        help="Git command (useful to use a non-default installation).",
        default="git",
    )
    parser.add_argument(
        "--scheduler",
        help="Whether or not to compile in a scheduled job.",
        action=generic.ConvertToBoolean,
        default=True,
    )
    parser.add_argument(
        "--patches",
        help="Path to directory containing patches.",
        default=patches,
    )
    parser.add_argument(
        "--sources",
        help="Path to directory containing extra sources.",
        default=None,
    )
    parser.add_argument(
        "--dry",
        help=(
            "Whether this is a dry run (dry run: clone the repository and "
            "create the compile script, but do not run the compile script)."
        ),
        action=generic.ConvertToBoolean,
        default=False,
    )

    # "which"-dependent command-line arguments
    if which == "WPS":
        parser.add_argument(
            "--wrfdir",
            help="Directory where WRF is installed.",
            default="./WRF",
        )
        parser.add_argument(
            "--parallel",
            help="Whether to compile with support for parallel computing.",
            action=generic.ConvertToBoolean,
            default=True,
        )
    elif which == "WRF":
        parser.add_argument(
            "--executable",
            help="Which WRF executable to compile.",
            default="em_real",
        )
        parser.add_argument(
            "--components",
            help="A comma-separated list of extra WRF components to compile.",
            default="kpp,chem",
        )
    else:
        msg = f"Invalid choice: {which}."
        raise ValueError(msg)

    return parser


def get_options(which):
    """Return the pre-processed installation options.

    Options are read from the command line, and optionally from an "option
    file" (--optfile=/path/to/this/file at the command line). Command-line
    arguments have priority over the option file.

    Parameters
    ----------
    which: "WPS" | "WRF"
        Which model are we trying to compile here?

    Returns
    -------
    Namespace
        The pre-processed user-defined installation options.

    """
    parser = prepare_argparser(which)
    opts = parser.parse_args()
    if opts.optfile is not None:
        with open(opts.optfile) as f:
            opts_from_file = json.load(f)
        if not isinstance(opts_from_file, dict):
            msg = "Option file must represent a JSON dictionnary."
            raise ValueError(msg)
        for optname in opts_from_file:
            if optname not in opts:
                msg = f"Unknown option in file: {optname}."
                raise ValueError(msg)
        # Parse again command-line arguments, with default values from the file
        parser.set_defaults(**opts_from_file)
        opts = parser.parse_args()
    if opts.repository.startswith("http://"):
        msg = "We do not allow http connections (not secure)."
        raise ValueError(msg)
    if generic.repo_is_local(opts.repository):
        opts.repository = generic.process_path(opts.repository)
    opts.destination = generic.process_path(opts.destination)
    if "components" in opts:
        opts.components = [
            comp.strip() for comp in opts.components.split(",") if comp.strip()
        ]
    opts.patches = generic.process_path(opts.patches)
    opts.sources = generic.process_path(opts.sources)
    return opts


def format_shell_value(value):
    """Format shell value.

    Parameters
    ----------
    value: str | int
        Value to format.

    Returns
    -------
    str
        A version of value that is suitable to write in a shell script as
        `my_variable=value`.

    """
    if isinstance(value, str):
        return f'"{value}"'
    elif isinstance(value, int):
        return str(value)
    else:
        msg = f"Unsupported type for input value: {type(value)}."
        raise TypeError(msg)


def prepare_slurm_options(time):
    """Prepare slurm options.

    Parameters
    ----------
    time: str
        The wall time requested for the job with format HH:MM:SS.

    Returns
    -------
    [str]
        The lines of text that contain the slurm options.

    """
    host = generic.identify_host_platform()
    slurm = {
        "ntasks": "1",
        "ntasks-per-node": "1",
        "output": "compile.log",
        "error": "compile.log",
        "time": time,
    }
    if host == "spirit":
        slurm["partition"] = "zen16"
        slurm["mem"] = "12GB"
    return [f"#SBATCH --{key}={value}" for key, value in slurm.items()]


def write_options(opts):
    """Write installation options into file for future reproducibility.

    Parameters
    ----------
    opts: Namespace
        The pre-processed user-defined installation options.

    """
    opts_dict = dict(vars(opts).items())
    opts_dict.pop("optfile")
    opts_dict.pop("destination")
    cmd = ["git", "rev-parse", "HEAD"]
    opts_dict["commit"] = generic.run_stdout(cmd, cwd=opts.destination)[0]
    if "components" in opts_dict:
        opts_dict["components"] = ",".join(opts_dict["components"])
    optfile = os.path.join(opts.destination, "compile.json")
    with open(optfile, mode="x") as f:
        json.dump(opts_dict, f, sort_keys=True, indent=4)
        f.write("\n")


def process_patches(opts):
    """Apply patches, if any.

    Parameters
    ----------
    opts: Namespace
        The pre-processed user-defined installation options.

    """
    if opts.patches is None:
        return
    cmd = ["find", opts.patches, "-type", "f", "-name", "*.patch"]
    patches = [generic.process_path(p) for p in generic.run_stdout(cmd)]
    n = len(opts.patches) + 1
    for patch in patches:
        path_in_repo = os.path.join(opts.destination, patch[n:-6])
        if os.path.exists(path_in_repo):
            generic.run(["patch", path_in_repo, patch])
        else:
            msg = f"File {path_in_repo} does not exist so cannot be patched."
            raise RuntimeError(msg)


def process_extra_sources(opts):
    """Copy extra source files, if any, to the repository.

    Parameters
    ----------
    opts: Namespace
        The pre-processed user-defined installation options.

    """
    if opts.sources is None:
        return
    cmd = ["find", opts.sources, "-type", "f"]
    sources = [generic.process_path(src) for src in generic.run_stdout(cmd)]
    n = len(opts.sources) + 1
    for src in sources:
        path_in_repo = os.path.join(opts.destination, src[n:])
        generic.run(["cp", "-v", src, path_in_repo])
