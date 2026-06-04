# Copyright (c) 2025-2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Compile WRF."""

import sys
import os
from wrfinfra import generic, compilation


def prepare_components(opts):
    """Prepare WRF components.

    Parameters
    ----------
    opts: Namespace
        The pre-processed user-defined installation options.

    Returns
    -------
    str
        The WRF options, formatted to be passed to the configure script.

    """
    return " " + " ".join(opts.components) if opts.components else ""


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
    host = generic.identify_host_platform()
    env_vars = {
        "EM_CORE": 1,
        "NMM_CORE": 0,
        "NETCDF": "$NETCDF_FORTRAN_ROOT",
        "HDF5": "$HDF5_ROOT",
    }
    # For some reason, just using the chem and kpp options is not enough, one
    # also has to explicitly set the corresponding environment variables
    if "chem" in opts.components:
        env_vars["WRF_CHEM"] = 1
    if "kpp" in opts.components:
        env_vars["WRF_KPP"] = 1
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
        if host in ("jeanzay", "jed", "spirit"):
            lines += compilation.prepare_slurm_options("03:00:00")
        else:
            msg = f"Unsupported host: {host}."
            raise NotImplementedError(msg)

    # Platform-specific environment
    with open(envfile) as f:
        env = [line.strip() for line in f]
    lines += [line for line in env if line and not line.startswith("#")]
    lines += prepare_environment_variables(opts)
    nesting = 1

    # Add the call to ./configure
    lines.append('echo -e "${WRF_COMPILE_PLATFORM}\\n%d" | \\' % nesting)
    lines.append(f"./configure{prepare_components(opts)}")

    # Add the call to ./compile
    lines.append(f"./compile {opts.executable}")

    # Write the script
    with open(script, mode="x") as f:
        f.write("\n".join(lines))
        f.write("\n")
    os.chmod(script, 0o744)


if __name__ == "__main__":
    # Actually do the work (parse user options, checkout, compile)

    host = generic.identify_host_platform()
    opts = compilation.get_options("WRF")

    generic.run([opts.git, "clone", opts.repository, opts.destination])
    generic.run([opts.git, "checkout", opts.commit], cwd=opts.destination)
    # On some supercalculators, cloning from GitHub is allowed on the login
    # nodes but not on the computing nodes. For that reason, we clone the git
    # submodules now, ie. before potentially sending the rest of the work to
    # the computing nodes
    generic.run(
        [opts.git, "submodule", "update", "--init", "--recursive"],
        cwd=opts.destination,
    )
    compilation.write_options(opts)
    write_job_script(opts)
    compilation.process_patches(opts)
    compilation.process_extra_sources(opts)

    if opts.dry:
        sys.exit(0)

    if opts.scheduler:
        schedulers = {"jeanzay": "sbatch", "jed": "sbatch", "spirit": "sbatch"}
        cmd = [schedulers[host], "compile.job"]
    else:
        cmd = ["./compile.job"]
    generic.run(cmd, cwd=opts.destination)
