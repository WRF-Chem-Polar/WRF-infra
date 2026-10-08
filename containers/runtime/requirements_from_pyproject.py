# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Create requirement file from pyproject file for Python dependencies."""

import tomllib

with open("pyproject.toml", mode="rb") as f:
    data = tomllib.load(f)

dependencies = []
for which in ("preprocess", "data", "performance"):
    dependencies += data["project"]["optional-dependencies"][which]

with open("requirements.txt", mode="x") as f:
    for dep in sorted(dependencies):
        f.write(f"{dep}\n")
