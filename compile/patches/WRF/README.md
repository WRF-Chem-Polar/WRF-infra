# chem/KPP/kpp/kpp-2.1/src/Makefile.patch

KPP uses (b)yacc. We can use GNU bison instead but, when using bison, one has to specify the name of the output file explicitly. This patch makes it possible to use bison instead of (b)yacc.

# phys/Makefile.patch

On some supercalculators, cloning from GitHub is allowed on the login nodes but not on the computing nodes. In the vanilla WRF compilation workflow, the submodules are pulled from GitHub or other providers quite deep in the compilation process, at a time where the job is typically already running on a computing node. To address this issue, we pull the submodules early in the compilation process (directly in compile_WRF.py) instead.
