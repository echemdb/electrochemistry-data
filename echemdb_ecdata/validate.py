r"""
This module contains additional methods for validating the data in the electrochemistry-data repository database.
"""

# ********************************************************************
#  This file is part of electrochemistry-data.
#
#        Copyright (C) 2025 Albert Engstfeld
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

def validate_identifier(resource):
    pass


def validate_identifiers(data_dir="data/generated/svgdigitizer"):
    from frictionless import Package
    from unitpackage.local import collect_datapackages
    packages = collect_datapackages(data_dir)

    package = Package()

    for pack in packages:
        for resource in pack.resources:
            package.add_resource(resource)


    data = {'source': [], 'figure': [], 'curve': [], "identifier": [], "expected_identifier": []}
    erroneous_data = [['expected_identifier',  'actual resource name']]

    for resource in package.resources:
        if resource.name != "echemdb":
            metadata = resource.custom["metadata"]["echemdb"]
            # collect metadata to construct an identifier
            key = metadata["source"]["citation key"]
            data["source"].append(key)
            figure = 'f' + metadata["source"]["figure"]
            data["figure"].append(figure)
            curve = metadata["source"]["curve"]
            data["curve"].append(curve)
            data["identifier"].append(resource.name)

            # construct an expected identifier
            expected_identifier = "_".join([key, figure, curve])
            data["expected_identifier"].append(expected_identifier)

            # validate the constructed identifier vs the expected identifier
            if not expected_identifier == resource.name:
                erroneous_data.append([expected_identifier, resource.name])

    if len(erroneous_data) > 1:
        for item in erroneous_data:
            print(item[0], ' - ', item[1])
        raise Exception("Invalid identifiers found.")

    return erroneous_data

import re
import os

def clean_and_replace_filename(file_path):
    # Extract directory and filename
    dir_name, old_filename = os.path.split(file_path)

    # Clean the filename
    new_filename = re.sub(r'_p\d+', '', old_filename)

    # Only rename if the filename changes
    if new_filename != old_filename:
        new_file_path = os.path.join(dir_name, new_filename)

        try:
            os.rename(file_path, new_file_path)
            print(f"Renamed: {old_filename} → {new_filename}")
        except Exception as e:
            print(f"Failed to rename {old_filename}: {e}")


def clean_and_replace_filenames(data_dir="data/generated/svgdigitizer"):
    import glob
    files = glob.glob(os.path.join(data_dir, "**/*.svg"), recursive=True)
    for file in files:
        clean_and_replace_filename(file)
