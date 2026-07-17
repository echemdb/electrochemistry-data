r"""
This module contains methods for validating identifiers and filenames
in the electrochemistry-data repository database.

The identifier naming convention is::

    {citationKey}_f{figure}_{curve}

where ``citationKey`` matches the BibTeX key in ``bibliography.bib``,
``figure`` is the figure label (e.g., ``4a``), and ``curve`` is a
unique descriptor for the curve within the figure (e.g., ``solid``,
``black``, ``1``).

EXAMPLES:

Validate identifiers of generated svgdigitizer data packages::

    >>> validate_generated_identifiers("data/generated/svgdigitizer")  # doctest: +SKIP

Validate input filenames for svgdigitizer data against the SVG and YAML metadata::

    >>> validate_svgdigitizer_input("literature/svgdigitizer")  # doctest: +SKIP

Validate input filenames for source data against the YAML metadata::

    >>> validate_source_data_input("literature/source_data")  # doctest: +SKIP

Validate only newly added entries compared to a base branch::

    >>> validate_new_input(base_ref="origin/main")  # doctest: +SKIP

"""

# ********************************************************************
#  This file is part of electrochemistry-data.
#
#        Copyright (C) 2025-2026 Albert Engstfeld
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

import glob
import json
import logging
import os
import subprocess
from pathlib import Path

import yaml
from astropy import units as astropy_units
from frictionless import Package
from svgdigitizer.svg import SVG
from svgdigitizer.svgfigure import SVGFigure
from svgdigitizer.svgplot import SVGPlot
from unitpackage.local import collect_datapackages

from echemdb_ecdata.bibliography import (
    _print_validation_summary,
    load_bib_keys,
    validate_bib_keys,
    validate_bib_utf8,
)

logger = logging.getLogger("echemdb_ecdata")

#: Default metadata-schema version used for validation and embedded in
#: generated data packages: a release tag of the
#: `metadata-schema repository <https://github.com/echemdb/metadata-schema>`_
#: (e.g. ``0.8.0``) or a branch name (e.g. ``main``).
#: Change this single value to update the version across all validation tasks.
#: Keep the ``mdstools`` git tag in ``pyproject.toml`` in sync with this value.
SCHEMA_VERSION = "0.8.3"


def _load_metadata_file(path):
    r"""
    Load a metadata file (YAML or JSON) into a dict.

    YAML is loaded with ``mdstools.schema.validator.load_yaml_metadata``, so
    unquoted dates (e.g. ``date: 2021-07-09``) stay plain strings as required
    for validation of string-typed schema fields.

    EXAMPLES::

        >>> import tempfile, os
        >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        ...     _ = f.write('{"key": "value"}')
        ...     name = f.name
        >>> _load_metadata_file(Path(name))
        {'key': 'value'}
        >>> os.unlink(name)

    """
    with open(path, encoding="utf-8") as f:
        if path.suffix == ".json":
            return json.load(f)
        # Imported lazily: mdstools requires Python >= 3.11 and is only
        # installed in the dev environment (see pyproject.toml).
        from mdstools.schema.validator import (  # pylint: disable=import-outside-toplevel
            load_yaml_metadata,
        )

        return load_yaml_metadata(f)


def _validation_messages(validator, data):
    r"""
    Return schema and instrument-reference error messages for ``data``.

    ``validator`` is a prepared ``jsonschema`` validator. In addition to its
    errors, this reports dangling instrument references in
    ``experimental.operationParameters`` control blocks, a cross-reference
    check provided by the metadata-schema tooling (``mdstools``) that JSON
    Schema itself cannot express.

    EXAMPLES::

        >>> import jsonschema  # doctest: +SKIP
        >>> _validation_messages(
        ...     jsonschema.Draft202012Validator({"type": "object"}), {})  # doctest: +SKIP
        []

    """
    # Imported lazily: mdstools requires Python >= 3.11 and is only installed
    # in the dev environment (see pyproject.toml).
    from mdstools.schema.validator import (  # pylint: disable=import-outside-toplevel
        validate_instrument_references,
    )

    messages = []
    for error in sorted(validator.iter_errors(data), key=lambda err: err.path):
        path = "/".join(str(part) for part in error.absolute_path) or "<root>"
        messages.append(f"{error.message} (at {path})")
    messages.extend(validate_instrument_references(data))
    return messages


