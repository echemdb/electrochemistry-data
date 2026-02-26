r"""
Batch conversion of SVG and source data files.

This module provides functions to convert multiple files in a single Python
process, avoiding the overhead of importing heavy dependencies (astropy,
frictionless, pandas, etc.) on every invocation.

EXAMPLES:

Digitize all SVG/YAML pairs, writing output to `data/generated/svgdigitizer`::

    >>> from echemdb_ecdata.digitize import digitize_svgdigitizer_data
    >>> digitize_svgdigitizer_data(dry_run=True)  # doctest: +SKIP

Convert all source data files::

    >>> from echemdb_ecdata.digitize import convert_source_data
    >>> convert_source_data(dry_run=True)  # doctest: +SKIP

"""

# ********************************************************************
#  This file is part of echemdb_ecdata.
#
#        Copyright (C) 2026 Albert Engstfeld
#
#  echemdb_ecdata is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  echemdb_ecdata is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with echemdb_ecdata. If not, see <https://www.gnu.org/licenses/>.
# ********************************************************************
import logging
import os
import tempfile
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path

import astropy.units as u
import yaml
from pybtex.database import parse_file
from svgdigitizer.electrochemistry.cv import CV
from svgdigitizer.entrypoint import _create_package, _outfile, _write_metadata
from svgdigitizer.svg import SVG
from svgdigitizer.svgplot import SVGPlot

from echemdb_ecdata.entrypoint import (
    DataDescription,
    _add_bibdata_to_source,
    build_source_entry,
)

logger = logging.getLogger("echemdb_ecdata.digitize")

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _load_bibliography(bibliography_path):
    r"""Load a BibTeX bibliography file and return the parsed database, or None."""
    if not bibliography_path.exists():
        return None
    with open(bibliography_path, "rb") as fh:
        content = fh.read().decode("utf-8")
    return parse_file(StringIO(content), bib_format="bibtex")


def _compute_output_dir(yaml_path, source_dir, target_dir):
    r"""Compute the output directory preserving the subdirectory structure."""
    try:
        rel = yaml_path.parent.relative_to(source_dir.resolve())
    except ValueError:
        rel = Path(yaml_path.stem)
    return target_dir / rel


def _add_bib_to_metadata(metadata, bibdata, yaml_name):
    r"""
    Insert bibliography data into *metadata* if the citation key is found.

    Logs warnings when the key is missing or not found in the bibliography.
    """
    citation_key = metadata.get("source", {}).get("citationKey", "")

    if not bibdata:
        return

    if not citation_key:
        logger.warning("%s: no citationKey in metadata.", yaml_name)
        return

    if citation_key not in bibdata.entries:
        logger.warning(
            "%s: citation key '%s' not found in bibliography.",
            yaml_name,
            citation_key,
        )
        return

    metadata.setdefault("source", {})
    metadata["source"]["bibdata"] = bibdata.entries[citation_key].to_string("bibtex")
    metadata["source"]["citationKey"] = citation_key


def _print_summary(label, processed, skipped, errors, total):
    r"""Print a summary line after batch processing."""
    print(
        f"Done: {processed} {label}, {skipped} up-to-date, {errors} errors "
        f"(out of {total} total)"
    )


# ---------------------------------------------------------------------------
# Timestamp-based rebuild checks
# ---------------------------------------------------------------------------


def _needs_rebuild(yaml_path, companion_path, outdir):
    r"""
    Return whether the output files for a given YAML/companion pair are
    missing or older than their sources.

    This replicates Make's dependency tracking logic: rebuild if any
    output (.csv or .json) is missing or older than any input.
    """
    stem = Path(yaml_path).stem
    csv_out = Path(outdir) / f"{stem}.csv"
    json_out = Path(outdir) / f"{stem}.json"

    if not csv_out.exists() or not json_out.exists():
        return True

    source_mtime = max(os.path.getmtime(yaml_path), os.path.getmtime(companion_path))
    target_mtime = min(os.path.getmtime(csv_out), os.path.getmtime(json_out))

    return source_mtime > target_mtime


# ---------------------------------------------------------------------------
# SVG digitizer – per-file processing
# ---------------------------------------------------------------------------


