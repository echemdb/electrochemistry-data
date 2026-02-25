# Electrochemistry-data

This repository contains data used for the creation of entries on [echemdb.org](https://wwww.echemdb.org/cv).
The data consist of frictionless based [`unitpackages`](https://echemdb.github.io/unitpackage/),
which were creared from SVG, YAML and bibtex (BIB) using [`svgdigitizer`](https://echemdb.github.io/svgdigitizer/).
All input YAML files and output DataPackages are validated against the [echemdb-metadata schema](https://github.com/echemdb/metadata-schema).

## Accessing Data

### Direct Download (Release Section)

The data can be downloaded as a ZIP from the [release section](https://github.com/echemdb/electrochemistry-data/releases).

### Unitpackage API

A collection can be created from the the [echemdb module](https://echemdb.github.io/unitpackage/usage/echemdb_usage.html) of the [`unitpackages`](https://echemdb.github.io/unitpackage/) interface
(see [`unitpackages` installation instructions](https://echemdb.github.io/unitpackage/installaton.html)).

```python
from unitpackage.database.echemdb import Echemdb
db = Echemdb.from_remote()
```

### Electrochemistry Data API

Install the latest version of the module.

```sh
pip install git+https://github.com/echemdb/electrochemistry-data.git
```

In your preferred Python environment retrieve the URL with the data via

```py
from echemdb_ecdata.url import ECHEMDB_DATABASE_URL
ECHEMDB_DATABASE_URL
```

## Contributing

The preparation and of the files and the extraction of the data from a PDF source is
described [here](https://echemdb.github.io/svgdigitizer/workflow.html).

## Development

If you want to work on the data and repository itself, install [pixi](https://pixi.sh)
and clone the repository:

```sh
git clone https://github.com/echemdb/electrochemistry-data.git
cd electrochemistry-data
```

For possible commands run

```sh
pixi run
```

More pixi tasks can be inferred from the [pyproject.toml](pyproject.toml).

### Conversion

The repository converts source data into standardized frictionless datapackages:

```sh
# Convert all data (SVG digitizer + raw data)
pixi run -e dev convert

# Convert only SVG digitizer data (from literature/svgdigitizer/)
pixi run -e dev convert-svg

# Convert only raw data (from literature/source_data/)
pixi run -e dev convert-raw

# Clean generated data before converting
pixi run -e dev clean-data
```

A typical workflow:

```sh
# Clean previous builds and convert all data
pixi run -e dev clean-data && pixi run -e dev convert
```

Generated datapackages are written to `data/generated/svgdigitizer/` and `data/generated/source_data/`.

### Validation

All data (input YAML and output JSON) is validated against the [echemdb-metadata schema](https://github.com/echemdb/metadata-schema).

```sh
# Validate input YAML files before conversion
pixi run -e dev validate-input

# Validate generated JSON datapackages after conversion
pixi run -e dev validate-generated
```

Each validation command shows verbose output listing all validated files. You can also validate specific parts:

```sh
# Individual input validation
pixi run -e dev validate-svgdigitizer-yaml  # SVG digitizer YAML files
pixi run -e dev validate-source-yaml        # Raw data YAML files

# Individual output validation
pixi run -e dev validate-svgdigitizer       # Generated SVG digitizer JSON
pixi run -e dev validate-raw                # Generated raw data JSON
```

Validate against a specific schema version:

```sh
pixi run -e dev validate-input --version tags/0.3.3
pixi run -e dev validate-generated --version head/my-branch
```
