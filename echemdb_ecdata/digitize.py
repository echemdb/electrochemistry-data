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
from pathlib import Path

logger = logging.getLogger("echemdb_ecdata.digitize")


def _needs_rebuild(yaml_path, svg_path, outdir):
    r"""
    Return whether the output files for a given YAML/SVG pair are
    missing or older than their sources.

    This replicates Make's dependency tracking logic: rebuild if any
    output (.csv or .json) is missing or older than any input (.yaml or .svg).
    """
    stem = Path(yaml_path).stem
    csv_path = Path(outdir) / f"{stem}.csv"
    json_path = Path(outdir) / f"{stem}.json"

    # If either output is missing, rebuild
    if not csv_path.exists() or not json_path.exists():
        return True

    # If any source is newer than any output, rebuild
    source_mtime = max(os.path.getmtime(yaml_path), os.path.getmtime(svg_path))
    target_mtime = min(os.path.getmtime(csv_path), os.path.getmtime(json_path))

    return source_mtime > target_mtime


def digitize_svgdigitizer_data(
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
    # Resolve default paths relative to the repository root
    repo_root = Path(__file__).resolve().parent.parent

    if source_dir is None:
        source_dir = repo_root / "literature" / "svgdigitizer"
    source_dir = Path(source_dir)

    if bibliography_path is None:
        bibliography_path = (
            repo_root / "literature" / "bibliography" / "bibliography.bib"
        )
    bibliography_path = Path(bibliography_path)

    if target_dir is None:
        target_dir = repo_root / "data" / "generated" / "svgdigitizer"
    target_dir = Path(target_dir)

    # Collect YAML files to process
    if yaml_files:
        yaml_paths = [Path(f).resolve() for f in yaml_files]
    else:
        yaml_paths = sorted(source_dir.rglob("*.yaml"))

    if not yaml_paths:
        logger.info("No YAML files found to process.")
        return

    # Pre-load bibliography once (shared across all files)
    bibdata = None
    if bibliography_path.exists():
        from io import StringIO

        from pybtex.database import parse_file

        with open(bibliography_path, "rb") as f:
            content = f.read().decode("utf-8")
        bibdata = parse_file(StringIO(content), bib_format="bibtex")

    # Import heavy dependencies once
    import yaml
    from astropy import units as u

    from svgdigitizer.electrochemistry.cv import CV
    from svgdigitizer.entrypoint import _create_package, _outfile, _write_metadata
    from svgdigitizer.svg import SVG
    from svgdigitizer.svgplot import SVGPlot

    algorithm = "mark-aligned" if skewed else "axis-aligned"

    processed = 0
    skipped = 0
    errors = 0

    for yaml_path in yaml_paths:
        yaml_path = Path(yaml_path).resolve()
        svg_path = yaml_path.with_suffix(".svg")

        if not svg_path.exists():
            skipped += 1
            continue

        # Compute output directory preserving subdirectory structure
        try:
            rel = yaml_path.parent.relative_to(source_dir.resolve())
        except ValueError:
            rel = Path(yaml_path.stem)
        outdir = target_dir / rel

        if not force and not _needs_rebuild(yaml_path, svg_path, outdir):
            skipped += 1
            continue

        if dry_run:
            print(f"Would digitize: {yaml_path.relative_to(source_dir.resolve())}")
            processed += 1
            continue

        try:
            # Read metadata
            with open(yaml_path, "r", encoding="utf-8") as f:
                metadata = yaml.load(f, Loader=yaml.SafeLoader)

            # Compute sampling interval in terms of x-axis unit
            actual_sampling = None
            if sampling_interval is not None:
                with open(svg_path, "rb") as f:
                    cv_temp = CV(
                        SVGPlot(SVG(f), algorithm=algorithm),
                        force_si_units=si_units,
                    )
                    actual_sampling = sampling_interval / u.Unit(
                        cv_temp.figure_schema.get_field(
                            cv_temp.svgplot.xlabel
                        ).custom["unit"]
                    ).to(u.V)

            # Create CV with sampling
            with open(svg_path, "rb") as f:
                svgfigure = CV(
                    SVGPlot(
                        SVG(f),
                        sampling_interval=actual_sampling,
                        algorithm=algorithm,
                    ),
                    metadata=metadata,
                    force_si_units=si_units,
                )

            # Write CSV
            os.makedirs(outdir, exist_ok=True)
            svg_str = str(svg_path)
            csvname = _outfile(svg_str, suffix=".csv", outdir=str(outdir))
            svgfigure.df.to_csv(csvname, index=False)

            # Handle bibliography
            fig_metadata = svgfigure.metadata
            citation_key = fig_metadata.get("source", {}).get("citationKey", "")

            if bibdata and citation_key and citation_key in bibdata.entries:
                fig_metadata.setdefault("source", {})
                fig_metadata["source"]["bibdata"] = bibdata.entries[
                    citation_key
                ].to_string("bibtex")
                fig_metadata["source"]["citationKey"] = citation_key
            elif bibdata and citation_key and citation_key not in bibdata.entries:
                logger.warning(
                    "%s: citation key '%s' not found in bibliography.",
                    yaml_path.name,
                    citation_key,
                )
            elif bibdata and not citation_key:
                logger.warning(
                    "%s: no citationKey in metadata.",
                    yaml_path.name,
                )

            # Build and write JSON package
            package = _create_package(fig_metadata, csvname, str(outdir))

            json_path = _outfile(svg_str, suffix=".json", outdir=str(outdir))
            with open(json_path, mode="w", encoding="utf-8") as json_file:
                _write_metadata(json_file, package.to_dict())

            processed += 1
            print(f"Digitized: {yaml_path.relative_to(source_dir.resolve())}")

        except Exception:
            logger.exception("Error digitizing %s", yaml_path)
            errors += 1

    print(
        f"Done: {processed} digitized, {skipped} up-to-date, {errors} errors "
        f"(out of {len(yaml_paths)} total)"
    )


def _needs_rebuild_source(yaml_path, csv_path, outdir):
    r"""
    Return whether the output files for a given source data YAML/CSV pair
    are missing or older than their sources.
    """
    stem = Path(yaml_path).stem
    out_csv = Path(outdir) / f"{stem}.csv"
    out_json = Path(outdir) / f"{stem}.json"

    if not out_csv.exists() or not out_json.exists():
        return True

    source_mtime = max(os.path.getmtime(yaml_path), os.path.getmtime(csv_path))
    target_mtime = min(os.path.getmtime(out_csv), os.path.getmtime(out_json))

    return source_mtime > target_mtime


def convert_source_data(
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
    # Resolve default paths relative to the repository root
    repo_root = Path(__file__).resolve().parent.parent

    if source_dir is None:
        source_dir = repo_root / "literature" / "source_data"
    source_dir = Path(source_dir)

    if bibliography_path is None:
        bibliography_path = (
            repo_root / "literature" / "bibliography" / "bibliography.bib"
        )
    bibliography_path = Path(bibliography_path)

    if target_dir is None:
        target_dir = repo_root / "data" / "generated" / "source_data"
    target_dir = Path(target_dir)

    # Collect YAML files to process
    if yaml_files:
        yaml_paths = [Path(f).resolve() for f in yaml_files]
    else:
        yaml_paths = sorted(source_dir.rglob("*.yaml"))

    if not yaml_paths:
        logger.info("No YAML files found to process.")
        return

    # Pre-load bibliography once
    bibdata = None
    if bibliography_path.exists():
        from io import StringIO

        from pybtex.database import parse_file

        with open(bibliography_path, "rb") as f:
            content = f.read().decode("utf-8")
        bibdata = parse_file(StringIO(content), bib_format="bibtex")

    # Import heavy dependencies once
    import astropy.units as u
    import yaml
    from unitpackage.entry import Entry

    from echemdb_ecdata.entrypoint import DataDescription, _add_bibdata_to_source, _add_time_axis

    processed = 0
    skipped = 0
    errors = 0

    for yaml_path in yaml_paths:
        yaml_path = Path(yaml_path).resolve()
        csv_path = yaml_path.with_suffix(".csv")

        if not csv_path.exists():
            skipped += 1
            continue

        # Compute output directory preserving subdirectory structure
        try:
            rel = yaml_path.parent.relative_to(source_dir.resolve())
        except ValueError:
            rel = Path(yaml_path.stem)
        outdir = target_dir / rel

        if not force and not _needs_rebuild_source(yaml_path, csv_path, outdir):
            skipped += 1
            continue

        if dry_run:
            print(f"Would convert: {yaml_path.relative_to(source_dir.resolve())}")
            processed += 1
            continue

        try:
            # Load metadata
            with open(yaml_path, "r", encoding="utf-8") as f:
                metadata_dict = yaml.safe_load(f)

            data_description = DataDescription.model_validate(
                metadata_dict["dataDescription"]
            )

            # Clean metadata (remove dataDescription as the CLI does)
            metadata = metadata_dict.copy()
            del metadata["dataDescription"]

            # Add bibliography data
            citation_key = metadata.get("source", {}).get("citationKey", "")
            if bibdata and citation_key and citation_key in bibdata.entries:
                bibliography_data = bibdata.entries[citation_key].to_string("bibtex")
                metadata = _add_bibdata_to_source(
                    metadata, bibliography_data, citation_key
                )
            elif bibdata and citation_key and citation_key not in bibdata.entries:
                logger.warning(
                    "%s: citation key '%s' not found in bibliography.",
                    yaml_path.name,
                    citation_key,
                )
            elif bibdata and not citation_key:
                logger.warning(
                    "%s: no citationKey in metadata.",
                    yaml_path.name,
                )

            # Construct entry
            dialect = data_description.dialect
            raw_entry = Entry.from_csv(
                str(csv_path),
                **dialect.model_dump(exclude_none=True, by_alias=False),
            )
            raw_entry.metadata.from_dict({"echemdb": metadata})

            # Remove unnecessary fields
            reduced_entry = raw_entry.remove_columns(
                *[
                    field
                    for field in raw_entry.df.columns
                    if field not in data_description.field_mapping.keys()
                ]
            )
            mapped_entry = reduced_entry.rename_fields(data_description.field_mapping)
            entry = mapped_entry.update_fields(data_description.field_units)

            # Create a time axis if not present
            if "t" not in entry.df.columns:
                scan_rate = metadata["figureDescription"]["scanRate"]["value"] * u.Unit(
                    metadata["figureDescription"]["scanRate"]["unit"]
                )
                entry = _add_time_axis(entry, scan_rate)

            # Update fields in metadata
            entry.metadata.echemdb["figureDescription"].__dict__.setdefault(
                "fields", {}
            )
            entry.metadata.echemdb["figureDescription"].__dict__["fields"] = (
                entry.fields
            )

            # Write output
            os.makedirs(outdir, exist_ok=True)
            entry.save(outdir=str(outdir))

            processed += 1
            print(f"Converted: {yaml_path.relative_to(source_dir.resolve())}")

        except Exception:
            logger.exception("Error converting %s", yaml_path)
            errors += 1

    print(
        f"Done: {processed} converted, {skipped} up-to-date, {errors} errors "
        f"(out of {len(yaml_paths)} total)"
    )


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
    repo_root = Path(__file__).resolve().parent.parent

    if reference_dir is None:
        reference_dir = repo_root / "data" / "generated" / data_type
    reference_dir = Path(reference_dir)

    if test_dir is None:
        raise ValueError("test_dir must be provided for comparison")
    test_dir = Path(test_dir)

    # Collect all .csv and .json files from reference
    ref_files = set()
    for ext in ("*.csv", "*.json"):
        for f in reference_dir.rglob(ext):
            ref_files.add(f.relative_to(reference_dir))

    test_files = set()
    for ext in ("*.csv", "*.json"):
        for f in test_dir.rglob(ext):
            test_files.add(f.relative_to(test_dir))

    identical = []
    differ = []
    missing_in_test = []
    extra_in_test = []

    for rel_path in sorted(ref_files):
        ref_file = reference_dir / rel_path
        test_file = test_dir / rel_path

        if not test_file.exists():
            missing_in_test.append(str(rel_path))
            continue

        # Compare file contents
        ref_content = ref_file.read_bytes()
        test_content = test_file.read_bytes()

        if ref_content == test_content:
            identical.append(str(rel_path))
        else:
            differ.append(str(rel_path))

    for rel_path in sorted(test_files - ref_files):
        extra_in_test.append(str(rel_path))

    # Print summary
    print(f"\nComparison of {data_type} output:")
    print(f"  Reference directory: {reference_dir}")
    print(f"  Test directory:      {test_dir}")
    print(f"  Total reference files: {len(ref_files)}")
    print(f"  Identical:           {len(identical)}")
    print(f"  Differ:              {len(differ)}")
    print(f"  Missing in test:     {len(missing_in_test)}")
    print(f"  Extra in test:       {len(extra_in_test)}")

    if differ:
        print("\n  Files that differ:")
        for f in differ:
            print(f"    - {f}")

    if missing_in_test:
        print("\n  Files missing in test:")
        for f in missing_in_test:
            print(f"    - {f}")

    if extra_in_test:
        print("\n  Extra files in test:")
        for f in extra_in_test:
            print(f"    - {f}")

    return {
        "identical": identical,
        "differ": differ,
        "missing_in_test": missing_in_test,
        "extra_in_test": extra_in_test,
        "total_reference": len(ref_files),
    }


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
    import tempfile

    repo_root = Path(__file__).resolve().parent.parent

    types_to_check = (
        ["svgdigitizer", "source_data"] if data_type == "all" else [data_type]
    )
    results = {}

    for dtype in types_to_check:
        reference_dir = repo_root / "data" / "generated" / dtype

        if not reference_dir.exists() or not any(reference_dir.rglob("*.json")):
            print(f"\nSkipping {dtype}: no reference data found in {reference_dir}")
            continue

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
            results[dtype] = result

            if result["differ"] or result["missing_in_test"]:
                print(f"\n  WARNING: {dtype} output does NOT match reference!")
            else:
                print(f"\n  OK: {dtype} output matches reference perfectly.")

    return results if len(types_to_check) > 1 else results.get(types_to_check[0], {})
