# Contributing to WRF-infra

## First-time external contributors

> [!IMPORTANT]
> This section applies to users who are not part of the [WRF-Chem-Polar organisation](https://github.com/WRF-Chem-Polar).

If you want to become a WRF-infra contributor, we kindly ask you to first open a dedicated issue that briefly describes how you came to know and use WRF-infra. We are seeking to create a community of WRF-infra-loving users and developers, and we will refrain from accepting contributions if we suspect they come from users or AI agents that are entirely disengaged from WRF-infra.

## Preparing your computing environment

A brief introduction on how to set up your computing environment for WRF-infra can be found in our [online documentation](https://wrf-chem-polar.eu/doc/infra.html).

## Scripts

WRF-infra is mainly made up of scripts. WRF-infra uses Bash and Python for scripting, nothing else.

We use Python by default. Bash is used instead when there is a good reason to use it over Python. A typical example is for job scripts that are meant to be sent directly to a scheduler on a supercomputer.

Scripts must be entirely configurable via command-line arguments. It is not acceptable to expect or require a user to open and modify a script to use it.

Every WRF-infra script must print a technical documentation when called with the command-line argument `--help`. This documentation must provide a short description of what the script does (one line or a few lines), and a short description of all command-line arguments supported by the script.

In Python, use the `argparse` module from the standard library to implement this functionality. In Bash, use the same approach as in [this script](./testing/analyse-results.bash).

All command-line arguments must have a long form starting with two dashes (eg `--output-file`). To increase human-readability of WRF-infra code, the long-form must be used when calling scripts from other scripts. Optionnally, a single-dash short form (eg. `-o`) may also be implemented, for convenience when calling scripts directly from the command-line.

## Creating issues

Anyone is welcome to create an issue to:

 - **report a bug.** In this case, please provide as much relevant information as possible to help us fix the bug.

 - **suggest an improvement**. In this case, please explain carefuly what is not working for you with WRF-infra as is, and what will become possible with your improvement that was not possible before.

 - **ask for a new feature**. In this case, please explain carefuly why you think adding this feature is relevant for WRF-infra, and suggest one or more usecase(s).

As far as reasonably possible, each issue should describe a single non-divisible task or improvement. If your suggested improvement or feature can be divided into multiple smaller improvements/features/tasks, then create separate issues for each of these. Do cross-reference issues as needed in your descriptions.

## Making a pull request

Before making a pull request, you must ensure that there exists a related issue. In other words, each pull request must be associated whith an existing issue. It is ok to have several pull requests associated with the same issue, if it is relevant to solve said issue in several independent smaller steps. Create the issue if needed, following the instructions above.

Only members of the [WRF-Chem-Polar organisation](https://github.com/WRF-Chem-Polar) with triage permissions can assign issues. If you want to work on an issue, you must first get it assigned to you by one of them. You can ask to get assigned an issue directly on said issue.

Create and do your work on a branch named `issue##/short-description-of-issue` where `##` is the issue number without leading zeros. If you have write access to the repository, you can create the branch there directly. Otherwise create it in your own fork.

The title of the pull request should be short, should start with a verb (and a capital letter), and should describe what the pull request fixes/does/adds. Examples are "Add docstrings to functions in myfile.py", or "Fix leap-year bug in run script". Do not use a trailing period mark.

If needed, add more information in the body of the message. In any case, the body of the pull request should mention the associated issue, typically with something like "This commit fixes issue ##." (here we say "commit" because we squash commits before merging pull requests, and therefore each merged pull request will appear as a single commit in the Git history).

Authors of pull requests are responsible for testing their code and making sure it works before requesting a review.

## Reviewing a pull request

Each pull request must obtain approval from one member of the [WRF-Chem-Polar organisation](https://github.com/WRF-Chem-Polar) with write privileges before it can be merged.

The guidelines for reviewing a pull request are:

 - Reviewers may, but do not have to, **test** the code.

 - Reviewers **must read the code**. They should request changes in the following circumstances:

   * clarity of the code can be improved.

   * the code can be simplified.

   * the code does not respect the WRF-infra coding style (see below).

   * the code will fail in certain circumstances.

   * the code does not fully address the associated issue (or the sub-part of this issue that it is meant to address).

   * the code adds functionality or fix parts of WRF-infra that are beyond the scope of the associated issue. These should be treated in separate issues and pull requests.

 - Reviewers may have ideas for new features or interesting additions related to the pull request but that go beyong the scope of the original issue. In this case, the reviewer should create a separate issue instead of requesting the author to implement them.

## Coding style

WRF-infra code must respect the following:

 - The UK-vs-US English style guide defined [here](https://github.com/WRF-Chem-Polar/WRF-infra/issues/148).

 - All Bash and Python functions must be documented with a [numpy-style docstring](https://numpydoc.readthedocs.io/en/latest/format.html), to the exception of standard Python dunder functions (eg. `__str__`).

 - Lines do not have trailing space (see section "Configure your text editor below"). This reduces unnecessary `diff`erences between files.

In addition, Python code must respect the following:

 - Python's style guide described in [PEP8](https://peps.python.org/pep-0008/).

 - The format and quality controls imposed by [Ruff](https://docs.astral.sh/ruff/), according to the options defined in [pyproject.toml](./pyproject.toml). Note that a CI workflow will block any pull request that does not respect this.

## Documentation

Each WRF-infra script should be self-documenting as previously detailed. In addition, we maintain a more beginner-friendly documentation of all things WRF-Chem-Polar in [this repository](https://github.com/WRF-Chem-Polar/documentation). WRF-infra contributors are expected to write beginner-friendly documentation into that repository for any new or updated WRF-infra feature that warrants it.

## Use of AI to create WRF-infra content

There is currently no policy in favor or against the use of artificial intelligence to contribute to WRF-infra. However, each contributing author is held accountable for the quality of the code they send to the review process, as well as for following the rules described in this document. Furthermore, authors are expected to fully understand each line of code they contribute. This is required to be able to engage in the technical discussions that are meant to occur between the author and the reviewer during the review process.

## Configure your text editor

We recommend you to configure your text editor so that all trailing space is removed as soon as you save a file:

```
# Emacs
(add-hook 'before-save-hook 'delete-trailing-whitespace)

# Vim
fun! TrimWhiteSpaceEndOfLines()
	let l:save = winsaveview()
	keeppatterns %s/\s\+$//e
	call winrestview(l:save)
endfun
autocmd BufWritePre * if !&binary | call TrimWhiteSpaceEndOfLines() | endif
```

## Derivative works

WRF-infra is free and open-source software: you are welcome to mofify it, distribute it, and distribute modified versions of it, as long as you abide the (very few) requirements of the [BSD 3-clause license](./LICENSE). These are mostly requirements of attribution and of not using our names for promoting your derived products.
