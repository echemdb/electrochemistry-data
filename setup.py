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

from distutils.core import setup

setup(
    name='echemdb_ecdata',
    version="0.3.0",
    packages=['echemdb_ecdata'],
    license='GPL 3.0+',
    description="a Python library to interact with a collection of frictionless datapackages",
    long_description=open('README.md', encoding="UTF-8").read(),
    long_description_content_type="text/markdown",
    include_package_data=True,
    install_requires=[
      "svgdigitizer>=0.11.0,<0.12.0",
    ],
    python_requires=">=3.9",
)
