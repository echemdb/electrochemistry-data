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
import logging
import os
import re
import subprocess
from pathlib import Path

import yaml
from frictionless import Package
from svgdigitizer.svg import SVG
from svgdigitizer.svgfigure import SVGFigure
from svgdigitizer.svgplot import SVGPlot
from unitpackage.local import collect_datapackages

from echemdb_ecdata.bibliography import (
    _print_validation_summary,
    load_bib_keys,
)

logger = logging.getLogger("echemdb_ecdata")

_SCHEMA_BASE = "https://raw.githubusercontent.com/echemdb/metadata-schema/refs"

#: Default metadata-schema version used for validation.
#: Change this single value to update the version across all validation tasks.
SCHEMA_VERSION = "tags/0.5.1"


def validate_schema(data_dir, schema_name, version=None, verbose=True):
    r"""
    Validate JSON or YAML files against a metadata schema using check-jsonschema.

    This is a cross-platform replacement for the ``find | xargs check-jsonschema``
    pipeline that fails on Windows (where ``find.exe`` is a different tool).

    Parameters
    ----------
    data_dir : str
        Directory to search recursively for files matching the schema type.
        For ``echemdb_package`` schema, searches for ``*.json`` files.
        For other schemas, searches for ``*.yaml`` files.
    schema_name : str
        Name of the schema file (without ``.json`` extension), e.g.,
        ``echemdb_package``, ``svgdigitizer``, or ``source_data``.
    version : str or None
        Schema version reference, e.g., ``tags/0.5.1`` or ``head/main``.
        Defaults to :data:`SCHEMA_VERSION` when ``None``.
    verbose : bool
        If ``True``, passes ``--verbose`` to ``check-jsonschema``.

    Raises
    ------
    FileNotFoundError
        If no matching files are found in ``data_dir``.
    subprocess.CalledProcessError
        If schema validation fails.

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

    schema_url = f"{_SCHEMA_BASE}/{version}/schemas/{schema_name}.json"

    cmd = [
        "check-jsonschema",
        "--schemafile",
        schema_url,
        "--base-uri",
        schema_url,
        "--no-cache",
    ]
    if verbose:
        cmd.append("--verbose")
    cmd.extend(str(f) for f in files)

    print(
        f"Validating {len(files)} {ext} file(s) in {data_dir} "
        f"against {schema_name} ({version})..."
    )
    subprocess.run(cmd, check=True)


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


def _lowercase_svg_labels(svg_path):
    r"""
    Lowercase the figure and curve text labels inside an SVG file.

    Modifies the SVG in place. Only changes ``<text>`` elements
    matching ``figure: ...`` or ``curve: ...`` patterns.

    EXAMPLES::

        >>> import tempfile, os
        >>> svg = '<svg><text>figure: 1Cs</text><text>curve: Au_solid</text></svg>'
        >>> kw = dict(mode='w', suffix='.svg',
        ...     delete=False, encoding='utf-8')
        >>> with tempfile.NamedTemporaryFile(**kw) as f:
        ...     _ = f.write(svg)
        ...     name = f.name
        >>> _lowercase_svg_labels(name)
        True
        >>> with open(name, encoding='utf-8') as f:
        ...     print(f.read())
        <svg><text>figure: 1cs</text><text>curve: au_solid</text></svg>
        >>> os.unlink(name)

    Returns ``False`` if nothing changed::

        >>> import tempfile, os
        >>> svg = '<svg><text>figure: 1a</text><text>curve: solid</text></svg>'
        >>> with tempfile.NamedTemporaryFile(**kw) as f:
        ...     _ = f.write(svg)
        ...     name = f.name
        >>> _lowercase_svg_labels(name)
        False
        >>> os.unlink(name)

    """
    with open(svg_path, encoding="utf-8") as f:
        content = f.read()

    def _lower_label(match):
        return match.group(1) + match.group(2).lower()

    new_content = re.sub(r"((?:figure|curve):\s*)([^<]+)", _lower_label, content)

    if new_content != content:
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    return False


def _git_mv_lowercase(file_path):
    r"""
    Rename a file to its lowercase version using ``git mv``.

    On Windows, case-only renames require a two-step process
    (file → temp → lowercase) because the filesystem is
    case-insensitive.

    Returns ``True`` if the file was renamed, ``False`` if already
    lowercase.
    """
    path = Path(file_path)
    lower_name = path.name.lower()

    if path.name == lower_name:
        return False

    # Two-step rename for Windows case-insensitive filesystem
    tmp_path = path.with_name(path.name + "_tmp_rename")
    target_path = path.with_name(lower_name)

    subprocess.run(
        ["git", "mv", str(path), str(tmp_path)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "mv", str(tmp_path), str(target_path)],
        check=True,
        capture_output=True,
    )
    return True


def lowercase_svgdigitizer_files(  # pylint: disable=too-many-locals,too-many-branches
    data_dir="literature/svgdigitizer",
    dry_run=False,
):
    r"""
    Fix uppercase in svgdigitizer SVG labels and filenames.

    This function:

    1. Lowercases ``figure:`` and ``curve:`` text labels inside SVG files.
    2. Renames files (both ``.svg`` and ``.yaml``) to lowercase using
       ``git mv`` (two-step for Windows compatibility).

    Use ``dry_run=True`` to preview changes without modifying anything.

    EXAMPLES::

        >>> lowercase_svgdigitizer_files(dry_run=True)  # doctest: +SKIP

    """
    yaml_files = sorted(glob.glob(os.path.join(data_dir, "**/*.yaml"), recursive=True))
    changes = []

    for yaml_file in yaml_files:
        yaml_path = Path(yaml_file)
        svg_path = yaml_path.with_suffix(".svg")

        if not svg_path.exists():
            continue

        stem = yaml_path.stem
        lower_stem = stem.lower()
        needs_rename = stem != lower_stem

        # Check SVG labels
        with open(svg_path, encoding="utf-8") as f:
            content = f.read()
        svg_has_upper = bool(re.search(r"(?:figure|curve):\s*[^<]*[A-Z]", content))

        if not needs_rename and not svg_has_upper:
            continue

        if svg_has_upper:
            changes.append(f"SVG LABELS: {svg_path}")
        if needs_rename:
            changes.append(f"RENAME: {stem}.yaml -> {lower_stem}.yaml")
            changes.append(f"RENAME: {stem}.svg -> {lower_stem}.svg")

        if dry_run:
            continue

        # Fix SVG labels first (before rename)
        if svg_has_upper:
            _lowercase_svg_labels(svg_path)
            print(f"Fixed SVG labels: {svg_path}")

        # Rename files
        if needs_rename:
            for ext in [".yaml", ".svg"]:
                filepath = yaml_path.with_suffix(ext)
                if filepath.exists():
                    renamed = _git_mv_lowercase(filepath)
                    if renamed:
                        print(f"Renamed: {filepath.name} -> {filepath.name.lower()}")

    if dry_run:
        if changes:
            print(f"Dry run: {len(changes)} changes needed:")
            for c in changes:
                print(f"  {c}")
        else:
            print("Dry run: no changes needed.")

    return changes


def _rename_directory(old_dir, new_dir, old_name, new_name, dry_run=False):
    r"""
    Rename a directory and all files whose names contain ``old_name``.

    Tracked files are renamed with ``git mv`` (two-step for Windows
    case-insensitive filesystem).  Untracked files are renamed with
    plain ``os.rename``.

    Returns a list of human-readable change descriptions.
    """
    changes = []
    old_path = Path(old_dir)
    new_path = Path(new_dir)

    if not old_path.exists():
        return changes

    # Rename files inside the directory first
    for filepath in sorted(old_path.iterdir()):
        old_basename = filepath.name
        new_basename = old_basename.replace(old_name, new_name)
        if old_basename == new_basename:
            continue

        changes.append(f"  FILE: {old_basename} -> {new_basename}")
        if dry_run:
            continue

        # Check if file is tracked by git
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(filepath)],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            # Two-step rename for Windows case-insensitive filesystem
            tmp = filepath.with_name(old_basename + ".tmp_rename")
            subprocess.run(
                ["git", "mv", str(filepath), str(tmp)],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "mv", str(tmp), str(old_path / new_basename)],
                check=True,
                capture_output=True,
            )
        else:
            os.rename(filepath, old_path / new_basename)

    # Rename the directory itself
    changes.append(f"  DIR:  {old_path.name}/ -> {new_path.name}/")
    if not dry_run:
        # Check if directory has tracked files
        result = subprocess.run(
            ["git", "ls-files", str(old_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout.strip():
            tmp_dir = old_path.with_name(old_path.name + ".tmp_rename")
            subprocess.run(
                ["git", "mv", str(old_path), str(tmp_dir)],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "mv", str(tmp_dir), str(new_path)],
                check=True,
                capture_output=True,
            )
        else:
            os.rename(old_path, new_path)

    return changes


def fix_identifiers(  # pylint: disable=too-many-locals,too-many-branches
    data_dir="literature/svgdigitizer",
    generated_dir="data/generated/svgdigitizer",
    dry_run=False,
):
    r"""
    Automatically detect and fix directory/file name mismatches.

    Scans all YAML files in ``data_dir``, reads each ``citationKey``,
    and compares it to the parent directory name.  When they differ,
    renames the directory and all contained files (in both the input
    and generated trees) to match the ``citationKey``.

    Uses ``git mv`` with a two-step rename for Windows compatibility.
    Untracked files (e.g. PDFs) are renamed with plain ``os.rename``.

    Use ``dry_run=True`` to preview changes without modifying anything.

    EXAMPLES::

        >>> fix_identifiers(dry_run=True)  # doctest: +SKIP

    """
    yaml_files = sorted(glob.glob(os.path.join(data_dir, "**/*.yaml"), recursive=True))

    if not yaml_files:
        raise FileNotFoundError(f"No YAML files found in {data_dir}")

    # Collect unique directory-level mismatches (one per directory)
    mismatches = {}  # old_dir_name -> new_dir_name (citationKey)
    for yaml_file in yaml_files:
        yaml_path = Path(yaml_file)
        citation_key = (
            _read_yaml_metadata(yaml_path).get("source", {}).get("citationKey", "")
        )
        if not citation_key:
            continue
        dir_name = yaml_path.parent.name
        if dir_name != citation_key and dir_name not in mismatches:
            mismatches[dir_name] = citation_key

    if not mismatches:
        print("No identifier mismatches found. Everything is up to date.")
        return []

    all_changes = []
    for old_name, new_name in sorted(mismatches.items()):
        print(f"{'[DRY RUN] ' if dry_run else ''}RENAME: {old_name} -> {new_name}")

        # Rename in literature/svgdigitizer/
        old_dir = os.path.join(data_dir, old_name)
        new_dir = os.path.join(data_dir, new_name)
        changes = _rename_directory(old_dir, new_dir, old_name, new_name, dry_run)
        for c in changes:
            print(c)
        all_changes.extend(changes)

        # Rename in data/generated/svgdigitizer/
        old_gen = os.path.join(generated_dir, old_name)
        new_gen = os.path.join(generated_dir, new_name)
        if Path(old_gen).exists():
            changes = _rename_directory(
                old_gen,
                new_gen,
                old_name,
                new_name,
                dry_run,
            )
            for c in changes:
                print(c)
            all_changes.extend(changes)

    action = "would rename" if dry_run else "renamed"
    n = len(mismatches)
    print(f"\n{n} director{'y' if n == 1 else 'ies'} {action}.")
    return all_changes
