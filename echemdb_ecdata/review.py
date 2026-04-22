r"""
Automated review utilities for literature addition PRs.

This module provides functions for downloading PDFs via DOI,
extracting text, and cross-validating YAML/SVG metadata against
the actual publication content.

EXAMPLES:

Review all new literature entries in the current PR::

    >>> from echemdb_ecdata.review import review_pr  # doctest: +SKIP
    >>> review_pr()  # doctest: +SKIP

Review a single literature entry by its directory path::

    >>> from echemdb_ecdata.review import review_entry  # doctest: +SKIP
    >>> review_entry("literature/svgdigitizer/hirai_2000_in_702")  # doctest: +SKIP

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

import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path

import yaml

logger = logging.getLogger("echemdb_ecdata.review")


def download_pdf_from_doi(doi, output_dir=None):
    r"""
    Download a PDF from a DOI by resolving it and attempting common
    publisher PDF URL patterns.

    Parameters
    ----------
    doi : str
        The DOI string (e.g., ``10.2355/isijinternational.40.702``).
    output_dir : str or Path or None
        Directory to save the PDF. If None, uses a temporary directory.

    Returns
    -------
    str or None
        Path to the downloaded PDF file, or None if download failed.
    """
    import requests

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="echemdb_review_")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = output_dir / "paper.pdf"

    # Resolve the DOI to get the landing page URL
    try:
        resp = requests.get(
            f"https://doi.org/{doi}",
            allow_redirects=True,
            timeout=15,
            headers={"User-Agent": "echemdb-review/1.0"},
        )
        landing_url = resp.url
    except Exception as e:
        logger.warning("Failed to resolve DOI %s: %s", doi, e)
        return None

    # Try known publisher PDF URL patterns
    pdf_urls = _build_pdf_urls(doi, landing_url)

    for url in pdf_urls:
        try:
            resp = requests.get(
                url,
                timeout=30,
                headers={"User-Agent": "echemdb-review/1.0"},
                allow_redirects=True,
            )
            content_type = resp.headers.get("Content-Type", "")
            if resp.ok and "pdf" in content_type.lower():
                pdf_path.write_bytes(resp.content)
                logger.info("Downloaded PDF from %s", url)
                return str(pdf_path)
        except Exception as e:
            logger.debug("Failed to download from %s: %s", url, e)
            continue

    logger.warning("Could not download PDF for DOI %s", doi)
    return None


def _build_pdf_urls(doi, landing_url):
    """Build candidate PDF URLs from DOI and landing page URL."""
    urls = []

    # J-STAGE (Japanese journals)
    if "jstage.jst.go.jp" in landing_url:
        pdf_url = landing_url.replace("/_article", "/_pdf")
        urls.append(pdf_url)

    # Elsevier / ScienceDirect
    if "sciencedirect.com" in landing_url:
        # Extract PII from URL
        pii_match = re.search(r"/pii/([A-Z0-9]+)", landing_url)
        if pii_match:
            pii = pii_match.group(1)
            urls.append(f"https://www.sciencedirect.com/science/article/pii/{pii}/pdfft")

    # Wiley
    if "onlinelibrary.wiley.com" in landing_url:
        urls.append(landing_url.replace("/abs/", "/pdfdirect/").replace("/full/", "/pdfdirect/"))

    # ACS
    if "pubs.acs.org" in landing_url:
        urls.append(landing_url.replace("/doi/abs/", "/doi/pdf/").replace("/doi/full/", "/doi/pdf/"))

    # ECS / IOP
    if "iopscience.iop.org" in landing_url:
        urls.append(landing_url + "/pdf")

    # Springer
    if "link.springer.com" in landing_url:
        urls.append(landing_url.replace("/article/", "/content/pdf/") + ".pdf")

    # Generic: try appending /pdf or .pdf
    if not urls:
        urls.append(landing_url + ".pdf")
        urls.append(landing_url + "/pdf")

    return urls


def extract_pdf_text(pdf_path):
    r"""
    Extract all text from a PDF file.

    Parameters
    ----------
    pdf_path : str or Path
        Path to the PDF file.

    Returns
    -------
    dict
        Dictionary mapping page number (0-indexed) to extracted text.
    """
    import pymupdf

    doc = pymupdf.open(str(pdf_path))
    pages = {}
    for i in range(doc.page_count):
        pages[i] = doc.get_page_text(i)
    doc.close()
    return pages


def _load_yaml(yaml_path):
    """Load a YAML file and return its contents."""
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_bib_entry(citation_key):
    """Load the bibliography entry for a given citation key."""
    bib_path = Path("literature/bibliography/bibliography.bib")
    if not bib_path.exists():
        return None
    from pybtex.database import parse_file

    bib_data = parse_file(str(bib_path), bib_format="bibtex")
    return bib_data.entries.get(citation_key)


def _extract_svg_metadata(svg_path):
    """Extract key metadata from an SVG file (labels, axis info, etc.)."""
    metadata = {}
    with open(svg_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract labeled text nodes
    for label in ["scan rate", "figure", "tags", "curve", "comment"]:
        pattern = rf'{label}:\s*([^<\n]+)'
        match = re.search(pattern, content)
        if match:
            metadata[label] = match.group(1).strip()

    # Extract axis labels
    for axis in ["E1", "E2", "j1", "j2"]:
        pattern = rf'{axis}:\s*([^<\n]+)'
        match = re.search(pattern, content)
        if match:
            metadata[axis] = match.group(1).strip()

    return metadata


def review_entry(entry_dir, pdf_text=None):
    r"""
    Review a single literature entry against the PR checklist.

    Parameters
    ----------
    entry_dir : str or Path
        Path to the entry directory (e.g., ``literature/svgdigitizer/hirai_2000_in_702``).
    pdf_text : dict or None
        Pre-extracted PDF text (page_num -> text). If None, will attempt to download.

    Returns
    -------
    dict
        Review report with findings organized by category.
    """
    entry_dir = Path(entry_dir)
    report = {
        "entry": str(entry_dir),
        "filename": [],
        "bib": [],
        "svg": [],
        "yaml": [],
        "pdf_cross_check": [],
        "errors": 0,
        "warnings": 0,
    }

    dir_name = entry_dir.name

    # Discover files
    yaml_files = sorted(entry_dir.glob("*.yaml"))
    svg_files = sorted(entry_dir.glob("*.svg"))

    if not yaml_files:
        _add_error(report, "filename", f"No YAML files found in {entry_dir}")
        return report

    # ── 1. Filename checks ──────────────────────────────────────────
    _check_filenames(report, entry_dir, dir_name, yaml_files, svg_files)

    # ── 2. Bib checks ───────────────────────────────────────────────
    yaml_data = _load_yaml(yaml_files[0])
    citation_key = yaml_data.get("source", {}).get("citationKey", "")
    _check_bib(report, dir_name, citation_key)

    # ── 3. SVG checks ───────────────────────────────────────────────
    for svg_file in svg_files:
        svg_meta = _extract_svg_metadata(svg_file)
        _check_svg(report, svg_file, svg_meta, yaml_data)

    # ── 4. YAML checks ──────────────────────────────────────────────
    for yaml_file in yaml_files:
        yd = _load_yaml(yaml_file)
        _check_yaml(report, yaml_file, yd, dir_name)

    # ── 5. PDF cross-validation ─────────────────────────────────────
    if pdf_text is None:
        # Check for a local PDF in the entry directory first
        local_pdfs = sorted(entry_dir.glob("*.pdf"))
        if local_pdfs:
            pdf_path = str(local_pdfs[0])
            logger.info("Using local PDF: %s", pdf_path)
            pdf_text = extract_pdf_text(pdf_path)
        else:
            doi_url = yaml_data.get("source", {}).get("url", "")
            doi_match = re.search(r"10\.\d{4,9}/[^\s]+", doi_url)
            if doi_match:
                doi = doi_match.group(0)
                pdf_path = download_pdf_from_doi(doi)
                if pdf_path:
                    pdf_text = extract_pdf_text(pdf_path)
                else:
                    _add_warning(report, "pdf_cross_check", "Could not download PDF for cross-validation.")

    if pdf_text:
        _cross_validate_with_pdf(report, yaml_data, pdf_text, svg_files)

    return report


def _add_error(report, category, message):
    """Add an error to the report."""
    report[category].append(("ERROR", message))
    report["errors"] += 1


def _add_warning(report, category, message):
    """Add a warning to the report."""
    report[category].append(("WARNING", message))
    report["warnings"] += 1


def _add_ok(report, category, message):
    """Add a passing check to the report."""
    report[category].append(("OK", message))


def _check_filenames(report, entry_dir, dir_name, yaml_files, svg_files):
    """Validate filename conventions."""
    # All lowercase
    if dir_name != dir_name.lower():
        _add_error(report, "filename", f"Directory name '{dir_name}' is not lowercase.")
    else:
        _add_ok(report, "filename", "Directory name is lowercase.")

    for f in list(yaml_files) + list(svg_files):
        if f.name != f.name.lower():
            _add_error(report, "filename", f"Filename '{f.name}' is not lowercase.")

    # Check naming pattern: {citationKey}_f{figure}_{curve}.{ext}
    pattern = re.compile(r"^[a-z0-9_-]+_f\w+_\w+\.\w+$")
    for f in list(yaml_files) + list(svg_files):
        if not pattern.match(f.name):
            _add_warning(report, "filename", f"Filename '{f.name}' may not match expected pattern '{{citationKey}}_f{{figure}}_{{curve}}.{{ext}}'.")
        else:
            _add_ok(report, "filename", f"Filename '{f.name}' matches naming pattern.")

    # Each SVG must have a matching YAML
    svg_stems = {f.stem for f in svg_files}
    yaml_stems = {f.stem for f in yaml_files}
    for stem in svg_stems:
        if stem not in yaml_stems:
            _add_error(report, "filename", f"SVG '{stem}.svg' has no matching YAML file.")
        else:
            _add_ok(report, "filename", f"SVG '{stem}.svg' has matching YAML.")

    # All files must start with dir_name
    for f in list(yaml_files) + list(svg_files):
        if not f.stem.startswith(dir_name):
            _add_error(report, "filename", f"Filename '{f.name}' does not start with directory name '{dir_name}'.")
        else:
            _add_ok(report, "filename", f"Filename '{f.name}' starts with directory name.")


def _check_bib(report, dir_name, citation_key):
    """Validate bibliography entry."""
    # Citation key matches directory name
    if citation_key != dir_name:
        _add_error(report, "bib", f"citationKey '{citation_key}' does not match directory name '{dir_name}'.")
    else:
        _add_ok(report, "bib", f"citationKey '{citation_key}' matches directory name.")

    # Check bib entry exists
    bib_entry = _load_bib_entry(citation_key)
    if bib_entry is None:
        _add_error(report, "bib", f"No bibliography entry found for key '{citation_key}'.")
        return
    else:
        _add_ok(report, "bib", f"Bibliography entry found for '{citation_key}'.")

    # Validate the computed identifier matches
    from pybtex.database import BibliographyData
    from svgdigitizer.pdf import Pdf

    bib_data = BibliographyData(entries={citation_key: bib_entry})
    expected_key = Pdf.build_identifier(bib_data)
    if expected_key != citation_key:
        _add_error(report, "bib", f"Computed identifier '{expected_key}' does not match citationKey '{citation_key}'.")
    else:
        _add_ok(report, "bib", f"Computed identifier matches citationKey.")

    # Check for common title issues
    title = bib_entry.fields.get("title", "")
    # Check for spaces before parentheses like "Pt (111)" -> should be "Pt(111)"
    space_paren = re.findall(r"\w\s+\(\d+\)", title)
    if space_paren:
        _add_warning(report, "bib", f"Possible unwanted space before parentheses in title: {space_paren}")

    # Check for trailing whitespace
    if title != title.strip():
        _add_warning(report, "bib", "Title has leading/trailing whitespace.")


def _check_svg(report, svg_file, svg_meta, yaml_data):
    """Validate SVG content."""
    fname = svg_file.name

    # Must have tags
    if "tags" not in svg_meta:
        _add_error(report, "svg", f"[{fname}] Missing 'tags' text label.")
    else:
        _add_ok(report, "svg", f"[{fname}] Has 'tags' label: {svg_meta['tags']}")

    # Must have figure label
    if "figure" not in svg_meta:
        _add_error(report, "svg", f"[{fname}] Missing 'figure' text label.")
    else:
        fig = svg_meta["figure"]
        # Figure label should be "xy" not "fxy"
        if fig.startswith("f"):
            _add_warning(report, "svg", f"[{fname}] Figure label '{fig}' starts with 'f'. Should be just the number/letter (e.g., '2' not 'f2').")
        else:
            _add_ok(report, "svg", f"[{fname}] Figure label '{fig}' format is correct.")

        # Verify figure number matches filename
        fig_from_name = _extract_figure_from_filename(svg_file.stem)
        if fig_from_name and fig_from_name != fig:
            _add_warning(report, "svg", f"[{fname}] Figure label '{fig}' does not match filename figure '{fig_from_name}'.")

    # Must have curve label
    if "curve" not in svg_meta:
        _add_warning(report, "svg", f"[{fname}] Missing 'curve' text label.")
    else:
        _add_ok(report, "svg", f"[{fname}] Has 'curve' label: {svg_meta['curve']}")

    # Must have scan rate
    if "scan rate" not in svg_meta:
        _add_warning(report, "svg", f"[{fname}] Missing 'scan rate' text label.")
    else:
        _add_ok(report, "svg", f"[{fname}] Has 'scan rate': {svg_meta['scan rate']}")

    # Check axis labels exist
    for axis in ["E1", "E2", "j1", "j2"]:
        if axis not in svg_meta:
            _add_warning(report, "svg", f"[{fname}] Missing axis label '{axis}'.")
        else:
            _add_ok(report, "svg", f"[{fname}] Axis '{axis}': {svg_meta[axis]}")

    # Check reference electrode consistency between SVG and YAML
    ref_electrode = None
    electrodes = yaml_data.get("system", {}).get("electrodes", [])
    for e in electrodes:
        if e.get("function") == "reference electrode":
            ref_electrode = e.get("material", "")
            break
    if ref_electrode and "E1" in svg_meta:
        if ref_electrode.lower() not in svg_meta["E1"].lower():
            _add_warning(report, "svg", f"[{fname}] Reference electrode in YAML ('{ref_electrode}') may not match SVG axis '{svg_meta['E1']}'.")


def _extract_figure_from_filename(stem):
    """Extract figure identifier from filename stem (e.g., 'hirai_2000_in_702_f2_solid' -> '2')."""
    match = re.search(r"_f(\w+)_", stem)
    if match:
        return match.group(1)
    return None


def _check_yaml(report, yaml_file, yaml_data, dir_name):
    """Validate YAML metadata."""
    fname = yaml_file.name

    # citationKey matches
    ck = yaml_data.get("source", {}).get("citationKey", "")
    if ck != dir_name:
        _add_error(report, "yaml", f"[{fname}] citationKey '{ck}' does not match directory name '{dir_name}'.")
    else:
        _add_ok(report, "yaml", f"[{fname}] citationKey matches directory name.")

    # Check required sections
    for section in ["curation", "source", "system"]:
        if section not in yaml_data:
            _add_error(report, "yaml", f"[{fname}] Missing required section '{section}'.")
        else:
            _add_ok(report, "yaml", f"[{fname}] Has '{section}' section.")

    # Check source URL (must be a DOI URL)
    url = yaml_data.get("source", {}).get("url", "")
    if not url:
        _add_error(report, "yaml", f"[{fname}] Missing source URL.")
    elif "doi.org" not in url and "doi" not in url.lower():
        _add_warning(report, "yaml", f"[{fname}] Source URL '{url}' may not be a DOI URL.")
    else:
        _add_ok(report, "yaml", f"[{fname}] Source URL is a DOI: {url}")

    # Check electrolyte info
    electrolyte = yaml_data.get("system", {}).get("electrolyte", {})
    if not electrolyte:
        _add_warning(report, "yaml", f"[{fname}] Missing electrolyte information.")
    else:
        if "type" not in electrolyte:
            _add_warning(report, "yaml", f"[{fname}] Electrolyte missing 'type' field.")
        if "components" not in electrolyte:
            _add_warning(report, "yaml", f"[{fname}] Electrolyte missing 'components'.")

    # Check electrodes
    electrodes = yaml_data.get("system", {}).get("electrodes", [])
    electrode_functions = [e.get("function", "") for e in electrodes]
    if "working electrode" not in electrode_functions:
        _add_warning(report, "yaml", f"[{fname}] No working electrode defined.")
    if "reference electrode" not in electrode_functions:
        _add_warning(report, "yaml", f"[{fname}] No reference electrode defined.")

    # Check curation info
    curation = yaml_data.get("curation", {})
    processes = curation.get("process", [])
    if not processes:
        _add_warning(report, "yaml", f"[{fname}] Missing curation process entries.")
    else:
        for proc in processes:
            if not proc.get("orcid"):
                _add_warning(report, "yaml", f"[{fname}] Curator '{proc.get('name', 'unknown')}' missing ORCID.")


def _cross_validate_with_pdf(report, yaml_data, pdf_text, svg_files):
    """Cross-validate YAML metadata against PDF text content."""
    # Combine all pages
    all_text = "\n".join(pdf_text.values())
    all_text_lower = all_text.lower()

    # Check electrolyte components mentioned in paper
    electrolyte = yaml_data.get("system", {}).get("electrolyte", {})
    components = electrolyte.get("components", [])
    for comp in components:
        name = comp.get("name", "")
        if name.lower() == "water":
            continue
        if name.lower() in all_text_lower:
            _add_ok(report, "pdf_cross_check", f"Electrolyte component '{name}' found in PDF text.")
        else:
            _add_warning(report, "pdf_cross_check", f"Electrolyte component '{name}' NOT found in PDF text. Verify manually.")

    # Check concentration values
    for comp in components:
        conc = comp.get("concentration", {})
        if conc:
            val = str(conc.get("value", ""))
            if val and val in all_text:
                _add_ok(report, "pdf_cross_check", f"Concentration value '{val}' for '{comp.get('name', '')}' found in PDF.")
            elif val:
                _add_warning(report, "pdf_cross_check", f"Concentration value '{val}' for '{comp.get('name', '')}' not directly found in PDF. Verify manually.")

    # Check electrode material
    electrodes = yaml_data.get("system", {}).get("electrodes", [])
    for e in electrodes:
        material = e.get("material", "")
        if material and material.lower() in all_text_lower:
            _add_ok(report, "pdf_cross_check", f"Electrode material '{material}' found in PDF.")
        elif material:
            _add_warning(report, "pdf_cross_check", f"Electrode material '{material}' not found in PDF. Verify manually.")

    # Check crystallographic orientation
    for e in electrodes:
        orient = e.get("crystallographicOrientation", "")
        if orient and orient in all_text:
            _add_ok(report, "pdf_cross_check", f"Crystallographic orientation '{orient}' found in PDF.")
        elif orient:
            # Try with parentheses format like (110)
            if f"({orient})" in all_text:
                _add_ok(report, "pdf_cross_check", f"Crystallographic orientation '({orient})' found in PDF.")
            else:
                _add_warning(report, "pdf_cross_check", f"Crystallographic orientation '{orient}' not found in PDF. Verify manually.")

    # Check pH value
    ph = electrolyte.get("ph", {})
    if ph:
        ph_val = str(ph.get("value", ""))
        if ph_val and ph_val in all_text:
            _add_ok(report, "pdf_cross_check", f"pH value '{ph_val}' found in PDF.")
        elif ph_val:
            _add_warning(report, "pdf_cross_check", f"pH value '{ph_val}' not found directly in PDF. Verify manually.")

    # Check scan rate from SVG against PDF
    for svg_file in svg_files:
        svg_meta = _extract_svg_metadata(svg_file)
        scan_rate = svg_meta.get("scan rate", "")
        if scan_rate:
            # Extract numeric part
            rate_match = re.search(r"(\d+(?:\.\d+)?)", scan_rate)
            if rate_match:
                rate_val = rate_match.group(1)
                if rate_val in all_text:
                    _add_ok(report, "pdf_cross_check", f"Scan rate value '{rate_val}' found in PDF.")
                else:
                    _add_warning(report, "pdf_cross_check", f"Scan rate value '{rate_val}' not found in PDF. Verify manually.")

    # Check reference electrode
    for e in electrodes:
        if e.get("function") == "reference electrode":
            ref_mat = e.get("material", "")
            if ref_mat:
                # Check various representations
                ref_variants = [ref_mat, ref_mat.replace("/", " "), ref_mat.replace("2", "₂")]
                found = any(v.lower() in all_text_lower for v in ref_variants)
                if found:
                    _add_ok(report, "pdf_cross_check", f"Reference electrode '{ref_mat}' found in PDF.")
                else:
                    _add_warning(report, "pdf_cross_check", f"Reference electrode '{ref_mat}' not found in PDF. Verify manually.")

    # Check purity info
    for e in electrodes:
        purity = e.get("purity", {})
        grade = str(purity.get("grade", ""))
        if grade and grade in all_text:
            _add_ok(report, "pdf_cross_check", f"Purity grade '{grade}' found in PDF.")
        elif grade:
            _add_warning(report, "pdf_cross_check", f"Purity grade '{grade}' not found in PDF. Verify manually.")

    # Check supplier names
    for comp in components:
        supplier = comp.get("source", {}).get("supplier", "")
        if supplier and supplier.lower() in all_text_lower:
            _add_ok(report, "pdf_cross_check", f"Supplier '{supplier}' found in PDF.")
        elif supplier:
            _add_warning(report, "pdf_cross_check", f"Supplier '{supplier}' not found in PDF. Verify manually.")


def format_report(report):
    r"""
    Format a review report as a readable string.

    Parameters
    ----------
    report : dict
        Report dictionary from :func:`review_entry`.

    Returns
    -------
    str
        Human-readable report.
    """
    lines = []
    lines.append(f"{'=' * 72}")
    lines.append(f"Review Report: {report['entry']}")
    lines.append(f"{'=' * 72}")
    lines.append(f"Errors: {report['errors']}  |  Warnings: {report['warnings']}")
    lines.append("")

    for category in ["filename", "bib", "svg", "yaml", "pdf_cross_check"]:
        items = report[category]
        if not items:
            continue
        header = category.upper().replace("_", " ")
        lines.append(f"── {header} {'─' * (66 - len(header))}")
        for level, msg in items:
            marker = {"OK": "✓", "WARNING": "⚠", "ERROR": "✗"}.get(level, "?")
            lines.append(f"  {marker} {msg}")
        lines.append("")

    if report["errors"] == 0 and report["warnings"] == 0:
        lines.append("All checks passed!")
    elif report["errors"] == 0:
        lines.append(f"No errors. {report['warnings']} warning(s) to review.")
    else:
        lines.append(f"{report['errors']} error(s) must be fixed. {report['warnings']} warning(s) to review.")

    return "\n".join(lines)


def generate_review_report(report, entry_dir, yaml_data=None, pdf_text=None):
    r"""
    Generate a Markdown review report with actionable decision boxes.

    Each issue (ERROR or WARNING) gets a numbered section with:
    - Finding description
    - Proposed fix (with concrete code/command)
    - Decision checkboxes: ``accept``, ``reject``, ``comment``
    - Space for reviewer notes

    Passing checks are listed as a summary checklist at the end.

    Parameters
    ----------
    report : dict
        Report dictionary from :func:`review_entry`.
    entry_dir : str or Path
        Path to the entry directory.
    yaml_data : dict or None
        Parsed YAML data. If None, loaded from the first YAML file.
    pdf_text : dict or None
        Extracted PDF text for context snippets.

    Returns
    -------
    str
        Markdown report content.
    """
    entry_dir = Path(entry_dir)
    dir_name = entry_dir.name

    if yaml_data is None:
        yaml_files = sorted(entry_dir.glob("*.yaml"))
        if yaml_files:
            yaml_data = _load_yaml(yaml_files[0])
        else:
            yaml_data = {}

    doi_url = yaml_data.get("source", {}).get("url", "")
    lines = []

    # Header
    lines.append(f"# Review Report: `{dir_name}`")
    lines.append("")
    lines.append(f"> **Entry:** `{entry_dir}`")
    lines.append(f"> **DOI:** {doi_url}")
    lines.append(f"> **Generated:** {_today()}")
    lines.append("")
    lines.append("Instructions: For each finding below, mark your decision:")
    lines.append("- `[x] accept` — apply the proposed fix")
    lines.append("- `[x] reject` — do not fix, leave as-is")
    lines.append("- `[x] comment` — needs discussion (add your note)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Collect issues (errors + warnings) for numbered sections
    issue_num = 0
    for category in ["filename", "bib", "svg", "yaml", "pdf_cross_check"]:
        for level, msg in report[category]:
            if level in ("ERROR", "WARNING"):
                issue_num += 1
                label = "ERROR" if level == "ERROR" else "SUGGESTION"
                lines.append(f"## {issue_num}. {msg} ({label})")
                lines.append("")
                lines.append(f"**Category:** {category}")
                lines.append("")
                # Generate proposed fix hint
                fix = _suggest_fix(level, msg, dir_name, yaml_data)
                if fix:
                    lines.append("**Proposed fix:**")
                    lines.append(fix)
                    lines.append("")
                lines.append("**Decision:**")
                lines.append("- [ ] accept")
                lines.append("- [ ] reject")
                lines.append("- [ ] comment")
                lines.append("")
                lines.append("**Reviewer notes:**")
                lines.append("> ")
                lines.append("")
                lines.append("---")
                lines.append("")

    if issue_num == 0:
        lines.append("**No issues found!** All checks passed.")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Summary checklist of passing checks
    lines.append("## Automated Checks Summary")
    lines.append("")
    for category in ["filename", "bib", "svg", "yaml", "pdf_cross_check"]:
        items = report[category]
        if not items:
            continue
        header = category.upper().replace("_", " ")
        lines.append(f"### {header}")
        for level, msg in items:
            if level == "OK":
                lines.append(f"- [x] {msg}")
            elif level == "ERROR":
                lines.append(f"- [ ] {msg} **(see issue above)**")
            elif level == "WARNING":
                lines.append(f"- [ ] {msg} **(see issue above)**")
        lines.append("")

    # Curator Notes placeholder
    lines.append("## Curator Notes")
    lines.append("")
    lines.append("> (Optional) Add any general notes, context, or observations here.")
    lines.append("")

    return "\n".join(lines)


def _today():
    """Return today's date as YYYY-MM-DD."""
    from datetime import date
    return date.today().isoformat()


