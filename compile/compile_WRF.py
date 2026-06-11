# Copyright (c) 2025-2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Compile WRF."""

import sys
import os
import configparser
from wrfinfra import generic, compilation

host = generic.identify_host_platform()
opts = compilation.get_options("WRF")
config = configparser.ConfigParser()
config.read(os.path.join(generic.path_of_repo(), "env", f"{host}.config"))

generic.run([opts.git, "clone", opts.repository, opts.destination])
generic.run([opts.git, "checkout", opts.commit], cwd=opts.destination)
# On some supercalculators, cloning from GitHub is allowed on the login nodes
# but not on the computing nodes. We therefore clone the git submodules now,
# ie. before potentially sending the rest of the work to the computing nodes
generic.run(
    [opts.git, "submodule", "update", "--init", "--recursive"],
    cwd=opts.destination,
)
compilation.write_options(opts)
compilation.write_job_script(opts, config, "WRF")
compilation.process_patches(opts)
compilation.process_extra_sources(opts)

if opts.dry:
    sys.exit(0)

if opts.scheduler:
    cmd = [config["common"]["job-exe"], "compile.job"]
else:
    cmd = ["./compile.job"]
generic.run(cmd, cwd=opts.destination)
