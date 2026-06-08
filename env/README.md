This directory contains the definitions of environments for compiling and running WPS and WRF/WRF-Chem on different machines.

There is one file per supported machine. This file should be named `$host.config` (the value of `$host` is determined by the function `identify_host_platform` in `pymodules/wrfinfra/generic.py`).

This file should follow the syntax of "config files" (also known as "INI files"). The reference for this syntax is Python's `configparser` module.

What follows describes the typical content of these configuration files.

# Section "common"

This section is mandatory only if a scheduler is used. It defines parameters that are common to everything (compiling and running WPS and WRF).

 - `job_exe` (mandatory for scheduler use): the executable of the scheduler.

 - `job_header` (mandatory for scheduler use): the header of the scheduler jobs (without the pound signs at the beginning of lines), with possibility of using place holders (syntax: <place_holder>).

 - `shell` (optional): Bash commands to be executed before compiling and executing WPS or WRF.

# Section "compile.all"

This section is optional and defines parameters that are common to the compilation of WRF and WPS.

 - `job_header_replace_${place_holder}` (optional): replace given place holder in the job header by given value.

 - `shell` (optional): Bash commands to be executed before compiling WRF and WPS.

# Section "compile.WRF"

This section is mandatory when compiling WRF and defines parameters that are specific to the compilation of WRF.

 - `job_header_replace_${place_holder}` (optional): same (but higher precedence) as for section `compile.all`.

 - `shell` (optional): contains Bash commands to be executed before compiling WRF.

 - `configure_opt` (mandatory): the option which defines the host platform and compiler suite to use for WRF/WRF-Chem, to choose from the list when running the vanilla WRF configure script.

Note that when compiling WRF, the `shell` commands of the "common" section will be executed before the `shell` commands of the `compile.all` section, which will themselves be executed before the `shell` commands of the "compile.WRF" section.

# Section "compile.WPS"

Same as "compile.WRF" but for compiling WPS.

# Section "run.all"

This section is mandatory when running WPS or WRF.

 - `cmd_python` (mandatory): the command to execute Python.
