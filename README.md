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

Both SVG digitization and raw data conversion use a batch approach that imports
heavy dependencies once and processes all files in a single Python process.
This avoids the ~3 s Python startup overhead per file that occurs when spawning
a subprocess for each file, reducing full-rebuild time from ~15 min to ~30-50 s
for 273 SVG files.

Force a full rebuild (ignoring timestamps):

```sh
pixi run -e dev convert-force
```

Verify that the batch conversion produces output identical to existing generated data:

```sh
pixi run -e dev verify-svg   # SVG digitizer output
pixi run -e dev verify-raw   # Source data output
pixi run -e dev verify-all   # Both at once
```

### Validation

All data (input YAML and output JSON) is validated against the [echemdb-metadata schema](https://github.com/echemdb/metadata-schema).
In addition, filenames, identifiers, and bibliography keys are validated for consistency.

Two umbrella tasks cover all checks:

```sh
# Validate all input files (YAML schema, filenames/identifiers, bib keys)
pixi run -e dev validate-input

# Validate all generated files (JSON schema, identifiers)
pixi run -e dev validate-generated
```

These are also used in the CI workflows. You can run individual sub-tasks:

```sh
# Schema validation
pixi run -e dev validate-svgdigitizer-yaml  # Input YAML (svgdigitizer)
pixi run -e dev validate-source-yaml        # Input YAML (source data)
pixi run -e dev validate-svgdigitizer       # Generated JSON (svgdigitizer)
pixi run -e dev validate-raw                # Generated JSON (source data)

# Filename and identifier validation
pixi run -e dev validate-identifiers              # All input filenames
pixi run -e dev validate-svgdigitizer-filenames   # SVG digitizer filenames only
pixi run -e dev validate-source-filenames         # Source data filenames only
pixi run -e dev validate-generated-identifiers    # Generated data identifiers

# Bibliography key validation
pixi run -e dev validate-bib-keys  # Check bib keys match expected identifiers
pixi run -e dev validate-bib-utf8  # Check for LaTeX accent encodings
```

Validate against a specific schema version:

```sh
pixi run -e dev validate-input --version tags/0.3.3
pixi run -e dev validate-generated --version head/my-branch
```

### Fix Utilities

```sh
# Lowercase SVG labels and filenames (enforced for Windows compatibility)
pixi run -e dev fix-lowercase          # Apply changes
pixi run -e dev fix-lowercase-dry-run  # Preview only

# Convert LaTeX accent encodings to UTF-8 in bibliography.bib
pixi run -e dev fix-bib-utf8           # Apply changes
pixi run -e dev fix-bib-utf8-dry-run   # Preview only

# Auto-fix identifier mismatches (detects dir name != YAML citationKey)
pixi run -e dev fix-identifiers          # Apply changes
pixi run -e dev fix-identifiers-dry-run  # Preview only

# Rename directories and files after a bib key change (manual)
pixi run -e dev rename-identifiers OLD_NAME NEW_NAME
```
