r"""
URL to a ZIP containing the latest echemdb electrochemistry data.
"""

# ********************************************************************
#  This file is part of electrochemistry-data.
#
#        Copyright (C) 2024 Albert Engstfeld
#
#  electrochemistry-data is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  electrochemistry-data is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with electrochemistry-data. If not, see <https://www.gnu.org/licenses/>.
# ********************************************************************

import os


def get_echemdb_database_url(version="0.3.0"):
    """Returns a URL to an asset of a certain version of the echemdb electrochemistry-data.

    EXAMPLES:

    By default a URL is returned with the most recent version::

        >>> from echemdb_ecdata.url import get_echemdb_database_url
        >>> get_echemdb_database_url()
        'https://github.com/echemdb/electrochemistry-data/releases/download/0.3.0/data-0.3.0.zip'

    A URL with a specific version can be created::

        >>> from echemdb_ecdata.url import get_echemdb_database_url
        >>> get_echemdb_database_url(version="0.3.0")
        'https://github.com/echemdb/electrochemistry-data/releases/download/0.3.0/data-0.3.0.zip'

    """
    return os.environ.get(
        "ECHEMDB_DATABASE_URL",
        f"https://github.com/echemdb/electrochemistry-data/releases/download/{version}/data-{version}.zip",
    )
