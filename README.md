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
and get a copy of the latest unreleased version of the metadata-schema:

```sh
git clone https://github.com/echemdb/electrochemistry-data.git
cd metadata-schema
```

For possible commands run

```sh
pixi run
```

Enable pre commit hooks

```sh
pixi run -e dev pre-commit install
```

When you commit changes, for example to `config.toml`, the pre-commit hook automatically:

1. Reads the `schema.version` from `config.toml`
2. Updates all `"default" = "tags/X.Y.Z"` values in `pyproject.toml` to match

To commit without running the hook (not recommended):

```bash
git commit --no-verify
```

More pixi tasks can be inferred from the [pyproject.toml](pyproject.toml).