@dataclass
class SvgDigitizerConfig:  # pylint: disable=too-many-instance-attributes
    r"""Configuration for SVG digitizer batch conversion."""

    source_dir: Path = field(
        default_factory=lambda: REPO_ROOT / "literature" / "svgdigitizer"
    )
    bibliography_path: Path = field(
        default_factory=lambda: (
            REPO_ROOT / "literature" / "bibliography" / "bibliography.bib"
        )
    )
    target_dir: Path = field(
        default_factory=lambda: (REPO_ROOT / "data" / "generated" / "svgdigitizer")
    )
    sampling_interval: float = 0.001
    si_units: bool = True
    skewed: bool = False
    force: bool = False
    dry_run: bool = False


def _compute_sampling(svg_path, config, algorithm):
    r"""Compute the actual sampling interval from the SVG x-axis unit."""
    with open(svg_path, "rb") as fh:
        cv_temp = CV(
            SVGPlot(SVG(fh), algorithm=algorithm),
            force_si_units=config.si_units,
        )
        x_unit = u.Unit(
            cv_temp.figure_schema.get_field(cv_temp.svgplot.xlabel).custom["unit"]
        )
        return config.sampling_interval / x_unit.to(u.V)  # pylint: disable=no-member


def _digitize_single_svg(yaml_path, svg_path, outdir, config, bibdata):
    r"""Digitize a single SVG/YAML pair, writing CSV and JSON output."""
    algorithm = "mark-aligned" if config.skewed else "axis-aligned"

    with open(yaml_path, "r", encoding="utf-8") as fh:
        metadata = yaml.load(fh, Loader=yaml.SafeLoader)

    actual_sampling = None
    if config.sampling_interval is not None:
        actual_sampling = _compute_sampling(svg_path, config, algorithm)

    with open(svg_path, "rb") as fh:
        svgfigure = CV(
            SVGPlot(
                SVG(fh),
                sampling_interval=actual_sampling,
                algorithm=algorithm,
            ),
            metadata=metadata,
            force_si_units=config.si_units,
        )

    os.makedirs(outdir, exist_ok=True)
    outdir_str = str(outdir)
    csvname = _outfile(str(svg_path), suffix=".csv", outdir=outdir_str)
    svgfigure.df.to_csv(csvname, index=False)

    _add_bib_to_metadata(svgfigure.metadata, bibdata, yaml_path.name)

    package = _create_package(svgfigure.metadata, csvname, outdir_str)
    json_out = _outfile(str(svg_path), suffix=".json", outdir=outdir_str)
    with open(json_out, mode="w", encoding="utf-8") as json_file:
        _write_metadata(json_file, package.to_dict())


# ---------------------------------------------------------------------------
# SVG digitizer – batch entry point
# ---------------------------------------------------------------------------


def digitize_svgdigitizer_data(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    source_dir=None,
    bibliography_path=None,
    target_dir=None,
    sampling_interval=0.001,
    si_units=True,
    skewed=False,
    force=False,
    dry_run=False,
    yaml_files=None,
):
    r"""
    Digitize multiple SVG/YAML file pairs in a single Python process.

    This avoids the ~3s import overhead per file that occurs when calling
    ``svgdigitizer cv`` as a subprocess for each file.

    Parameters
    ----------
    source_dir : str or Path or None
        Directory containing SVG/YAML source files (with subdirectories).
        Defaults to ``literature/svgdigitizer`` relative to the repository root.
    bibliography_path : str or Path or None
        Path to the bibliography .bib file.
        Defaults to ``literature/bibliography/bibliography.bib``.
    target_dir : str or Path or None
        Directory to write generated .csv and .json files.
        Defaults to ``data/generated/svgdigitizer``.
    sampling_interval : float
        Sampling interval in volts for interpolation. Default: 0.001.
    si_units : bool
        Whether to convert units to SI. Default: True.
    skewed : bool
        Whether to detect non-orthogonal skewed axes. Default: False.
    force : bool
        If True, rebuild all files regardless of timestamps.
    dry_run : bool
        If True, only print what would be done without actually digitizing.
    yaml_files : list of str or None
        If provided, only process these specific YAML files (absolute or
        relative paths). This is useful for Make-driven incremental builds
        that pass only the changed files.
    """
    config = SvgDigitizerConfig(
        source_dir=(
            Path(source_dir) if source_dir else SvgDigitizerConfig.source_dir.default
        ),
        bibliography_path=(
            Path(bibliography_path)
            if bibliography_path
            else SvgDigitizerConfig.bibliography_path.default
        ),
        target_dir=(
            Path(target_dir) if target_dir else SvgDigitizerConfig.target_dir.default
        ),
        sampling_interval=sampling_interval,
        si_units=si_units,
        skewed=skewed,
        force=force,
        dry_run=dry_run,
    )

    _run_svg_batch(config, yaml_files)


