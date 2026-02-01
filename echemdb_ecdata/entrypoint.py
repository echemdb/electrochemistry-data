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

import astropy.units as u
import click
import pandas as pd
import yaml
from pydantic import BaseModel, ConfigDict, Field
from svgdigitizer.entrypoint import _create_bibliography
from unitpackage.entry import Entry

logger = logging.getLogger("echemdb_ecdata")


class Dialect(BaseModel):
    """Container for CSV dialect information."""

    model_config = ConfigDict(populate_by_name=True)

    delimiters: str | None = None
    decimal: str | None = None
    column_header_lines: int | None = Field(None, alias="columnHeaderLines")
    header_lines: int | None = Field(None, alias="headerLines")
    encoding: str | None = None


class DataDescription(BaseModel):
    """Container for data description metadata from YAML configuration."""

    model_config = ConfigDict(populate_by_name=True)

    original_filename: str | None = Field(None, alias="originalFilename")
    type: str | None = None
    measurement_type: str | None = Field(None, alias="measurementType")
    scan_rate: dict | None = Field(None, alias="scanRate")
    comment: str | None = None
    dialect: Dialect | None = None
    field_mapping: dict | None = Field(None, alias="fieldMapping")
    field_units: list | None = Field(None, alias="fieldUnits")


@click.group(help=__doc__.split("EXAMPLES", maxsplit=1)[0])
def cli():
    r"""
    Entry point of the command line interface.

    This redirects to the individual commands listed below.
    """


def _add_time_axis(entry, scan_rate):
    r"""
    Return an entry with an added time axis based on scan rate.

    This is a helper function for :func:`convert`.
    """
    conversion_factor = (
        1 * u.Unit(entry.field_unit("E")) / (1 * scan_rate.unit)
    ).decompose()
    # Calculate potential differences
    df = pd.DataFrame()
    df["diff_E"] = abs(entry.df["E"].diff())

    # Calculate time differences: dt = dE / (dE/dt) = dE / scan_rate
    df["dt"] = df["diff_E"] / scan_rate.value * conversion_factor.value  # in seconds

    # Calculate cumulative time starting from 0
    df["t"] = df["dt"].cumsum().fillna(0)

    # Add time column to entry
    new_entry = entry.add_columns(
        df["t"], new_fields=[{"name": "t", "unit": str(conversion_factor.unit)}]
    )
    return new_entry


def _add_bibdata_to_source(metadata, bibliography_data, new_citation_key):
    r"""
    Return metadata with added bibliography data to source.

    This is a helper function for :func:`convert`.
    """
    metadata.setdefault("source", {})
    metadata["source"].setdefault("bibdata", {})

    if metadata["source"]["bibdata"]:
        logger.warning(
            "The key with name `bibliography` in the metadata will be "
            "overwritten with the new bibliography data."
        )

    metadata["source"].update({"bibdata": bibliography_data})

    metadata["source"].setdefault("citationKey", {})

    if metadata["source"]["citationKey"]:
        if new_citation_key != metadata["source"]["citationKey"]:
            logger.warning(
                "Replace existing citation key in metadata with the new "
                "citation key '%s'.",
                new_citation_key,
            )

    metadata["source"].update({"citationKey": new_citation_key})
    return metadata


bibliography_option = click.option(
    "--bibliography",
    type=click.File("rb"),
    default="../literature/bibliography/bibliography.bib",
    help="BIB file with bibliography data to add to the datapackage.",
)


@click.command(name="raw")
@click.argument("csv", type=click.Path(exists=True))
@click.option(
    "--outdir",
    type=click.Path(file_okay=False),
    default="./data/generated/rawdata/",
    help="write output files to this directory",
)
@click.option(
    "--metadata",
    type=click.Path(exists=True),
    default=None,
    help="yaml file with metadata",
)
@bibliography_option
def convert(csv, outdir, metadata, bibliography):
    """
    Convert a file containing CSV data into a datapackage.
    \f

    EXAMPLES::

        >>> import os.path
        >>> from echemdb_ecdata.test.cli import invoke, TemporaryData
        >>> with TemporaryData("../**/default.csv") as directory:
        ...     invoke(cli, "csv", os.path.join(directory, "default.csv"),
        ... "--outdir", "test/generated/loaders/")

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
    # pylint: disable=too-many-locals

    csvpath = Path(csv)

    metadata_file = metadata if metadata else csvpath.with_suffix(".yaml")

    # Load metadata
    with open(metadata_file, "r", encoding="utf-8") as f:
        metadata_dict = yaml.safe_load(f)
    data_description = DataDescription.model_validate(metadata_dict["dataDescription"])
    dialect = data_description.dialect
    fieldmapping = data_description.field_mapping
    field_units = data_description.field_units
    scan_rate = data_description.scan_rate["value"] * u.Unit(
        data_description.scan_rate["unit"]
    )

    # clean metadata and create figure description
    metadata = metadata_dict.copy()
    metadata.setdefault(
        "figureDescription",
        {
            key: value
            for key, value in metadata_dict["dataDescription"].items()
            if key not in ["fieldMapping", "fieldUnits", "dialect"]
        },
    )

    del metadata["dataDescription"]

    # get bibliography data
    bibliography_data, new_citation_key = _create_bibliography(
        bibliography, citation_key=None, metadata=metadata
    )

    if bibliography_data:
        metadata = _add_bibdata_to_source(metadata, bibliography_data, new_citation_key)

    # We should include a number of exceptions
    #    if metadata:
    #     metadata = yaml.load(metadata, Loader=yaml.SafeLoader)
    #     try:
    #         fields = metadata["figure description"]["fields"]
    #     except (KeyError, AttributeError):
    #         logger.warning("No units to the fields provided in the metadata")

    # construct entry

    raw_entry = Entry.from_csv(csv, **dialect.__dict__)
    raw_entry.metadata.from_dict({"echemdb": metadata})
    mapped_entry = raw_entry.rename_fields(fieldmapping)
    entry = mapped_entry.update_fields(field_units)
    entry.df.head()

    # create a time axis if not present
    if "t" not in entry.df.columns:
        entry = _add_time_axis(entry, scan_rate)

    # update fields
    entry.metadata.echemdb["figureDescription"].__dict__.setdefault("fields", {})
    entry.metadata.echemdb["figureDescription"].__dict__[
        "fields"
    ] = entry.mutable_resource.schema.to_dict()["fields"]

    entry.save(outdir=outdir)


cli.add_command(convert)


# Register command docstrings for doctesting.
# Since commands are not functions anymore due to their decorator, their
# docstrings would otherwise be ignored.
__test__ = {
    name: command.__doc__ for (name, command) in cli.commands.items() if command.__doc__
}
