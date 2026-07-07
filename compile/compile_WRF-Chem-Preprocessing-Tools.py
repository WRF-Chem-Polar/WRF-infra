# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Compile the WRF-Chem Preprocessing Tools."""

host = generic.identify_host_platform()
opts = compilation.get_options("WRF-Chem-Preprocessing-Tools")
config = configparser.ConfigParser()
config.read(os.path.join(generic.path_of_repo(), "env", f"{host}.config"))

generic.run([opts.git, "clone", opts.repository, opts.destination])
generic.run([opts.git, "checkout", opts.commit], cwd=opts.destination)
compilation.write_options(opts)

script = os.path.join(opts.destination, "compile.job")
with open(script, mode="x") as f:
    f.write("#!/bin/bash\n")

    # Write the job header
    if opts.scheduler:
        f.write(prepare_scheduler_header(opts, config, which) + "\n")

    # Write the plateform-specific environment
    section_names = (
        "common",
        "compile.all",
        "compile.WRF-Chem-Preprocessing-Tools",
    )
    for section_name in section_names:
        try:
            shell = config[section_name]["shell"]
        except KeyError:
            continue
        f.write(shell + "\n")

os.chmod(script, 0o744)

compilation.process_patches(opts)
compilation.process_extra_sources(opts)

if opts.dry:
    sys.exit(0)

if opts.scheduler:
    cmd = [config["common"]["job-exe"], "compile.job"]
else:
    cmd = ["./compile.job"]
generic.run(cmd, cwd=opts.destination)