def _run_svg_batch(config, yaml_files=None):
    r"""Run the SVG digitizer batch with the given configuration."""
    yaml_paths = _collect_yaml_paths(config.source_dir, yaml_files)
    if not yaml_paths:
        logger.info("No YAML files found to process.")
        return

    bibdata = _load_bibliography(config.bibliography_path)

    processed, skipped, errors = 0, 0, 0

    for yaml_path in yaml_paths:
        yaml_path = Path(yaml_path).resolve()
        svg_path = yaml_path.with_suffix(".svg")

        if not svg_path.exists():
            skipped += 1
            continue

        outdir = _compute_output_dir(yaml_path, config.source_dir, config.target_dir)

        if not config.force and not _needs_rebuild(yaml_path, svg_path, outdir):
            skipped += 1
            continue

        if config.dry_run:
            print(
                f"Would digitize: {yaml_path.relative_to(config.source_dir.resolve())}"
            )
            processed += 1
            continue

        try:
            _digitize_single_svg(yaml_path, svg_path, outdir, config, bibdata)
            processed += 1
            print(f"Digitized: {yaml_path.relative_to(config.source_dir.resolve())}")
        except (OSError, ValueError, KeyError, yaml.YAMLError) as exc:
            logger.exception("Error digitizing %s: %s", yaml_path, exc)
            errors += 1

    _print_summary("digitized", processed, skipped, errors, len(yaml_paths))


# ---------------------------------------------------------------------------
# Source data – per-file processing
# ---------------------------------------------------------------------------


@dataclass
class SourceDataConfig:
    r"""Configuration for source data batch conversion."""

    source_dir: Path = field(
        default_factory=lambda: REPO_ROOT / "literature" / "source_data"
    )
    bibliography_path: Path = field(
        default_factory=lambda: REPO_ROOT
        / "literature"
        / "bibliography"
        / "bibliography.bib"
    )
    target_dir: Path = field(
        default_factory=lambda: REPO_ROOT / "data" / "generated" / "source_data"
    )
    force: bool = False
    dry_run: bool = False


def _convert_single_source(yaml_path, csv_path, outdir, bibdata):
    r"""Convert a single source data YAML/CSV pair, writing output."""
    with open(yaml_path, "r", encoding="utf-8") as fh:
        metadata_dict = yaml.safe_load(fh)

    data_description = DataDescription.model_validate(metadata_dict["dataDescription"])

    metadata = metadata_dict.copy()
    del metadata["dataDescription"]

    # Add bibliography data
    citation_key = metadata.get("source", {}).get("citationKey", "")
    if bibdata and citation_key and citation_key in bibdata.entries:
        bibliography_data = bibdata.entries[citation_key].to_string("bibtex")
        metadata = _add_bibdata_to_source(metadata, bibliography_data, citation_key)
    elif bibdata and citation_key and citation_key not in bibdata.entries:
        logger.warning(
            "%s: citation key '%s' not found in bibliography.",
            yaml_path.name,
            citation_key,
        )
    elif bibdata and not citation_key:
        logger.warning("%s: no citationKey in metadata.", yaml_path.name)

    entry = build_source_entry(csv_path, metadata, data_description)

    os.makedirs(outdir, exist_ok=True)
    entry.save(outdir=str(outdir))


# ---------------------------------------------------------------------------
# Source data – batch entry point
# ---------------------------------------------------------------------------


