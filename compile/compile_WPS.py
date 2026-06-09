# Copyright (c) 2025-2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Compile WPS."""

import sys
import os.path
import configparser
from wrfinfra import generic, compilation

host = generic.identify_host_platform()
opts = compilation.get_options("WPS")
config = configparser.ConfigParser()
config.read(os.path.join(generic.path_of_repo(), "env", f"{host}.config"))

generic.run([opts.git, "clone", opts.repository, opts.destination])
generic.run([opts.git, "checkout", opts.commit], cwd=opts.destination)
compilation.write_options(opts)
compilation.write_job_script(opts, config, "WPS")
compilation.process_patches(opts)
compilation.process_extra_sources(opts)

if opts.dry:
    sys.exit(0)

if opts.scheduler:
    cmd = [config["common"]["job_exe"], "compile.job"]
else:
    cmd = ["./compile.job"]
generic.run(cmd, cwd=opts.destination)
