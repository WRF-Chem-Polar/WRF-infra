# Copyright (c) 2026-now LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Common Python resources for WRF-infra: read and write WRF namelists."""


def _name_is_valid(name):
    """Determine if given name is a valid section or key name.

    Parameters
    ----------
    name: str
        The name to analyse.

    Returns
    -------
    bool
        True if and only if given name is a valid section or key name.

    """
    if len(name) < 1 or not name[0].isalpha() or name.endswith("_"):
        return False
    for sub in name.split("_"):
        if sub == "" or not sub.isalnum():
            return False
    return True


def _process_value(value):
    """Process given namelist value.

    Parameters
    ----------
    value: str
        The value to process.

    Return
    ------
    Value
        The processed value.

    """
    if value.startswith("'") or value.startswith('"'):
        if len(value) < 2 or value[-1] != value[0]:
            msg = f"Badly quoted value: {value}."
            raise ValueError(msg)
        quoted = True
        value = value[1:-1]
    else:
        quoted = False
    if value == ".true.":
        value = True
    elif value == ".false.":
        value = False
    else:
        for convert in (int, float):
            try:
                value = convert(value)
            except ValueError:
                pass
            else:
                break
        else:
            value = str(value)
    return Value(value, quoted)


def _parse_key_values(line):
    """Parse given line that corresponds to "key = comma-separated values".

    Parameters
    ----------
    line: str
        The line to parse.

    Returns
    -------
    str: [Value]
        The key name and the corresponding list of values.

    """
    split = line.split("=")
    if len(split) != 2:
        msg = f"Could not split line around equal sign ({line})."
        raise ValueError(msg)
    key_name = split[0].strip()
    if not _name_is_valid(key_name):
        msg = f"Invalid key name: {key_name}."
        raise ValueError(msg)
    # Some parsing edge cases are not yet implemented here
    # cf https://github.com/WRF-Chem-Polar/WRF-infra/issues/192 for more info
    values = [_process_value(value.strip()) for value in split[1].split(",")]
    if values[-1].is_empty:
        values = values[:-1]
    return key_name, values


class Value:
    """A namelist value."""

    def __init__(self, value, quoting=None):
        """Initialise instance.

        Parameters
        ----------
        value: bool | int | float | str
            The actual value.
        quoting: None | bool
            Whether the value should be quoted in the namelist (automatically
            determined if None).

        """
        self._value = value
        self._quoting = isinstance(value, str) if quoting is None else quoting

    def __repr__(self):
        if self._value is True:
            out = ".true."
        elif self._value is False:
            out = ".false."
        else:
            out = str(self._value)
        if self._quoting:
            out = f"'{out}'"
        return out

    def __str__(self):
        return self.__repr__()

    @property
    def is_empty(self):
        """True if and only if the value is empty."""
        return self._value == ""


class Namelist:
    """A WRF of WRF-Chem namelist."""

    def __init__(self, filepath=None):
        """Initialise instance.

        Parameters
        ----------
        filepath: None | str
            If not None, parse the namelist located at given path.

        """
        self._content = {}
        if filepath is not None:
            self.read(filepath)

    def __repr__(self):
        out = []
        for section, key_values in self._content.items():
            if len(key_values) == 0:
                out.append(f"&{section}\n/")
            else:
                n = max(len(key) for key in key_values)
                m = max(
                    -1
                    if len(values) == 0
                    else max(len(str(v)) for v in values)
                    for _, values in key_values.items()
                )
                fmt_key = "    %%-%ds = " % n
                section_content = []
                for key, values in key_values.items():
                    fmt = fmt_key + ", ".join(["%%-%ds" % m] * len(values))
                    section_content.append(fmt % tuple([key] + values))
                out.append(f"&{section}\n{'\n'.join(section_content)}\n/")
        return "\n\n".join(out)

    def __str__(self):
        return self.__repr__()

    def read(self, filepath, overwrite=False):
        """Read and parse given file.

        Parameters
        ----------
        filepath: str
            Path to the file to read and parse.
        overwrite: bool
            Whether overwriting exisiting content is allowed.

        """
        with open(filepath, mode="r") as f:
            content = f.readlines()

        in_section = False
        for line in [line.strip() for line in content]:
            if line == "" or line.startswith("!"):
                continue

            elif line.startswith("&"):
                # This is the beginning of a new section
                if in_section:
                    msg = "Nested sections are forbidden."
                    raise ValueError(msg)
                in_section = True
                section_name = line[1:]
                if not _name_is_valid(section_name):
                    msg = f"Invalid section name: {section_name}."
                    raise ValueError(msg)
                try:
                    section = self._content[section_name]
                except KeyError:
                    section = self._content[section_name] = {}

            elif line == "/":
                # This is the end of a section
                if not in_section:
                    msg = "Unexpected end of section."
                    raise ValueError(msg)
                in_section = False

            else:
                # This is a "key = value" line
                if not in_section:
                    msg = "Content line encountered out of section."
                    raise ValueError(msg)
                key, values = _parse_key_values(line)
                self.set_values(section_name, key, values, overwrite=overwrite)

    def set_values(self, section, key, values, overwrite=False):
        """Set namelist values for given section and key.

        Parameters
        ----------
        section: str
            The name of the section.
        key: str
            The name of the key.
        values: [Value]
            The corresponding values.
        overwrite: bool
            Whether overwriting values is allowed.

        """
        if not isinstance(values, list):
            msg = 'Input parameter "values" must be a list.'
            raise TypeError(msg)
        try:
            section = self._content[section]
        except KeyError:
            self._content[section] = {key: values}
        else:
            try:
                current_values = section[key]
            except KeyError:
                section[key] = values
            else:
                if values != current_values:
                    if not overwrite:
                        msg = (
                            "Receiving new and different values for existing "
                            f"key {key} but overwriting is not allowed."
                        )
                        raise ValueError(msg)
                    section[key] = values

    def get_values(self, section, key):
        """Get namelist values for given section and key.

        Parameters
        ----------
        section: str
            The name of the section.
        key: str
            The name of the key.

        Returns
        -------
        [Value]
            The values of given key in given section.

        """
        try:
            return self._content[section][key]
        except KeyError:
            msg = f"Key {key} and/or section {section} does not exist."
            raise ValueError(msg)
