This directory contains the definitions of environments for compiling and running WRF/WRF-Chem on different machines.

There is one file per supported machine.

Each file may manipulate the environment in any way necessary (eg. load modules) but must define a number of environmental variables. Below are listed all the required and optional environmental variables (they can be needed for compilation, runtime, or both -- this is indicated in square brackets in each case).

 - cmd_python [runtime]: the command to run Python code (this can, for example, be a `conda run ... python` command or a system-wide Python such as `/usr/bin/python`).
