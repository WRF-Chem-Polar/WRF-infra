# Copyright (c) 2025-now LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Common Python resources for WRF-infra: generic resources."""

import os
import functools
import argparse
import subprocess

URL_GITHUB = "https://github.com"
URL_GROUP_WRF = "%s/wrf-model" % URL_GITHUB
URL_WPS = "%s/WPS.git" % URL_GROUP_WRF
URL_GROUP_POLAR = "%s/WRF-Chem-Polar" % URL_GITHUB
URL_WRFCHEMPOLAR = "%s/WRF-Chem-Polar.git" % URL_GROUP_POLAR


class ConvertToBoolean(argparse.Action):
    """Action to convert command-line arguments to booleans."""

    def __call__(self, _, namespace, values, option_string=None):
        """Convert command line option value to boolean.

        See https://docs.python.org/3/library/argparse.html#action-classes for
        more details about action classes and the corresponding API.

        """
        while option_string.startswith("-"):
            option_string = option_string[1:]
        option_string = option_string.replace("-", "_")
        if values.lower() in ("true", "t", "yes", "y"):
            values = True
        elif values.lower() in ("false", "f", "no", "n"):
            values = False
        else:
            msg = f'Could not convert "{values}" to boolean.'
            raise ValueError(msg)
        setattr(namespace, option_string, values)


@functools.lru_cache
def identify_host_platform():
    """Return the identity of the host platform.

    Returns
    -------
    str
        The identity of the host platform.

    """
    known_plateforms = {
        "spirit1.ipsl.fr": "spirit",
        "spirit2.ipsl.fr": "spirit",
    }
    nodename = os.uname().nodename
    try:
        platform = known_plateforms[nodename]
    except KeyError:
        msg = f"Unknown host platform: {nodename}."
        raise NotImplementedError(msg)
    return platform


def process_path(path):
    """Return a unique absolute version of given path.

    Parameters
    ----------
    path: str | None
        The path to process.

    Returns
    -------
    str | None
        The unique and absolute version of given path (or None if given path is
        empty or None)

    """
    if path is None or path.strip() == "":
        return None
    return os.path.abspath(os.path.expanduser(path))


def path_of_repo(path=None):
    """Return path of Git repository containing given path.

    Parameters
    ----------
    path: str
        A path that is supposed to be located somewhere in a Git repository. If
        None, then this function returns the path of the Git repository
        containing this module.

    Returns
    -------
    str
        The path of the Git repository that contains given path.

    Notes
    -----
    Given path does not have to exist to find the corresponding Git repository.
    For example, if /home/myself/myrepo is an existing Git repository, then
    path_of_repo("/home/myself/myrepo/myfile.txt") will return
    "/home/myself/myrepo" even if myfile.txt does not exists.

    """
    abspath = os.path.abspath(__file__ if path is None else path)
    if os.path.isdir(os.path.join(abspath, ".git")):
        return abspath
    parent = os.path.dirname(abspath)
    if parent == abspath:
        msg = "Could not determine path to git repository."
        raise RuntimeError(msg)
    else:
        return path_of_repo(parent)


def repo_is_local(repository):
    """Return whether given repository address is local.

    This function only looks at the format of the given character string.
    Whether the repository is local or remote, this function does not check if
    the repository exists or not.

    Returns
    -------
    bool
        True if given address is local, False otherwise.

    """
    return (
        "@" not in repository
        and not repository.startswith("http://")
        and not repository.startswith("https://")
    )


def run(args, **kwargs):
    """Run given command and arguments as a subprocess.

    Parameters
    ----------
    args: sequence
        The command to run and its arguments, eg. ["grep", "-v", "some text"].
    kwargs: dict
        These are passed "as is" to subprocess.run.

    Returns
    -------
    subprocess.CompletedProcess
        The result of running the command.

    Raises
    ------
    RuntimeError
        If the command returns a non-zero exit code.

    """
    out = subprocess.run(args, **kwargs)
    if out.returncode:
        msg = f"Command '{' '.join(args)}' exited with non-zero return code."
        raise RuntimeError(msg)
    return out


def run_stdout(args, **kwargs):
    """Run given command and arguments as a subprocess and return stdout.

    Parameters
    ----------
    args: sequence
        The command to run and its arguments, eg. ["grep", "-v", "some text"].
    kwargs: dict
        These are passed "as is" to subprocess.run, but cannot contain
        "capture_output" nor "text".

    Returns
    -------
    [str]
        The standard output of the command (one string per line).

    Raises
    ------
    RuntimeError
        If the command returns a non-zero exit code.

    """
    nope_list = ("capture_output", "text")
    forbidden_kwargs = list(filter(lambda kwarg: kwarg in nope_list, kwargs))
    if forbidden_kwargs:
        msg = f"Forbidden keyword argument(s): {', '.join(forbidden_kwargs)}."
        raise ValueError(msg)
    out = run(args, capture_output=True, text=True, **kwargs)
    return out.stdout[:-1].split("\n")


def clone_and_checkout(opts):
    """Clone the repository and checkout the required commit.

    Parameters
    ----------
    opts: Namespace
        The pre-processed user-defined installation options.

    Raises
    ------
    RuntimeError
        If the destination already exists.

    """
    if os.path.exists(opts.destination):
        raise RuntimeError("Destination directory already exists.")
    run([opts.git, "clone", opts.repository, opts.destination])
    run([opts.git, "checkout", opts.commit], cwd=opts.destination)
