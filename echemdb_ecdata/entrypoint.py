r"""
CLI for conversion of echemdb data files.

EXAMPLES::

    >>> from echemdb_ecdata.test.cli import invoke
    >>> invoke(cli, "--help")  # doctest: +NORMALIZE_WHITESPACE
    Usage: cli [OPTIONS] COMMAND [ARGS]...

      The unitpackage suite

    Options:
      --help  Show this message and exit.
    Commands:
      raw  Convert a file containing CSV data into a datapackage.

"""

# ********************************************************************
#  This file is part of echemdb_ecdata.
#
#        Copyright (C) 2024-2026 Albert Engstfeld
#        Copyright (C)      2022 Johannes Hermann
#        Copyright (C) 2022-2025 Julian Rüth
#
#  echemdb_ecdata is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  echemdb_ecdata is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with echemdb_ecdata. If not, see <https://www.gnu.org/licenses/>.
# ********************************************************************
import logging
from pathlib import Path
import pandas as pd

import astropy.units as u

import click

from unitpackage.entry import Entry

logger = logging.getLogger("echemdb_ecdata")


class DataDescription:

    def __init__(self, data_description_dict):
        self.original_filename = data_description_dict.get("originalFilename", None)
        self.type = data_description_dict.get("type", None)
        self.measurement_type = data_description_dict.get("measurementType", None)
        self.scan_rate = data_description_dict.get("scanRate", None)
        self.comment = data_description_dict.get("comment", None)
        self.dialect = Dialect(data_description_dict.get("dialect", None))
        self.field_mapping = data_description_dict.get("fieldMapping", None)
        self.field_units = data_description_dict.get("fieldUnits", None)

class Dialect:

    def __init__(self, dialect_dict):
        self.delimiters = dialect_dict.get("delimiters", None)
        self.decimal = dialect_dict.get("decimal", None)
        self.column_header_lines = dialect_dict.get("columnHeaderLines", None)
        self.header_lines = dialect_dict.get("headerLines", None)
        self.encoding = dialect_dict.get("encoding", None)



@click.group(help=__doc__.split("EXAMPLES")[0])
def cli():
    r"""
    Entry point of the command line interface.

    This redirects to the individual commands listed below.
    """


@click.command(name="raw")
@click.argument("csv", type=click.Path(exists=True))
@click.option(
    "--outdir",
    type=click.Path(file_okay=False),
    default="./data/generated/rawdata/",
    help="write output files to this directory",
)
@click.option(
    "--metadata", type=click.Path(exists=True), default=None, help="yaml file with metadata"
)
def convert(csv, outdir, metadata):
    """
    Convert a file containing CSV data into a datapackage.
    \f

    EXAMPLES::

        >>> import os.path
        >>> from echemdb_ecdata.test.cli import invoke, TemporaryData
        >>> with TemporaryData("../**/default.csv") as directory:
        ...     invoke(cli, "csv", os.path.join(directory, "default.csv"), "--outdir", "test/generated/loaders/")

    TESTS:

    The command can be invoked on files in the current directory::

        >>> from echemdb_ecdata.test.cli import invoke, TemporaryData
        >>> cwd = os.getcwd()
        >>> with TemporaryData("../**/default.csv") as directory:
        ...     os.chdir(directory)
        ...     try:
        ...         invoke(cli, "csv", "default.csv", "--outdir", "test/generated/loaders/")
        ...     finally:
        ...         os.chdir(cwd)

    """
    import yaml

    csvpath = Path(csv)


    metadata_file = metadata if metadata else csvpath.with_suffix(".yaml")

    # Load metadata
    metadata = yaml.safe_load(open(metadata_file, 'r', encoding='utf-8'))
    data_description = DataDescription(metadata["dataDescription"])
    dialect = data_description.dialect
    fieldmapping = data_description.field_mapping
    field_units = data_description.field_units
    scanRate = data_description.scan_rate["value"] * u.Unit(data_description.scan_rate["unit"])

    # clean metadata and create figure description
    metadata.setdefault("figureDescription", {key: value for key, value in metadata["dataDescription"].items() if key not in ["fieldMapping", "fieldUnits", "dialect"]})

    del metadata["dataDescription"]


    # These sshould include a number of exceptions
    #    if metadata:
    #     metadata = yaml.load(metadata, Loader=yaml.SafeLoader)
    #     try:
    #         fields = metadata["figure description"]["fields"]
    #     except (KeyError, AttributeError):
    #         logger.warning("No units to the fields provided in the metadata")

    #construct entry

    raw_entry = Entry.from_csv(csv, **dialect.__dict__)
    raw_entry.metadata.from_dict({"echemdb": metadata})
    mapped_entry = raw_entry.rename_fields(fieldmapping)
    entry = mapped_entry.update_fields(field_units)
    entry.df.head()

    def add_time_axis(entry, scanRate):
        conversion_factor = (1 *u.Unit(entry.field_unit('E')) / (1* scanRate.unit)).decompose()
        # Calculate potential differences
        df = pd.DataFrame()
        df['diff_E'] = abs(entry.df['E'].diff())

        # Calculate time differences: dt = dE / (dE/dt) = dE / scan_rate
        df['dt'] = df['diff_E'] / scanRate.value * conversion_factor.value # in seconds

        # Calculate cumulative time starting from 0
        df['t'] = df['dt'].cumsum().fillna(0)

        # Add time column to entry
        new_entry = entry.add_columns(df['t'], new_fields=[{'name':'t', 'unit': str(conversion_factor.unit)}])
        return new_entry

    if not 't' in entry.df.columns:
        entry = add_time_axis(entry, scanRate)

    entry.metadata.echemdb["figureDescription"].__dict__.setdefault("fields", {})
    entry.metadata.echemdb["figureDescription"].__dict__["fields"] = entry.mutable_resource.schema.to_dict()["fields"]

    entry.save(outdir=outdir)


cli.add_command(convert)


# Register command docstrings for doctesting.
# Since commands are not functions anymore due to their decorator, their
# docstrings would otherwise be ignored.
__test__ = {
    name: command.__doc__ for (name, command) in cli.commands.items() if command.__doc__
}
