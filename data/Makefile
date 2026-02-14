# ********************************************************************
#  This file is part of echemdb.
#
#        Copyright (C) 2025 Albert Engstfeld
#        Copyright (C) 2022 Johannes Hermann
#        Copyright (C) 2022 Julian Rüth
#        Copyright (C) 2022 Nicolas Hörmann
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

SVGDIGITIZER=svgdigitizer
CP=cp

# The sampling interval at which we interpolate in volts.
SAMPLING_INTERVAL=.001

# The directory which we search for .yaml and .svg files to digitize.
SVG_SOURCE_DIR=../literature/svgdigitizer

# All the .yaml files in SVG_SOURCE_DIR directory and its subdirectories.
SVG_SOURCE_METADATA=${wildcard ${SVG_SOURCE_DIR}/**/*.yaml}

# All the .svg files corresponding to the SVG_SOURCE_METADATA .yaml files.
SVG_SOURCE_SVG=${patsubst %.yaml,%.svg,${SVG_SOURCES_METADATA}}

# The directory with the bibliography file
SOURCE_BIB=../literature/bibliography/bibliography.bib

# The files for the digitized .csv, .json, and .bib are written to this
# directory with the same subdirectory structure as they had in SVG_SOURCE_DIR.
SVG_TARGET_DIR=generated/svgdigitizer

TARGET_BIB_DIR = generated/bibliography

# The .csv files that we are going to generate from the .yaml and .svg files.
SVG_TARGET_CSV=${patsubst %.yaml,%.csv,${patsubst ${SVG_SOURCE_DIR}/%,${SVG_TARGET_DIR}/%,${wildcard ${SVG_SOURCE_DIR}/**/*.yaml}}}
# The .json files that we are going to generate from the .yaml and .svg files.
SVG_TARGET_JSON=${patsubst %.yaml,%.json,${patsubst ${SVG_SOURCE_DIR}/%,${SVG_TARGET_DIR}/%,${wildcard ${SVG_SOURCE_DIR}/**/*.yaml}}}

# The directory which we search for .yaml and .csv files for raw data conversion.
RAW_SOURCE_DIR=../literature/source_data

# All the .yaml files in RAW_SOURCE_DIR directory and its subdirectories.
RAW_SOURCE_METADATA=${wildcard ${RAW_SOURCE_DIR}/**/*.yaml}

# The directory where we write the converted raw data files.
RAW_TARGET_DIR=generated/source_data

# The .csv files that we are going to generate from the raw .yaml and .csv files.
RAW_TARGET_CSV=${patsubst %.yaml,%.csv,${patsubst ${RAW_SOURCE_DIR}/%,${RAW_TARGET_DIR}/%,${RAW_SOURCE_METADATA}}}
# The .json files that we are going to generate from the raw .yaml and .csv files.
RAW_TARGET_JSON=${patsubst %.yaml,%.json,${patsubst ${RAW_SOURCE_DIR}/%,${RAW_TARGET_DIR}/%,${RAW_SOURCE_METADATA}}}

# We create a data package, i.e., a .csv and a .json file, from a .yaml and a
# .svg files by invoking the svgdigitizer.
# We also include the bibliography data from the bibliography.bib file.
${SVG_TARGET_DIR}/%.csv ${SVG_TARGET_DIR}/%.json : ${SVG_SOURCE_DIR}/%.yaml ${SVG_SOURCE_DIR}/%.svg
	${SVGDIGITIZER} cv --sampling-interval ${SAMPLING_INTERVAL} --si-units \
		--bibliography ${SOURCE_BIB} --metadata $< ${patsubst %.yaml,%.svg,$<} \
		--outdir=${@D} 2>&1 | awk '{ print "'$<': "$$0 }'

# We create a data package, i.e., a .csv and a .json file, from a .yaml and a
# .csv files by invoking the echemdb_ecdata convert command.
${RAW_TARGET_DIR}/%.csv ${RAW_TARGET_DIR}/%.json : ${RAW_SOURCE_DIR}/%.yaml ${RAW_SOURCE_DIR}/%.csv
	@mkdir -p ${@D}
	pixi run -e dev echemdb_ecdata convert ${patsubst %.yaml,%.csv,$<} --metadata $< --outdir=${@D} 2>&1 | awk '{ print "'$<': "$$0 }'

# The default action when calling "make" is to digitize all the .yaml/.svg
# pairs and convert all raw data packages.
all: ${SVG_TARGET_CSV} ${SVG_TARGET_JSON} ${RAW_TARGET_CSV} ${RAW_TARGET_JSON}

# Convert all raw data packages only (without SVG digitization).
source_data: ${RAW_TARGET_CSV} ${RAW_TARGET_JSON}

# Digitize all SVG files only (without raw data conversion).
svg: ${SVG_TARGET_CSV} ${SVG_TARGET_JSON}

# Remove the entire generated directory to delete all the generated output.
clean:
	rm -rf ${SVG_TARGET_DIR} ${RAW_TARGET_DIR} ${TARGET_BIB_DIR}


.PHONY: all source_data svg clean
