This directory contains the definitions of environments for compiling and running WPS and WRF/WRF-Chem on different machines.

There is one file per supported machine. This file should be named `$host.config` (the value of `$host` is determined by the function `identify_host_platform` in `pymodules/wrfinfra/generic.py`).

This file should follow the syntax of "config files" (also known as "INI files"). The reference for this syntax is Python's `configparser` module.

What follows describes the typical content of these configuration files.

# Section "common"

This section is mandatory only if a scheduler is used. It defines parameters that are common to everything (compiling and running WPS and WRF).

 - `job-exe` (mandatory for scheduler use): the executable of the scheduler.

 - `job-header-prefix` (mandatory for scheduler use): the prefix of the scheduler instruction lines in job scripts (eg. `#SBATCH --` if scheduler uses lines such as `#SBATCH --time=00:01:00`).

 - `job-header-separator` (mandatory for scheduler use): the character string that separates option names from option values in scheduler instruction lines in job scripts (typically an equal sign or a space character).

 - `job_header_option_${option_name}` (optional): the value of given scheduler option.

 - `shell` (optional): Bash commands to be executed before compiling and executing WPS or WRF.

# Section "compile.all"

This section is optional and defines parameters that are common to the compilation of WRF and WPS.

 - `job_header_option_${option_name}` (optional): the value of given scheduler option, has precedence over the one in section "common".

 - `shell` (optional): Bash commands to be executed before compiling WRF and WPS.

# Section "compile.WRF"

This section is mandatory when compiling WRF and defines parameters that are specific to the compilation of WRF.

 - `job_header_option_${option_name}` (optional): the value of given scheduler option, has precedence over the one in section "compile.all".

 - `shell` (optional): contains Bash commands to be executed before compiling WRF.

 - `configure-opt` (mandatory): the option which defines the host platform and compiler suite to use for WRF/WRF-Chem, to choose from the list when running the vanilla WRF configure script.

Note that when compiling WRF, the `shell` commands of the "common" section will be executed before the `shell` commands of the `compile.all` section, which will themselves be executed before the `shell` commands of the "compile.WRF" section.

# Section "compile.WPS"

Same as "compile.WRF" but for compiling WPS.

# Section "run.all"

This section is mandatory when running WPS or WRF.

 - `cmd-python` (mandatory): the command to execute Python.
