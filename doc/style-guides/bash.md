## POSIX versus Bash

There is a lot of debate out there about using POSIX-compliant versus Bash-specific syntax (eg. `[` versus `[[`, respectively). Using POSIX-compliant syntax is more portable across different shells, but using Bash-specific syntax can be cleaner and conducive to fewer bugs.

Here we do not write system-level code; we write user-level code. We do not need portabaly outside of Bash because any self-respecting user-oriented Unix-like system has a Bash interpreter. We prefer cleaner, less error-prone code. We therefore do not restrain ourselves from using Bash-specific syntax.

## Shebang

Use `#!/bin/bash` (and not `#!/usr/bin/env bash`) for the shebang.

Rationale:

-  `#!/bin/bash` ensures that the script is run using the system-wide Bash whereas `#!/usr/bin/env bash` runs whichever Bash executable comes first in the search path. Here we prefer the predictability of enforcing the use of the system-wide Bash and we dislike to unpredictability of potentially using a custom Bash version installed by the user.
- `#!/bin/bash` works on virtually all GNU/Linux distributions. It does not work on some of the BSDs, but for now we have no plan to support BSD systems (besides, the admins of such systems can simply sim-link the actual Bash executable to `/bin/bash`).
- For licensing reasons, `/bin/bash` on MacOS is stuck at version 3.2.57 (the last GPL2 version before transitionning to GPL3). We may use some Bash v4+ features in our scripts but we do not intend to support MacOS for running WRF-Chem-Polar at this time.

## Filename extension

Use the `.bash` extension for Bash scripts.

Rationale:

 - It gives more information than `.sh`: it says: _"this script might use features that are specific to Bash"_.

## Max column width

When reasonably achievable, try to make line lengths < 80 characters.

Rationale:

- It is admittedly easier to work on code if the line length is not too long (easier to read, to look at files side-by-side, etc).
- The same limit is enforced (by Ruff) for Python code in this repository, so things will look consistent.

## Indentation

Use 4 spaces (no tabs) for each level of indentation.

Rationale: isn't that a universally accepted convention?

## Variable names

Use lower case names for variables, and use underscores as needed to improve readabilty.

Rationale:

- Save our pinkie fingers some needless strain.
- The same convention is used for Python code in this repository, so things will look consistent.

## Quotes

### String literals

Dot not use quotes around string literals that do not need them:

```sh
# Not OK
my_variable="/home/myself"

# OK
my_variable=/home/myself
```

Rationale: this is simpler and more readable.

### When using variables

Always use double quotes in strings that involve the value of a variable.

```sh
# Not OK
dir_model=/home/myself/model
dir_parameters=${dir_models}/parameters

# OK
dir_model=/home/myself/model
dir_parameters="${dir_models}"/parameters

# OK
dir_model=/home/myself/model
dir_parameters="${dir_models}/parameters"
```

Rationale: this is safer when variable values contain spaces.

### Single versus double quotes.

Where quotes are needed, use double-quotes by default. Use single quotes only when you need things NOT to be expanded, for example:

```sh
# OK
echo 'I want to show you what the dollar sign looks like: $'
```

Rationale: most often we want things to be expanded.

## Single versus double brackets

We use double brackets. Everywhere. For example:

```sh
# Not OK
if [ $myvar -eq 42 ]; then
    echo "this is the answer"
fi

# OK
if [[ $myvar -eq 42 ]]; then
    echo "this is the answer"
fi
```

Rationale: the double brackets syntax is a Bash-specific feature that is more powerful than the POSIX-compliant single bracket. Double brackets are also safer to use when variables are undefined. In the example above, if `$myvar` is undefined, the single bracket syntax will result in a syntax-like error while the double bracket syntax will work as expected.

# Use of curly braces around variable names

Always use curly braces around variable names, except for one-letter variable names when it can be avoided.

```sh
# OK
dir_simulation="${dir_model}/simulations"

# NOT OK
dir_simulation="$dir_model/simulations"
```

Rationale:

- Always using curly braces around variable names helps to prevent errors such as `concat_with_underscore="$myvar_$myothervar"`.
- In the case of one-letter variable names (eg `$i`, `$?`, `$#`), curly braces may actually increase confusion, so we avoid them if we can.

# Double square brackets versus double parentheses

Use double square brackets everywhere you can. Use double parentheses when you actually need arithmetics.

```sh
# OK
if [[ $my_var -eq 0 ]]; then
    echo "my_var is zero"
fi

# Not OK
if (( my_var == 0 )); then
    echo "my_var is zero"
fi
```

Rationale: with this choice, the syntax is generally more consistent throughout scripts. We rarely need to perform many arithemetic operations in a Bash script. If you do, you should probably use Python instead.

# Comparison operators (-eq, -ne, =, ==, !=, etc)

The following operators are used to compare numbers inside double square braquets `[[ ... ]]`: `-eq`, `-ne`, `-lt`, `-le`, `-gt`, `-ge`.

The following operators are used to compare strings inside double square braquets `[[ ... ]]`: `==`, `!=`. The operator `=` can also be used for equality testing in this context, but we prefer to use `==` instead. Rationale:
 - It is more intuitive, because most other languages use `==` for equality testing, while `=` is generally used for assignment.
 - `==` is more flexible than `=`: the former can be used for pattern matching.

# Function docstrings

Write docstring using the Numpy/Scipy conventions, for example:

```sh
function check_dates {
    # Run quality checks on given dates.
    #
    # Parameters
    # ----------
    # date_1, date_2, ...: str
    #     Dates to check. Accepted formats are anything parsable by the shell
    #     function `date` as long as the timezone is explicitly specified.
    #
    # Returns
    # -------
    # int
    #     Zero if all the dates are parsable and valid, non-zero otherwise.
    #
    ...
}
```

Rationale: things will look consistent with the Python code of this repository.