def _suggest_fix(level, msg, dir_name, yaml_data):
    """Generate a proposed fix block for a given issue message."""
    # Identifier mismatch
    match = re.search(r"Computed identifier '(\S+)' does not match citationKey '(\S+)'", msg)
    if match:
        expected, current = match.group(1), match.group(2)
        return (
            f"```bash\n"
            f"pixi run -e dev rename-identifiers {current} {expected}\n"
            f"```\n"
            f"This renames the directory, all files, the bib key, and the YAML citationKey."
        )

    # Missing field suggestions — detect common patterns
    if "not found in bibliography" in msg.lower():
        return "Add a matching entry to `literature/bibliography/bibliography.bib`."

    if "missing" in msg.lower() and "tags" in msg.lower():
        return "Add a `tags: BCV` (or appropriate) text label in the SVG file."

    if "not lowercase" in msg.lower():
        return "```bash\npixi run -e dev fix-lowercase\n```"

    return None


def parse_review_report(report_path):
    r"""
    Parse a Markdown review report and return the decisions.

    Reads the REVIEW.md file and extracts each numbered issue
    with its accept/reject/comment decision and reviewer notes.

    Parameters
    ----------
    report_path : str or Path
        Path to the ``REVIEW.md`` file.

    Returns
    -------
    list of dict
        List of issues with keys:
        ``number``, ``title``, ``category``, ``decision``, ``notes``,
        ``fix_command`` (if present).
    """
    report_path = Path(report_path)
    content = report_path.read_text(encoding="utf-8")

    issues = []
    # Split into sections by "## N."
    sections = re.split(r"^## (\d+)\. ", content, flags=re.MULTILINE)

    # sections[0] is the header, then alternating: number, body
    for i in range(1, len(sections) - 1, 2):
        number = int(sections[i])
        body = sections[i + 1]

        # Extract title (first line)
        title_line = body.split("\n")[0].strip()

        # Extract category
        cat_match = re.search(r"\*\*Category:\*\*\s*(\S+)", body)
        category = cat_match.group(1) if cat_match else ""

        # Extract decision
        decision = "none"
        if re.search(r"- \[x\] accept", body, re.IGNORECASE):
            decision = "accept"
        elif re.search(r"- \[x\] reject", body, re.IGNORECASE):
            decision = "reject"
        elif re.search(r"- \[x\] comment", body, re.IGNORECASE):
            decision = "comment"

        # Extract reviewer notes
        notes_match = re.search(r"\*\*Reviewer notes:\*\*\n>\s*(.*?)(?:\n---|\n##|\Z)", body, re.DOTALL)
        notes = notes_match.group(1).strip() if notes_match else ""

        # Extract fix command if present
        cmd_match = re.search(r"```(?:bash|yaml)?\n(.+?)```", body, re.DOTALL)
        fix_command = cmd_match.group(1).strip() if cmd_match else ""

        issues.append({
            "number": number,
            "title": title_line,
            "category": category,
            "decision": decision,
            "notes": notes,
            "fix_command": fix_command,
        })

    return issues