def validate_schema(data_dir, schema_name, version=None, verbose=True):
    r"""
    Validate JSON or YAML files against a metadata schema.

    Uses the validation tools shipped with the
    `metadata-schema repository <https://github.com/echemdb/metadata-schema>`_
    (``mdstools``). The JSON Schema for ``schema_name`` is fetched once for
    ``version`` and all files are validated in-process. Besides plain JSON
    Schema validation this also runs the instrument-reference check
    (``operationParameters`` control blocks must reference an instrument
    declared in ``experimental.instrumentation``), which JSON Schema itself
    cannot express.

    Parameters
    ----------
    data_dir : str
        Directory to search recursively for files matching the schema type.
        For ``echemdb_package`` schema, searches for ``*.json`` files.
        For other schemas, searches for ``*.yaml`` files.
    schema_name : str
        Name of the schema (without ``.json`` extension), e.g.,
        ``echemdb_package``, ``svgdigitizer``, or ``source_data``.
    version : str or None
        Schema version: a metadata-schema release tag (e.g. ``0.8.0``) or a
        branch name (e.g. ``main``). Defaults to :data:`SCHEMA_VERSION` when
        ``None``.
    verbose : bool
        If ``True``, prints each file as it validates.

    Raises
    ------
    FileNotFoundError
        If no matching files are found in ``data_dir``.
    ValueError
        If schema validation fails for any file.

    EXAMPLES::

        >>> validate_schema("data/generated/svgdigitizer", "echemdb_package")  # doctest: +SKIP
        >>> validate_schema("literature/svgdigitizer", "svgdigitizer")  # doctest: +SKIP

    """
    if version is None:
        version = SCHEMA_VERSION

    data_path = Path(data_dir)
    ext = "*.json" if schema_name == "echemdb_package" else "*.yaml"
    files = sorted(data_path.rglob(ext))

    if not files:
        raise FileNotFoundError(
            f"No {ext} files found in {data_dir}. " f"Has the data been generated?"
        )

    # Imported lazily: mdstools requires Python >= 3.11 and is only installed
    # in the dev environment (see pyproject.toml).
    # pylint: disable=import-outside-toplevel
    import jsonschema
    from mdstools.schema import validator as mds_validator

    # pylint: enable=import-outside-toplevel
    # Fetch the schema (and, for package schemas, the Frictionless schemas it
    # references) once, then validate all files in-process. mdstools' public
    # ``validate()`` refetches the schema for every document, which is too slow
    # for hundreds of files.
    # pylint: disable=protected-access
    schema = mds_validator._fetch_remote_schema(schema_name, version=version)
    registry = mds_validator._build_remote_registry(schema_name)
    # pylint: enable=protected-access
    validator = jsonschema.validators.validator_for(schema)(schema, registry=registry)

    print(
        f"Validating {len(files)} {ext} file(s) in {data_dir} "
        f"against {schema_name} ({version})..."
    )

    failed_files = 0
    for file in files:
        messages = _validation_messages(validator, _load_metadata_file(file))
        if messages:
            failed_files += 1
            print(f"FAILED: {file}")
            print("\n".join(f"  - {message}" for message in messages))
        elif verbose:
            print(f"ok: {file}")

    if failed_files:
        raise ValueError(
            f"Schema validation failed for {failed_files} of "
            f"{len(files)} file(s). See output above for details."
        )


