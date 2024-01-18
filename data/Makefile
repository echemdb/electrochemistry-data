# ********************************************************************
#  This file is part of echemdb.
#
#        Copyright (C) 2022 Albert Engstfeld
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
SOURCE_DIR=../literature

# All the .yaml files in SOURCE_DIR directory and its subdirectories.
SOURCE_METADATA=${wildcard ${SOURCE_DIR}/**/*.yaml}

# All the .svg files corresponding to the SOURCE_METADATA .yaml files.
SOURCE_SVG=${patsubst %.yaml,%.svg,${SOURCES_METADATA}}

# The files for the digitized .csv, .json, and .bib are written to this
# directory with the same subdirectory structure as they had in SOURCE_DIR.
TARGET_DIR=generated/svgdigitizer

# The .csv files that we are going to generate from the .yaml and .svg files.
TARGET_CSV=${patsubst %.yaml,%.csv,${patsubst ${SOURCE_DIR}/%,${TARGET_DIR}/%,${wildcard ${SOURCE_DIR}/**/*.yaml}}}
# The .json files that we are going to generate from the .yaml and .svg files.
TARGET_JSON=${patsubst %.yaml,%.json,${patsubst ${SOURCE_DIR}/%,${TARGET_DIR}/%,${wildcard ${SOURCE_DIR}/**/*.yaml}}}
# The .bib files that we are going to create, the same .bib files that were present in SOURCE_DIR.
TARGET_BIB=${patsubst ${SOURCE_DIR}/%,${TARGET_DIR}/%,${wildcard ${SOURCE_DIR}/**/*.bib}}

# We create a data package, i.e., a .csv and a .json file, from a .yaml and a
# .svg files by invoking the svgdigitizer.
${TARGET_DIR}/%.csv ${TARGET_DIR}/%.json : ${SOURCE_DIR}/%.yaml ${SOURCE_DIR}/%.svg
	${SVGDIGITIZER} cv --sampling-interval ${SAMPLING_INTERVAL} --si-units --bibliography --metadata $< ${patsubst %.yaml,%.svg,$<} --outdir=${@D} 2>&1 | awk '{ print "'$<': "$$0 }'

# We create a .bib file describing a publication by copying the .bib file from SOURCE_DIR to TARGET_DIR.
${TARGET_DIR}/%.bib: ${SOURCE_DIR}/%.bib
	@mkdir -p ${@D}
	${CP} $< $@

# The default action when calling "make" is to digitize all the .yaml/.svg
# pairs and copy over all the .bib files.
all: ${TARGET_CSV} ${TARGET_JSON} ${TARGET_BIB}

# Remove the entire TARGET_DIR to delete all the generated output.
clean:
	rm -rf ${TARGET_DIR}


.PHONY: all clean
