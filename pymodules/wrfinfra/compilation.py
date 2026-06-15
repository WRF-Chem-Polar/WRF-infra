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
        patches = os.path.join(
            generic.path_of_repo(), "compile", "patches", "WRF"
        )
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
        "--scheduler-opt",
        help="Define a scheduler option (can be used multiple times).",
        action="append",
        nargs=2,
        default=[],
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


def prepare_scheduler_header(opts, config, which):
    """Create the scheduler header.

    Parameters
    ----------
    opts: Namespace
        The pre-processed user-defined installation options.
    config: Namespace
        The parsed plateform-dependent configuration.
    which: "WRF" | "WPS"
        The program being compiled.

    Returns
    -------
    str
        The scheduler header.

    """
    # Quality checks on input arguments
    if which not in ("WRF", "WPS"):
        msg = f"Bad value of which ({which})."
        raise ValueError(msg)

    # Prepare options from platform-dependent config file
    options = {}
    for section_name in ("common", "compile.all", f"compile.{which}"):
        try:
            section = config[section_name]
        except KeyError:
            continue
        for key, value in section.items():
            if not key.startswith("job-header-option-"):
                continue
            name = key[len("job-header-option-") :]
            if name == "":
                msg = f"Invalid option ({key})."
                raise ValueError(msg)
            options[name] = value

    # Update options with command-line arguments
    for name, value in opts.scheduler_opt:
        options[name] = value

    # Format and return the header
    pfx = config["common"]["job-header-prefix"]
    sep = config["common"]["job-header-separator"]
    header = [f"{pfx}{key}{sep}{value}" for key, value in options.items()]
    return "\n".join(header)


def write_job_script(opts, config, which):
    """Create the job script.

    Parameters
    ----------
    opts: Namespace
        The pre-processed user-defined installation options.
    config: Namespace
        The parsed plateform-dependent configuration.
    which: "WRF" | "WPS"
        The program being compiled.

    """
    script = os.path.join(opts.destination, "compile.job")
    with open(script, mode="x") as f:
        f.write("#!/bin/bash\n")

        # Write the job header
        if opts.scheduler:
            f.write(prepare_scheduler_header(opts, config, which) + "\n")

        # Write the plateform-specific environment
        for section_name in ("common", "compile.all", f"compile.{which}"):
            try:
                shell = config[section_name]["shell"]
            except KeyError:
                continue
            f.write(shell + "\n")

        # Write the generic environment
        f.write("export EM_CORE=1\nexport NMM_CORE=0\n")

        # Write the model-dependent environment
        opt = int(config[f"compile.{which}"]["configure-opt"])
        if which == "WRF":
            # Just using the chem and kpp options is not enough, one also has
            # to explicitly set the corresponding environment variables
            if "chem" in opts.components:
                f.write("export WRF_CHEM=1\n")
            if "kpp" in opts.components:
                f.write("export WRF_KPP=1\n")
            cmd = 'echo -e "%d\\n1" | ./configure' % opt
            if opts.components:
                cmd += " " + " ".join(opts.components)
            f.write(cmd + f"\n./compile {opts.executable}\n")

        elif which == "WPS":
            f.write(f"export WRF_DIR={generic.process_path(opts.wrfdir)}\n")
            f.write('echo -e "%d" | ./configure --build-grib2-libs\n' % opt)
            f.write("./compile\n")

        else:
            msg = f"Invalid value for which (f{which})"
            raise ValueError(msg)

    # Make the script executable and we are done
    os.chmod(script, 0o744)


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