def _build_expected_identifier(citation_key, figure, curve):
    r"""
    Construct the expected identifier from metadata components.

    The identifier is built as ``{citationKey}_f{figure}_{curve}``,
    where spaces in the curve label are replaced with underscores.
    Figure and curve labels are lowercased for consistency
    (important for Windows filesystem compatibility).

    EXAMPLES::

        >>> _build_expected_identifier("atkin_2009_afm_13266", "4a", "solid")
        'atkin_2009_afm_13266_f4a_solid'

        >>> _build_expected_identifier("howlett_2006_electrochemistry_1483", "1", "Au_dashed")
        'howlett_2006_electrochemistry_1483_f1_au_dashed'

    Spaces in curve labels are replaced with underscores::

        >>> _build_expected_identifier("sandbeck_2019_dissolution_2997", "1", "solid red")
        'sandbeck_2019_dissolution_2997_f1_solid_red'

    Uppercase in figure/curve labels is lowercased::

        >>> _build_expected_identifier("briega_martos_2021_cation_48", "1Cs", "black")
        'briega_martos_2021_cation_48_f1cs_black'

        >>> _build_expected_identifier("lipkowski_1998_ionic_2875", "1a", "SO4")
        'lipkowski_1998_ionic_2875_f1a_so4'

        >>> _build_expected_identifier("schuett_2021_electrodeposition_20461", "S1", "blue")
        'schuett_2021_electrodeposition_20461_fs1_blue'

    """
    # Replace spaces with underscores in the curve label
    curve = curve.replace(" ", "_")
    # Lowercase figure and curve for filesystem consistency
    figure = figure.lower()
    curve = curve.lower()
    return f"{citation_key}_f{figure}_{curve}"


