# Electrochemistry-data

This repository contains data used for the creation of entries on [echemdb.org](https://wwww.echemdb.org/cv).
The data consist of SVG, YAML and BIB files which are converted into frictionless based
[`unitpackages`](https://echemdb.github.io/unitpackage/) using [`svgdigitizer`](https://echemdb.github.io/svgdigitizer/).
All input YAML files are validated against the [echemdb-metadata schema](https://github.com/echemdb/metadata-schema).

## Contributing

The preparation and of the files and the extraction of the data from a PDF source is
described [here](https://echemdb.github.io/svgdigitizer/workflow.html).

## Accessing Data

The resulting data can be downloaded as a ZIP from the release section.

Alternatively you can use the [`unitpackages`](https://echemdb.github.io/unitpackage/) interface
(see [`unitpackages` installation instructions](https://echemdb.github.io/unitpackage/installaton.html)).

## Create Data Locally

To create the output data packages locally clone the repository

```sh
git clone git@github.com:echemdb/electrochemistry-data.git
cd electrochemistry-data
```

Install dependencies via conda (or mamba).

```sh
conda create -f environment.yaml
conda activate echemdb-data
```

Run the makefile in the `data` folder.

```sh
cd data
make
```

To use multiple core use `make -j4` (in this case 4 cores).
