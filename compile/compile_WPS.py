# Copyright (c) 2025 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Compile WPS."""

import sys
import os.path
from wrfinfra import generic, compilation


def prepare_environment_variables(opts):
    """Prepare the compilation environment variables.

    Parameters
    ----------
    opts: Namespace
        The pre-processed user-defined installation options.

    Returns
    -------
    [str]
        The lines setting environment variables.

    """
    env_vars = {
        "NETCDF": "$NETCDF_FORTRAN_ROOT",
        "HDF5": "$HDF5_ROOT",
        "WRF_DIR": generic.process_path(opts.wrfdir),
    }
    return [
        f"export {name}={compilation.format_shell_value(value)}"
        for name, value in env_vars.items()
    ]


def write_job_script(opts):
    """Create the job script.

    Parameters
    ----------
    opts: Namespace
        The pre-processed user-defined installation options.

    """
    # Platform, directories, and files
    host = generic.identify_host_platform()
    envfile = os.path.join(generic.path_of_repo(), "env", f"{host}.sh")
    script = os.path.join(opts.destination, "compile.job")

    # Prepare header of file (hash bang and scheduler options)
    lines = ["#!/bin/bash"]
    if opts.scheduler:
        if host in ("spirit",):
            lines += compilation.prepare_slurm_options("00:30:00")
        else:
            msg = f"Unsupported host: {host}."
            raise NotImplementedError(msg)

    # Platform-specific environment
    with open(envfile) as f:
        env = [line.strip() for line in f]
    lines += [line for line in env if line and not line.startswith("#")]
    lines += prepare_environment_variables(opts)
    setup = {"spirit": 1 + opts.parallel}[host]

    # Add the call to ./configure and ./compile
    lines.append('echo -e "%d" | \\' % setup)
    lines.append("./configure --build-grib2-libs")
    lines.append("./compile")

    # Write the script
    with open(script, mode="x") as f:
        f.write("\n".join(lines))
        f.write("\n")
    os.chmod(script, 0o744)


if __name__ == "__main__":
    # Actually do the work (parse user options, checkout, compile)

    host = generic.identify_host_platform()
    opts = compilation.get_options("WPS")

    generic.clone_and_checkout(opts)
    compilation.write_options(opts)
    write_job_script(opts)
    compilation.process_patches(opts)
    compilation.process_extra_sources(opts)

    if opts.dry:
        sys.exit(0)

    if opts.scheduler:
        cmd = [{"spirit": "sbatch"}[host], "compile.job"]
    else:
        cmd = ["./compile.job"]
    generic.run(cmd, cwd=opts.destination)