def _read_yaml_metadata(yaml_path):
    r"""
    Read and return the metadata from a YAML file.

    EXAMPLES::

        >>> import tempfile, os
        >>> content = (
        ...     "source:\\n  citationKey: test_2024_example_1"
        ...     "\\n  figure: '1a'\\n  curve: '1'\\n"
        ... )
        >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        ...     _ = f.write(content.encode().decode('unicode_escape'))
        ...     name = f.name
        >>> meta = _read_yaml_metadata(name)
        >>> meta['source']['citationKey']
        'test_2024_example_1'
        >>> os.unlink(name)

    """
    with open(yaml_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _read_svg_labels(svg_path):
    r"""
    Extract figure and curve labels from an SVG file using svgdigitizer.

    Returns a tuple ``(figure_label, curve_label)``.

    EXAMPLES::

        >>> from io import StringIO
        >>> import tempfile, os
        >>> svg_content = '''<svg>
        ...   <g>
        ...     <path d="M 0 200 L 0 100" />
        ...     <text x="0" y="200">E1: 0 V</text>
        ...   </g>
        ...   <g>
        ...     <path d="M 100 200 L 100 100" />
        ...     <text x="100" y="200">E2: 1 V</text>
        ...   </g>
        ...   <g>
        ...     <path d="M -100 100 L 0 100" />
        ...     <text x="-100" y="100">j1: 0 uA / cm2</text>
        ...   </g>
        ...   <g>
        ...     <path d="M -100 0 L 0 0" />
        ...     <text x="-100" y="0">j2: 1 uA / cm2</text>
        ...   </g>
        ...   <g>
        ...     <path d="M 0 100 L 100 0" />
        ...     <text x="0" y="0">curve: solid</text>
        ...   </g>
        ...   <text x="-200" y="330">scan rate: 50 mV / s</text>
        ...   <text x="-400" y="330">figure: 2b</text>
        ... </svg>'''
        >>> kw = dict(mode='w', suffix='.svg',
        ...     delete=False, encoding='utf-8')
        >>> with tempfile.NamedTemporaryFile(**kw) as f:
        ...     _ = f.write(svg_content)
        ...     name = f.name
        >>> _read_svg_labels(name)
        ('2b', 'solid')
        >>> os.unlink(name)

    """
    with open(svg_path, encoding="utf-8") as f:
        svg = SVG(f)
    plot = SVGPlot(svg)
    figure = SVGFigure(plot)
    return figure.figure_label, figure.curve_label


def validate_svgdigitizer_input(
    data_dir="literature/svgdigitizer",
    bib_path="literature/bibliography/bibliography.bib",
):
    r"""
    Validate filenames of svgdigitizer input data against metadata.

    For each YAML/SVG pair, this function:

    1. Reads the ``citationKey`` from the YAML file.
    2. Extracts the ``figure`` and ``curve`` labels from the SVG file.
    3. Constructs the expected identifier: ``{citationKey}_f{figure}_{curve}``.
    4. Compares the expected identifier to the actual filename.
    5. Verifies the directory name matches the ``citationKey``.
    6. Verifies the ``citationKey`` exists in ``bibliography.bib``.

    Returns a list of error messages (empty if all valid).
    Raises ``ValueError`` if any mismatches are found.

    EXAMPLES::

        >>> validate_svgdigitizer_input("literature/svgdigitizer")  # doctest: +SKIP

    """
    bib_keys = load_bib_keys(bib_path) if os.path.exists(bib_path) else set()

    errors = []
    checked = 0

    yaml_files = sorted(glob.glob(os.path.join(data_dir, "**/*.yaml"), recursive=True))

    if not yaml_files:
        raise FileNotFoundError(f"No YAML files found in {data_dir}")

    for yaml_file in yaml_files:
        yaml_path = Path(yaml_file)
        svg_path = yaml_path.with_suffix(".svg")

        if not svg_path.exists():
            errors.append(f"MISSING SVG: No matching SVG for {yaml_path}")
            continue

        actual_stem = yaml_path.stem

        # Read citationKey from YAML
        citation_key = (
            _read_yaml_metadata(yaml_path).get("source", {}).get("citationKey", "")
        )

        if not citation_key:
            errors.append(f"MISSING KEY: No citationKey in {yaml_path}")
            continue

        # Read figure/curve labels from SVG
        try:
            figure_label, curve_label = _read_svg_labels(svg_path)
        except Exception as e:  # pylint: disable=broad-exception-caught
            errors.append(f"SVG ERROR: Cannot parse {svg_path}: {e}")
            continue

        if not figure_label:
            errors.append(
                f"MISSING FIGURE: No figure label in SVG or YAML for {svg_path}"
            )

        if not curve_label:
            errors.append(f"MISSING CURVE: No curve label in SVG for {svg_path}")

        checked += 1

        # Validate citation key is in bibliography
        if bib_keys and citation_key not in bib_keys:
            errors.append(
                f"BIB MISMATCH: citationKey '{citation_key}' "
                f"not found in bibliography ({yaml_path})"
            )

        # Validate directory name matches citation key
        if yaml_path.parent.name != citation_key:
            errors.append(
                f"DIR MISMATCH: directory "
                f"'{yaml_path.parent.name}' != "
                f"citationKey '{citation_key}' ({yaml_path})"
            )

        # Validate filename matches expected identifier
        if figure_label and curve_label:
            expected_stem = _build_expected_identifier(
                citation_key, figure_label, curve_label
            )
            if actual_stem != expected_stem:
                errors.append(
                    f"FILENAME MISMATCH: '{actual_stem}' != "
                    f"expected '{expected_stem}' ({yaml_path})"
                )

        # Validate that filename starts with the citation key
        if not actual_stem.startswith(citation_key):
            errors.append(
                f"PREFIX MISMATCH: filename '{actual_stem}' does not start "
                f"with citationKey '{citation_key}' ({yaml_path})"
            )

    _print_validation_summary("svgdigitizer input", checked, errors)
    return errors


def validate_source_data_input(
    data_dir="literature/source_data",
    bib_path="literature/bibliography/bibliography.bib",
):
    r"""
    Validate filenames of source data input against YAML metadata.

    For each YAML file, this function:

    1. Reads ``citationKey``, ``figure``, and ``curve`` from the YAML.
    2. Constructs the expected identifier: ``{citationKey}_f{figure}_{curve}``.
    3. Compares the expected identifier to the actual filename.
    4. Verifies the directory name matches the ``citationKey``.
    5. Verifies the ``citationKey`` exists in ``bibliography.bib``.

    Returns a list of error messages (empty if all valid).
    Raises ``ValueError`` if any mismatches are found.

    EXAMPLES::

        >>> errors = validate_source_data_input("literature/source_data")  # doctest: +ELLIPSIS
        Validation of source data input: checked ... files, found 0 errors.

    """
    bib_keys = load_bib_keys(bib_path) if os.path.exists(bib_path) else set()

    errors = []
    checked = 0

    yaml_files = sorted(glob.glob(os.path.join(data_dir, "**/*.yaml"), recursive=True))

    if not yaml_files:
        raise FileNotFoundError(f"No YAML files found in {data_dir}")

    for yaml_file in yaml_files:
        yaml_path = Path(yaml_file)
        actual_stem = yaml_path.stem

        # Read metadata from YAML
        meta = _read_yaml_metadata(yaml_path)
        citation_key = meta.get("source", {}).get("citationKey", "")
        figure = meta.get("source", {}).get("figure", "")
        curve = str(meta.get("source", {}).get("curve", ""))

        if not citation_key:
            errors.append(f"MISSING KEY: No citationKey in {yaml_path}")
            continue

        checked += 1

        # Validate citation key is in bibliography
        if bib_keys and citation_key not in bib_keys:
            errors.append(
                f"BIB MISMATCH: citationKey '{citation_key}' "
                f"not found in bibliography ({yaml_path})"
            )

        # Validate directory name matches citation key
        if yaml_path.parent.name != citation_key:
            errors.append(
                f"DIR MISMATCH: directory "
                f"'{yaml_path.parent.name}' != "
                f"citationKey '{citation_key}' ({yaml_path})"
            )

        # Validate filename matches expected identifier
        if figure and curve:
            expected_stem = _build_expected_identifier(citation_key, figure, curve)
            if actual_stem != expected_stem:
                errors.append(
                    f"FILENAME MISMATCH: '{actual_stem}' != "
                    f"expected '{expected_stem}' ({yaml_path})"
                )
        else:
            if not figure:
                errors.append(
                    f"MISSING FIGURE: No 'figure' in source metadata ({yaml_path})"
                )
            if not curve:
                errors.append(
                    f"MISSING CURVE: No 'curve' in source metadata ({yaml_path})"
                )

        # Validate that filename starts with the citation key
        if not actual_stem.startswith(citation_key):
            errors.append(
                f"PREFIX MISMATCH: filename '{actual_stem}' does not start "
                f"with citationKey '{citation_key}' ({yaml_path})"
            )

        # Validate matching CSV exists
        csv_path = yaml_path.with_suffix(".csv")
        if not csv_path.exists():
            errors.append(f"MISSING CSV: No matching CSV for {yaml_path}")

    _print_validation_summary("source data input", checked, errors)
    return errors


def validate_generated_identifiers(data_dir="data/generated/svgdigitizer"):
    r"""
    Validate identifiers in generated data packages.

    For each resource in the generated data packages, this function:

    1. Reads the ``citationKey``, ``figure``, and ``curve`` from the
       resource metadata.
    2. Constructs the expected identifier: ``{citationKey}_f{figure}_{curve}``.
    3. Compares the expected identifier to the actual resource name.

    Returns a list of error messages (empty if all valid).
    Raises ``ValueError`` if any mismatches are found.

    EXAMPLES::

        >>> validate_generated_identifiers("data/generated/svgdigitizer")  # doctest: +SKIP

    """
    packages = collect_datapackages(data_dir)

    package = Package()
    for pack in packages:
        for resource in pack.resources:
            package.add_resource(resource)

    errors = []
    checked = 0

    for resource in package.resources:
        if resource.name == "echemdb":
            continue

        metadata = resource.custom["metadata"]["echemdb"]
        source = metadata.get("source", {})
        citation_key = source.get("citationKey", "")
        figure = source.get("figure", "")
        curve = str(source.get("curve", ""))

        if not citation_key:
            errors.append(f"MISSING KEY: No citationKey for resource '{resource.name}'")
            continue

        checked += 1

        if figure and curve:
            expected_identifier = _build_expected_identifier(
                citation_key, figure, curve
            )
            if expected_identifier != resource.name:
                errors.append(
                    f"ID MISMATCH: resource '{resource.name}' != "
                    f"expected '{expected_identifier}'"
                )
        else:
            if not figure:
                errors.append(
                    f"MISSING FIGURE: No figure in metadata "
                    f"for resource '{resource.name}'"
                )
            if not curve:
                errors.append(
                    f"MISSING CURVE: No curve in metadata "
                    f"for resource '{resource.name}'"
                )

    _print_validation_summary("generated identifiers", checked, errors)
    return errors


def validate_identifiers():
    r"""
    Run all input validation checks (svgdigitizer + source data).

    This is the main entry point called from the CLI task
    ``pixi run validate_identifiers``.

    EXAMPLES::

        >>> validate_identifiers()  # doctest: +SKIP

    """
    all_errors = []

    print("=" * 60)
    print("Validating svgdigitizer input filenames...")
    print("=" * 60)
    svg_errors = validate_svgdigitizer_input()
    all_errors.extend(svg_errors)

    print()
    print("=" * 60)
    print("Validating source data input filenames...")
    print("=" * 60)
    source_errors = validate_source_data_input()
    all_errors.extend(source_errors)

    if all_errors:
        raise ValueError(
            f"Validation failed with {len(all_errors)} error(s). "
            f"See output above for details."
        )

    print()
    print("All validations passed.")


def validate_citation_keys_in_bib(
    bib_path="literature/bibliography/bibliography.bib",
):
    r"""
    Validate that every ``citationKey`` referenced by a literature entry
    exists in the bibliography.

    This is a cross-cutting check that scans *all* svgdigitizer and source_data
    YAML files, regardless of which entries changed. It catches the case where a
    bibliography entry is removed or renamed while a still-present (but unchanged)
    data entry keeps referencing it — a mismatch that a changed-entries-only
    validation (see :func:`validate_new_input`) would miss.

    Returns a list of error messages (empty if all valid).

    EXAMPLES::

        >>> errors = validate_citation_keys_in_bib()  # doctest: +ELLIPSIS
        Validation of citation keys in bibliography: checked ... files, found ... errors.

    """
    bib_keys = load_bib_keys(bib_path) if os.path.exists(bib_path) else set()

    errors = []
    checked = 0

    patterns = [
        "literature/svgdigitizer/**/*.yaml",
        "literature/source_data/**/*.yaml",
    ]
    yaml_files = sorted(f for p in patterns for f in glob.glob(p, recursive=True))

    for yaml_file in yaml_files:
        yaml_path = Path(yaml_file)
        meta = _read_yaml_metadata(yaml_path)
        citation_key = meta.get("source", {}).get("citationKey", "")
        if not citation_key:
            continue
        checked += 1
        if bib_keys and citation_key not in bib_keys:
            errors.append(
                f"BIB MISMATCH: citationKey '{citation_key}' "
                f"not found in bibliography ({yaml_path})"
            )

    _print_validation_summary("citation keys in bibliography", checked, errors)
    return errors


#: Units that are established in the electrochemistry community but have no
#: astropy-parseable representation yet. They are tolerated by
#: :func:`validate_units` until a general solution is found, see
#: https://github.com/echemdb/electrochemistry-data/issues/176
KNOWN_UNPARSEABLE_UNITS = {"ppm", "ppb", "volume percent"}


def validate_units(literature_dir="literature"):
    r"""
    Validate that every ``unit`` in the YAML metadata below ``literature_dir``
    is parseable by astropy.

    Tools consuming the data, such as the website generator or unitpackage's
    ``quantity``, parse units with astropy. Unsupported units only fail once
    such a tool touches the field, long after the data was merged, so we catch
    them here at validation time instead.

    Units listed in :data:`KNOWN_UNPARSEABLE_UNITS` are tolerated.
    Returns a list of error messages.

    EXAMPLES::

        >>> validate_units()  # doctest: +SKIP
        Validation of units: checked 716 files, found 0 errors.
        []

    """
    checked = 0
    errors = []

    def _units(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "unit" and not isinstance(value, (dict, list)):
                    yield value
                else:
                    yield from _units(value)
        elif isinstance(obj, list):
            for item in obj:
                yield from _units(item)

    for yaml_file in sorted(glob.glob(f"{literature_dir}/**/*.yaml", recursive=True)):
        checked += 1
        with open(yaml_file, encoding="utf-8") as f:
            metadata = yaml.safe_load(f)
        for unit in _units(metadata):
            if str(unit) in KNOWN_UNPARSEABLE_UNITS:
                continue
            try:
                astropy_units.Unit(str(unit))
            except ValueError:
                errors.append(
                    f"UNIT: {unit!r} is not parseable by astropy ({yaml_file})"
                )

    _print_validation_summary("units", checked, errors)
    return errors


def validate_new_input(base_ref="origin/main"):
    r"""
    Validate added or modified entries in ``literature/`` compared to a base branch.

    Uses ``git diff`` to find directories added or modified in the current branch relative
    to ``base_ref``, then runs schema and filename validation on those directories only.

    Also validates the bibliography (cross-cutting, cannot be scoped to changed entries),
    including a full scan that every ``citationKey`` referenced by *any* svgdigitizer or
    source_data entry resolves to a bibliography entry (see
    :func:`validate_citation_keys_in_bib`).

    Parameters
    ----------
    base_ref : str
        The git reference to compare against, e.g., ``origin/main``.

    EXAMPLES::

        >>> validate_new_input(base_ref="origin/main")  # doctest: +SKIP

    """
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=AM", f"{base_ref}...HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    changed_files = result.stdout.splitlines()

    def _changed_dirs(prefix):
        dirs = set()
        for f in changed_files:
            parts = Path(f).parts
            if len(parts) >= 3 and f.startswith(prefix):
                dirs.add(str(Path(parts[0]) / parts[1] / parts[2]))
        return sorted(dirs)

    svg_dirs = _changed_dirs("literature/svgdigitizer/")
    src_dirs = _changed_dirs("literature/source_data/")

    if not svg_dirs and not src_dirs:
        print("No changed literature entries found.")
        return

    for data_dir in svg_dirs:
        print(f"\nValidating {data_dir} ...")
        validate_schema(data_dir, "svgdigitizer")
        validate_svgdigitizer_input(data_dir)

    for data_dir in src_dirs:
        print(f"\nValidating {data_dir} ...")
        validate_schema(data_dir, "source_data")
        validate_source_data_input(data_dir)

    print("\nValidating bibliography...")
    validate_bib_keys()
    validate_bib_utf8()

    # Cross-cutting: every citationKey referenced by *any* entry (not only the
    # changed ones) must resolve to a bibliography entry. This catches a bib
    # entry that was removed/renamed while an unchanged data entry still uses it.
    print("\nValidating citation-key references across all entries...")
    ref_errors = validate_citation_keys_in_bib()

    # Cross-cutting: every unit in *any* entry must be parseable by astropy
    # (except for the known exceptions in KNOWN_UNPARSEABLE_UNITS).
    print("\nValidating units across all entries...")
    unit_errors = validate_units()

    errors = ref_errors + unit_errors
    if errors:
        raise ValueError(
            f"Validation failed with {len(ref_errors)} citation-key reference "
            f"error(s) and {len(unit_errors)} unit error(s). "
            f"See output above for details."
        )
