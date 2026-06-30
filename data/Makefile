# ********************************************************************
#  This file is part of echemdb.
#
#        Copyright (C)      2025 Albert Engstfeld
#        Copyright (C)      2022 Johannes Hermann
#        Copyright (C) 2022-2026 Julian Rüth
#        Copyright (C)      2022 Nicolas Hörmann
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

# The sampling interval at which we interpolate in volts.
SAMPLING_INTERVAL=.001

# The directory which we search for .yaml and .svg files to digitize.
SVG_SOURCE_DIR=../literature/svgdigitizer

# The directory with the bibliography file
SOURCE_BIB=../literature/bibliography/bibliography.bib

TARGET_DIR=generated

# The files for the digitized .csv, .json, and .bib are written to this
# directory with the same subdirectory structure as they had in SVG_SOURCE_DIR.
SVG_TARGET_DIR=${TARGET_DIR}/svgdigitizer

TARGET_BIB_DIR = ${TARGET_DIR}/bibliography

# The directory which we search for .yaml and .csv files for raw data conversion.
RAW_SOURCE_DIR=../literature/source_data

# The directory where we write the converted raw data files.
RAW_TARGET_DIR=${TARGET_DIR}/source_data

# Description of the possible licenses for the generated data
LICENSE_TARGETS = ${TARGET_DIR}/LICENSE.md ${TARGET_DIR}/LICENSE-GPL-3.0-or-later ${TARGET_DIR}/LICENSE-CC-BY-4.0 ${TARGET_DIR}/LICENSE-ODC-By-1.0

# The default action when calling "make" is to digitize all the .yaml/.svg
# pairs and convert all raw data packages.
all: svg source_data licenses

# Copy all licensing information into the generated data archive.
licenses: ${LICENSE_TARGETS}

# Ensures that the output directories exist. We use Python instead of `mkdir`
# so the recipe also works on Windows where Make cannot exec Unix utilities.
${TARGET_DIR}:
	python -c "import os, sys; os.makedirs(sys.argv[1], exist_ok=True)" "$@"

# We create data packages, i.e., .csv and .json files, from .yaml and .svg
# files by invoking the svgdigitizer via a batch Python function.
# This processes all files in a single Python process, avoiding the ~3s import
# overhead per file that occurs when calling `svgdigitizer cv` as a subprocess.
# The function has built-in timestamp checking (like Make's dependency tracking)
# to only rebuild files whose sources have changed.
svg: | ${TARGET_DIR}
	python -c "from echemdb_ecdata.digitize import digitize_svgdigitizer_data; digitize_svgdigitizer_data( \
		source_dir='${SVG_SOURCE_DIR}', \
		bibliography_path='${SOURCE_BIB}', \
		target_dir='${SVG_TARGET_DIR}', \
		sampling_interval=${SAMPLING_INTERVAL})"

# Force rebuild all SVG files regardless of timestamps.
svg-force: | ${TARGET_DIR}
	python -c "from echemdb_ecdata.digitize import digitize_svgdigitizer_data; digitize_svgdigitizer_data( \
		source_dir='${SVG_SOURCE_DIR}', \
		bibliography_path='${SOURCE_BIB}', \
		target_dir='${SVG_TARGET_DIR}', \
		sampling_interval=${SAMPLING_INTERVAL}, \
		force=True)"

# We create a data package, i.e., a .csv and a .json file, from a .yaml and a
# .csv files by invoking the batch Python conversion function.
# This processes all files in a single Python process, avoiding the ~3s import
# overhead per file that occurs when calling `echemdb_ecdata convert` as a subprocess.
source_data: | ${TARGET_DIR}
	python -c "from echemdb_ecdata.digitize import convert_source_data; convert_source_data( \
		source_dir='${RAW_SOURCE_DIR}', \
		bibliography_path='${SOURCE_BIB}', \
		target_dir='${RAW_TARGET_DIR}')"

# Force rebuild all source data files regardless of timestamps.
source_data-force: | ${TARGET_DIR}
	python -c "from echemdb_ecdata.digitize import convert_source_data; convert_source_data( \
		source_dir='${RAW_SOURCE_DIR}', \
		bibliography_path='${SOURCE_BIB}', \
		target_dir='${RAW_TARGET_DIR}', \
		force=True)"

# Copy licensing information into the generated data archive
${TARGET_DIR}/LICENSE.md: ../literature/LICENSE.md
${TARGET_DIR}/LICENSE-GPL-3.0-or-later: ../LICENSE
${TARGET_DIR}/LICENSE-CC-BY-4.0: ../LICENSE-CC-BY-4.0
${TARGET_DIR}/LICENSE-ODC-By-1.0: ../LICENSE-ODC-By-1.0


# We use Python instead of `cp` so the recipe also works on Windows where Make
# cannot exec Unix utilities.
${LICENSE_TARGETS}: | ${TARGET_DIR}
	python -c "import shutil, sys; shutil.copy(sys.argv[1], sys.argv[2])" "$<" "$@"

# Remove the entire generated directory to delete all the generated output.
clean:
	rm -rf ${TARGET_DIR}

.PHONY: all source_data source_data-force svg svg-force licenses clean