def write_review_report(entry_dir, base_branch="main", output_path=None):
    r"""
    Run the review for an entry and write the REVIEW.md report file.

    Parameters
    ----------
    entry_dir : str or Path
        Path to the entry directory.
    base_branch : str
        Branch to compare against (default: ``main``).
    output_path : str or Path, optional
        Path to write the report to. Defaults to ``REVIEW.md`` in the
        repository root (current working directory).

    Returns
    -------
    Path
        Path to the written REVIEW.md file.
    """
    entry_dir = Path(entry_dir)
    report = review_entry(entry_dir)
    md = generate_review_report(report, entry_dir)
    report_path = Path(output_path) if output_path else Path("REVIEW.md")
    report_path.write_text(md, encoding="utf-8")
    logger.info("Review report written to %s", report_path)
    return report_path


def review_pr(base_branch="main"):
    r"""
    Review all new/modified literature entries in the current PR.

    Detects changed files by comparing with the given base branch
    and reviews each affected entry directory.

    Parameters
    ----------
    base_branch : str
        Branch to compare against (default: ``main``).

    Returns
    -------
    list of dict
        List of review reports, one per entry directory.
    """
    # Get changed files
    try:
        result = subprocess.run(
            ["git", "diff", base_branch, "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        logger.error("Failed to run git diff. Are you in a git repository?")
        return []

    changed_files = result.stdout.strip().split("\n")

    # Find unique entry directories in literature/svgdigitizer/
    entry_dirs = set()
    for f in changed_files:
        f = f.strip()
        if f.startswith("literature/svgdigitizer/"):
            parts = Path(f).parts
            if len(parts) >= 3:
                entry_dir = Path(parts[0]) / parts[1] / parts[2]
                entry_dirs.add(entry_dir)

    if not entry_dirs:
        logger.info("No new literature entries found in this PR.")
        return []

    reports = []
    for entry_dir in sorted(entry_dirs):
        if entry_dir.exists():
            report = review_entry(entry_dir)
            reports.append(report)
            print(format_report(report))
            print()

    return reports
