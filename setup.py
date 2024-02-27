# ********************************************************************
#  This file is part of electrochemistry-data.
#
#        Copyright (C)      2024 Albert Engstfeld
#
#  echemdb is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  echemdb is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with echemdb. If not, see <https://www.gnu.org/licenses/>.
# ********************************************************************

from distutils.core import setup

setup(
    name='electrochemistry_data',
    version="0.2.1",
    packages=['echemdb_ecdata'],
    license='GPL 3.0+',
    long_description=open('README.md').read(),
    include_package_data=True,
)