def convert_source_data(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    source_dir=None,
    bibliography_path=None,
    target_dir=None,
    force=False,
    dry_run=False,
    yaml_files=None,
):
    r"""
    Convert multiple source data YAML/CSV file pairs in a single Python process.

    This avoids the ~3s import overhead per file that occurs when calling
    ``echemdb_ecdata convert`` as a subprocess for each file.

    Parameters
    ----------
    source_dir : str or Path or None
        Directory containing source data YAML/CSV files (with subdirectories).
        Defaults to ``literature/source_data`` relative to the repository root.
    bibliography_path : str or Path or None
        Path to the bibliography .bib file.
        Defaults to ``literature/bibliography/bibliography.bib``.
    target_dir : str or Path or None
        Directory to write generated .csv and .json files.
        Defaults to ``data/generated/source_data``.
    force : bool
        If True, rebuild all files regardless of timestamps.
    dry_run : bool
        If True, only print what would be done without actually converting.
    yaml_files : list of str or None
        If provided, only process these specific YAML files.
    """
    config = SourceDataConfig(
        source_dir=(
            Path(source_dir) if source_dir else SourceDataConfig.source_dir.default
        ),
        bibliography_path=(
            Path(bibliography_path)
            if bibliography_path
            else SourceDataConfig.bibliography_path.default
        ),
        target_dir=(
            Path(target_dir) if target_dir else SourceDataConfig.target_dir.default
        ),
        force=force,
        dry_run=dry_run,
    )

    _run_source_batch(config, yaml_files)


def _run_source_batch(config, yaml_files=None):
    r"""Run the source data batch with the given configuration."""
    yaml_paths = _collect_yaml_paths(config.source_dir, yaml_files)
    if not yaml_paths:
        logger.info("No YAML files found to process.")
        return

    bibdata = _load_bibliography(config.bibliography_path)

    processed, skipped, errors = 0, 0, 0

    for yaml_path in yaml_paths:
        yaml_path = Path(yaml_path).resolve()
        csv_path = yaml_path.with_suffix(".csv")

        if not csv_path.exists():
            skipped += 1
            continue

        outdir = _compute_output_dir(yaml_path, config.source_dir, config.target_dir)

        if not config.force and not _needs_rebuild(yaml_path, csv_path, outdir):
            skipped += 1
            continue

        if config.dry_run:
            print(
                f"Would convert: {yaml_path.relative_to(config.source_dir.resolve())}"
            )
            processed += 1
            continue

        try:
            _convert_single_source(yaml_path, csv_path, outdir, bibdata)
            processed += 1
            print(f"Converted: {yaml_path.relative_to(config.source_dir.resolve())}")
        except (OSError, ValueError, KeyError, yaml.YAMLError) as exc:
            logger.exception("Error converting %s: %s", yaml_path, exc)
            errors += 1

    _print_summary("converted", processed, skipped, errors, len(yaml_paths))


# ---------------------------------------------------------------------------
# Shared YAML collection
# ---------------------------------------------------------------------------


def _collect_yaml_paths(source_dir, yaml_files=None):
    r"""Return a list of resolved YAML paths, either from *yaml_files* or by globbing."""
    if yaml_files:
        return [Path(f).resolve() for f in yaml_files]
    return sorted(source_dir.rglob("*.yaml"))


# ---------------------------------------------------------------------------
# Verification / comparison utilities
# ---------------------------------------------------------------------------


def _collect_output_files(directory):
    r"""Collect all .csv and .json relative paths under *directory*."""
    result = set()
    for ext in ("*.csv", "*.json"):
        for fpath in directory.rglob(ext):
            result.add(fpath.relative_to(directory))
    return result


def _compare_file_sets(ref_files, test_files, reference_dir, test_dir):
    r"""Compare two sets of relative file paths and return classification lists."""
    identical, differ, missing_in_test = [], [], []

    for rel_path in sorted(ref_files):
        test_file = test_dir / rel_path
        if not test_file.exists():
            missing_in_test.append(str(rel_path))
            continue

        ref_content = (reference_dir / rel_path).read_bytes()
        if ref_content == test_file.read_bytes():
            identical.append(str(rel_path))
        else:
            differ.append(str(rel_path))

    extra_in_test = [str(p) for p in sorted(test_files - ref_files)]

    return identical, differ, missing_in_test, extra_in_test


def _print_comparison_report(data_type, reference_dir, test_dir, ref_count, result):
    r"""Print a human-readable comparison report."""
    print(f"\nComparison of {data_type} output:")
    print(f"  Reference directory: {reference_dir}")
    print(f"  Test directory:      {test_dir}")
    print(f"  Total reference files: {ref_count}")
    print(f"  Identical:           {len(result['identical'])}")
    print(f"  Differ:              {len(result['differ'])}")
    print(f"  Missing in test:     {len(result['missing_in_test'])}")
    print(f"  Extra in test:       {len(result['extra_in_test'])}")

    for label, items in [
        ("Files that differ", result["differ"]),
        ("Files missing in test", result["missing_in_test"]),
        ("Extra files in test", result["extra_in_test"]),
    ]:
        if items:
            print(f"\n  {label}:")
            for fname in items:
                print(f"    - {fname}")


