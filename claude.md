# Electrochemistry Data - Context Guide for Claude

## Project Overview

This repository builds a database for published electrochemical data (echemdb.org). It converts data from scientific publications into standardized, machine-readable formats using the [frictionless data package](https://frictionless.io/) specification.

**Current Branch**: `conversion-performance` (batch conversion for SVG and source data)
**Main Dependencies**: svgdigitizer, unitpackage, pydantic, pybtex

## Repository Structure

### Source Data (`literature/`)

The source material is organized by publication:

- **`bibliography/bibliography.bib`** - BibTeX references for all publications
- **`svgdigitizer/[paper_key]/`** - Data extracted from figures in publications
  - `*.svg` - Digitized plot traces from figures
  - `*.yaml` - Metadata describing experimental conditions
  - `*.pdf` - Source publication PDFs
  - Example: `atkin_2009_afm_13266_f4a_solid.svg` (figure 4a, solid line)
- **`source_data/[paper_key]/`** - Raw experimental data files (CSV) with metadata
  - `*.csv` - Original raw data files
  - `*.yaml` - Metadata describing experimental setup and data structure
  - Example: `engstfeld_2018_polycrystalline_17743_f4b_1.yaml`

### Generated Data (`data/generated/`)

Processed data packages validated against the [echemdb-metadata schema](https://github.com/echemdb/metadata-schema):

- **`svgdigitizer/[paper_key]/`** - Converted data from SVG sources
  - `*.json` - Frictionless datapackage metadata
  - `*.csv` - Extracted tabular data
- **`source_data/[paper_key]/`** - Converted raw data submissions
  - `*.json` - Frictionless datapackage metadata
  - `*.csv` - Processed raw data

## YAML Metadata Structure

Both `svgdigitizer/` and `source_data/` YAML files follow similar structures but serve different purposes:

### Common Sections

```yaml
experimental:
  tags: [BCV, LSV, etc.]  # Experiment type tags
  instrumentation:
    - name: Biologic
      type: potentiostat

system:
  type: electrochemical
  electrodes:
    - name: WE  # Working electrode
      function: working electrode
      material: Au
      crystallographicOrientation: '111'
      geometricElectrolyteContactArea:
        value: 0.3
        unit: cm-2
    - name: CE  # Counter electrode
    - name: REF  # Reference electrode
  electrolyte:
    components:
      - name: KOH
        concentration:
          unit: mol / l
          value: 0.1
    temperature:
      unit: K
      value: 298.15

source:
  citationKey: atkin_2009_afm_13266  # Must match bibliography.bib
  url: https://doi.org/10.1021/jp9026755
  figure: 4a  # Figure reference
  curve: '1'  # Curve identifier

curation:
  process:
    - role: curator
      name: Jerome Mayer
      orcid: https://orcid.org/0000-0002-7451-9994
      date: 2022-01-10
```

### Additional for Raw Data (`source_data/`)

```yaml
dataDescription:
  type: raw  # Indicates raw experimental data
  measurementType: CV  # Cyclic Voltammetry
  scanRate:
    value: 50
    unit: mV / s
  dialect:  # CSV parsing information
    delimiters: ','
    decimal: '.'
    encoding: utf-8
    headerLines: 0
    columnHeaderLines: 2
  fieldMapping:  # Map original column names to standardized names
    'E / V vs. RHE': E
    'j / mA cm\+(-2)': j
  fieldUnits:
    - name: E
      unit: V
      reference: RHE
```

## Key Workflows

### Build Database from Source

```bash
# Clean previous builds
pixi run -e dev clean-data

# Convert SVG data (batch, single process)
pixi run -e dev convert-svg

# Convert raw data (batch, single process)
pixi run -e dev convert-raw

# Full conversion
pixi run -e dev convert

# Force full rebuild (ignore timestamps)
pixi run -e dev convert-force

# Verify batch output matches existing generated data
pixi run -e dev verify-svg
pixi run -e dev verify-raw
pixi run -e dev verify-all
```

### Validation

Two umbrella tasks cover all checks and are used in CI:

```bash
# Validate all input files (YAML schema + filenames/identifiers + bib keys)
pixi run -e dev validate-input

# Validate all generated files (JSON schema + identifiers)
pixi run -e dev validate-generated
```

Individual sub-tasks:

```bash
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

# Bibliography key and encoding validation
pixi run -e dev validate-bib-keys  # Check bib keys match expected identifiers
pixi run -e dev validate-bib-utf8  # Check for LaTeX accent encodings

# Use specific schema version (default: echemdb_ecdata.validate.SCHEMA_VERSION)
pixi run -e dev validate-input --version tags/0.3.3
pixi run -e dev validate-generated --version head/branch-name
```

Validation commands:
- Display each file being validated with `--verbose` flag
- Use Python `pathlib.rglob()` + `subprocess` for cross-platform compatibility
- Return non-zero exit code when validation fails or files are missing
- Validate against echemdb-metadata-schema (configurable version)

### Fix Utilities

```bash
# Lowercase SVG labels and filenames (enforced for Windows compatibility)
pixi run -e dev fix-lowercase          # Apply changes
pixi run -e dev fix-lowercase-dry-run  # Preview only

# Convert LaTeX accent encodings to UTF-8 in bibliography.bib
pixi run -e dev fix-bib-utf8           # Apply changes
pixi run -e dev fix-bib-utf8-dry-run   # Preview only

# Auto-fix identifier mismatches (detects dir name != YAML citationKey)
# Renames directories and files in both literature/svgdigitizer/ and data/generated/svgdigitizer/
pixi run -e dev fix-identifiers          # Apply changes
pixi run -e dev fix-identifiers-dry-run  # Preview only

# Rename directories and files after a bib key change (manual)
# Renames in both literature/svgdigitizer/ and data/generated/svgdigitizer/
pixi run -e dev rename-identifiers OLD_NAME NEW_NAME
# Or directly: bash util/rename_identifiers.sh OLD_NAME NEW_NAME
```

### Development Tasks

```bash
# Show all available commands
pixi run

# Run all tests (doctest + pytest)
pixi run -e dev test

# Use specific Python version
pixi run -e python-312 test
```

## Python API

### Access Published Database

```python
from unitpackage.database.echemdb import Echemdb
db = Echemdb.from_remote()
```

### Get Database URL

```python
from echemdb_ecdata.url import ECHEMDB_DATABASE_URL
print(ECHEMDB_DATABASE_URL)
```

## Naming Conventions

Files follow the pattern: `{citationKey}_f{figure}_{curve}.{ext}`

The `citationKey` is derived from the BibTeX entry using `svgdigitizer.pdf.Pdf.build_identifier` (author, year, slugified title keyword, starting page). All identifiers are enforced to be lowercase.

Examples:
- `engstfeld_2018_polycrystalline_17743_f4b_1.yaml` - Figure 4b, curve 1
- `atkin_2009_afm_13266_f4a_solid.svg` - Figure 4a, solid line

## Important Notes

- **Don't read all files in `literature/svgdigitizer/`** - There are 273+ entries. Sample a few to understand structure.
- **Schema validation** is critical - all generated JSON must validate against echemdb-metadata schema
- **Naming must match** - `citationKey` in YAML must match key in `bibliography.bib`, directory name, and filename prefix
- **Bib keys are computed** - Use `svgdigitizer.pdf.Pdf.build_identifier` + `pybtex` to derive expected keys from BibTeX entries
- **Lowercase enforced** - All identifiers, filenames, and SVG labels must be lowercase (Windows compatibility)
- **Raw data support** - `literature/source_data/` holds raw experimental data with CSV files and YAML metadata
- **Batch conversion** - Both SVG and source data conversion run in a single Python process via `echemdb_ecdata.digitize`, avoiding per-file import overhead (~3 s/file). Full rebuild: ~30-50 s instead of ~15 min

## Agent Workflow Notes (Tagging)

- **Source of truth for svgdigitizer tags**: tags are stored in `literature/svgdigitizer/**/*.svg` as a text field `tags: ...` (comma-separated).
- **Do not rely on YAML tags for svgdigitizer**: `experimental.tags` is intentionally removed from `literature/svgdigitizer/**/*.yaml`.
- **Why digest files are generated during curation**: to review proposed tag updates before bulk edits and to document the inference rationale in a reproducible way.
- **Do not commit internal digest artifacts** unless explicitly requested.

Tag inference rules used for SVG curation:
- Start from baseline `BCV` when no explicit reactant oxidation tag applies.
- Add `SHA` when electrolyte components include specific halide additives (e.g., `KCl`, `NaBr`, `KI`, `CsI`; but not oxyanions like `HClO4`/`KClO4`).
- Add reactant tags based on component names: `FAOR` (formic acid/formate), `COOR` (CO), `MOR` (methanol).
- Keep reaction-focused tags (e.g., `HER`, `OER`, `ORR`) only when explicitly justified by the entry context.

Practical reproducible workflow (no tables in repo docs):
- Parse `literature/svgdigitizer/**/*.yaml` to read electrolyte component names and electrolyte type (aqueous vs ionic liquid).
- Detect whether an SVG already has a `tags:` text node.
- For missing tag nodes, infer tags from components and inject `tags: ...` before `</svg>`.
- For existing tag nodes, update tag text in place and keep comma-separated format.
- Run `pixi run -e dev validate-input` after bulk edits.

## Related Documentation

- [svgdigitizer workflow](https://echemdb.github.io/svgdigitizer/workflow.html) - Data extraction process
- [unitpackage docs](https://echemdb.github.io/unitpackage/) - Data API
- [metadata schema](https://github.com/echemdb/metadata-schema) - Validation schema
- [echemdb.org](https://www.echemdb.org/cv) - Public database frontend

## Testing

Run all tests (includes doctest and pytest):
```bash
pixi run -e dev test
```

Tests validate:
- JSON schema compliance
- Data integrity
- Conversion processes
- YAML metadata correctness
- CLI functionality and output format
