r"""
Helpers for click CLI testing.

Click's own CliRunner is quite cumbersome to work with in some simple test
scenarios so we wrap it in more convenient ways here.

The code has been adapted from https://github.com/echemdb/svgdigitizer/.

"""

# *********************************************************************
#  This file is part of unitpackage.
#
#        Copyright (C) 2024-2026 Albert Engstfeld
#        Copyright (C) 2021-2024 Julian Rüth
#
#  unitpackage is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  unitpackage is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with unitpackage. If not, see <https://www.gnu.org/licenses/>.
# *********************************************************************

import glob
import json
import os
import os.path
import shutil
import tempfile

import pandas
import pandas.testing
import pytest
from click.testing import CliRunner

import echemdb_ecdata
from echemdb_ecdata.entrypoint import cli


def invoke(command, *args):
    r"""
    Invoke the click ``command`` with the given list of string arguments.

    >>> import click
    >>> @click.command()
    ... def hello(): print("Hello World")
    >>> invoke(hello)
    Hello World

    >>> @click.command()
    ... def fails(): raise Exception("expected error")
    >>> invoke(fails)
    Traceback (most recent call last):
    ...
    Exception: expected error

    """
    invocation = CliRunner().invoke(command, args, catch_exceptions=False)
    output = invocation.output.strip()
    if output:
        print(output)


class TemporaryData:
    r"""
    Provides a temporary directory with test files.

    EXAMPLES::

        >>> import os
        >>> with TemporaryData("**/default.*") as directory:
        ...     'default.csv' in os.listdir(directory)
        True

    """

    def __init__(self, *patterns):
        self._patterns = patterns
        self._tmpdir = None

    def __enter__(self):
        self._tmpdir = tempfile.TemporaryDirectory()

        try:
            cwd = os.getcwd()
            os.chdir(
                os.path.join(os.path.dirname(echemdb_ecdata.__file__), "..", "test")
            )
            try:
                for pattern in self._patterns:
                    for filename in glob.glob(pattern):
                        shutil.copy(filename, self._tmpdir.name)

                return self._tmpdir.name
            finally:
                os.chdir(cwd)

        except Exception:
            self._tmpdir.cleanup()
            raise

    def __exit__(self, *args):
        self._tmpdir.__exit__(*args)


@pytest.mark.parametrize(
    "name,args,use_bibliography",
    [
        (  # "Standard" CSV with a single column header line.
            "default",
            ["convert", "default.csv"],
            False,
        ),
        (  # CSV with multiple header lines.
            "multi_header_lines",
            ["convert", "multi_header_lines.csv"],
            False,
        ),
        (  # CVS with an empty column
            "empty_column",
            ["convert", "empty_column.csv"],
            False,
        ),
        (  # add bibliography
            "bibliography",
            [
                "convert",
                "bibliography.csv",
            ],
            True,
        ),
    ],
)
def test_convert(name, args, use_bibliography):
    r"""
    Test that the convert command from the command line interface works correctly.

    This function is executed by pytest and checks that "convert" produces JSON and
    CSV files that match expected outputs.
    """
    cwd = os.getcwd()
    test_output_dir = os.path.join(cwd, "test", "generated", "raw_data")
    bib_path = os.path.join(cwd, "literature", "bibliography", "bibliography.bib")

    patterns = [f"raw_data/{name}.*", f"generated/raw_data/{name}.*.expected"]
    if use_bibliography:
        patterns.append("../literature/bibliography/bibliography.bib")

    with TemporaryData(*patterns) as workdir:
        os.chdir(workdir)
        try:
            # Build command arguments
            temp_args = [*args, "--outdir", "generated/raw_data/"]
            persistent_args = [*args, "--outdir", test_output_dir]

            if use_bibliography:
                temp_args.extend(["--bibliography", "bibliography.bib"])
                persistent_args.extend(["--bibliography", bib_path])

            # Generate files in temporary directory for comparison
            invoke(cli, *temp_args)
            # Also generate files in the persistent test directory
            invoke(cli, *persistent_args)

            with open(f"generated/raw_data/{name}.json", encoding="utf-8") as actual:
                with open(f"{name}.json.expected", encoding="utf-8") as expected:
                    assert json.load(actual) == json.load(expected)

            pandas.testing.assert_frame_equal(
                pandas.read_csv(f"generated/raw_data/{name}.csv"),
                pandas.read_csv(f"{name}.csv.expected"),
            )
        finally:
            os.chdir(cwd)