def compare_generated_output(
    reference_dir=None,
    test_dir=None,
    data_type="svgdigitizer",
):
    r"""
    Compare generated output files against a reference directory to verify
    that the batch conversion produces identical results.

    This is useful for validating that a new conversion approach (e.g., batch
    processing) produces the same output as the original per-file approach.

    Parameters
    ----------
    reference_dir : str or Path or None
        Directory with reference output files (the "known good" output).
        Defaults to ``data/generated/{data_type}``.
    test_dir : str or Path or None
        Directory with test output files to compare against reference.
        Must be provided explicitly (e.g., a temporary directory).
    data_type : str
        One of ``"svgdigitizer"`` or ``"source_data"``.

    Returns
    -------
    dict
        Summary with keys: ``identical``, ``differ``, ``missing_in_test``,
        ``extra_in_test``, ``total_reference``.
    """
    if reference_dir is None:
        reference_dir = REPO_ROOT / "data" / "generated" / data_type
    reference_dir = Path(reference_dir)

    if test_dir is None:
        raise ValueError("test_dir must be provided for comparison")
    test_dir = Path(test_dir)

    ref_files = _collect_output_files(reference_dir)
    test_files = _collect_output_files(test_dir)

    identical, differ, missing_in_test, extra_in_test = _compare_file_sets(
        ref_files,
        test_files,
        reference_dir,
        test_dir,
    )

    result = {
        "identical": identical,
        "differ": differ,
        "missing_in_test": missing_in_test,
        "extra_in_test": extra_in_test,
        "total_reference": len(ref_files),
    }

    _print_comparison_report(data_type, reference_dir, test_dir, len(ref_files), result)

    return result


def _verify_single_type(dtype, reference_dir):
    r"""Verify a single data type by re-generating into a temporary directory."""
    with tempfile.TemporaryDirectory(prefix=f"echemdb_verify_{dtype}_") as tmpdir:
        test_dir = Path(tmpdir)
        print(f"\nVerifying {dtype} batch conversion...")
        print(f"  Generating to: {test_dir}")

        if dtype == "svgdigitizer":
            digitize_svgdigitizer_data(target_dir=test_dir, force=True)
        elif dtype == "source_data":
            convert_source_data(target_dir=test_dir, force=True)
        else:
            raise ValueError(f"Unknown data type: {dtype}")

        result = compare_generated_output(
            reference_dir=reference_dir,
            test_dir=test_dir,
            data_type=dtype,
        )

        if result["differ"] or result["missing_in_test"]:
            print(f"\n  WARNING: {dtype} output does NOT match reference!")
        else:
            print(f"\n  OK: {dtype} output matches reference perfectly.")

        return result


def verify_batch_conversion(data_type="svgdigitizer"):
    r"""
    Verify that the batch conversion produces output identical to existing
    generated data by re-generating into a temporary directory and comparing.

    This function:
    1. Creates a temporary directory
    2. Runs the batch conversion (force mode) into it
    3. Compares the output file-by-file against the existing generated data
    4. Prints a detailed report and returns the comparison result

    Parameters
    ----------
    data_type : str
        One of ``"svgdigitizer"`` or ``"source_data"`` or ``"all"``.

    Returns
    -------
    dict
        Comparison result from :func:`compare_generated_output`.
        If ``data_type="all"``, returns a dict keyed by data type.
    """
    types_to_check = (
        ["svgdigitizer", "source_data"] if data_type == "all" else [data_type]
    )
    results = {}

    for dtype in types_to_check:
        reference_dir = REPO_ROOT / "data" / "generated" / dtype

        if not reference_dir.exists() or not any(reference_dir.rglob("*.json")):
            print(f"\nSkipping {dtype}: no reference data found in {reference_dir}")
            continue

        results[dtype] = _verify_single_type(dtype, reference_dir)

    return results if len(types_to_check) > 1 else results.get(types_to_check[0], {})
