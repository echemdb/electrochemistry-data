# Electrochemistry-data

This repository contains data used for the creation of entries on [echemdb.org](https://wwww.echemdb.org/cv).
The data consist of SVG, YAML and BIB files which are converted into frictionless based
[`unitpackages`](https://echemdb.github.io/unitpackage/) using [`svgdigitizer`](https://echemdb.github.io/svgdigitizer/).
All input YAML files are validated against the [echemdb-metadata schema](https://github.com/echemdb/metadata-schema).

## Contributing

The preparation and of the files and the extraction of the data from a PDF source is
described [here](https://echemdb.github.io/svgdigitizer/workflow.html).

## Accessing Data

***Direct download***

The resulting data can be downloaded as a ZIP from the release section.

Alternatively you can use the [`unitpackages`](https://echemdb.github.io/unitpackage/) interface
(see [`unitpackages` installation instructions](https://echemdb.github.io/unitpackage/installaton.html)).

***From the API***

Install the latest version of the module.

```sh
pip install git@github.com:echemdb/electrochemistry-data.git
```

In your preferred Python environment retrieve the URL via

```py
from echemdb_ecdata.url import ECHEMDB_DATABASE_URL
ECHEMDB_DATABASE_URL
```

## Development

Clone the repository

```sh
git clone git+pip install git@github.com:echemdb/electrochemistry-data.git
cd electrochemistry-data
```

Install dependencies via conda (or mamba).

```sh
conda create -f environment.yaml
conda activate echemdb-data
```

***Create data locally***

Run the makefile in the `data` folder to create data locally.

```sh
cd data
make
```

To use multiple core use `make -j4` (in this case 4 cores).
