r"""
This module contains methods for validating and processing
BibTeX bibliography files in the electrochemistry-data repository.

It provides utilities for:

- Converting LaTeX accent encodings to UTF-8 characters.
- Validating BibTeX keys against the identifier convention.
- Loading citation keys from a BibTeX file.

EXAMPLES:

Validate bib keys against the expected convention::

    >>> validate_bib_keys()  # doctest: +SKIP

Check for and convert LaTeX accent encodings to UTF-8::

    >>> has_latex_accents("Tam{\\'a}s")
    True
    >>> latex_to_utf8("Tam{\\'a}s")
    'Tamás'

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

import re
from re import Match

import latexcodec as _latexcodec  # noqa: F401  # registers "latex+latin1" codec
from pybtex.database import BibliographyData, parse_file, parse_string
from svgdigitizer.pdf import Pdf

# Mapping of LaTeX accent commands to their UTF-8 equivalents.
# Covers common accent types: acute ('), grave (`), umlaut ("),
# circumflex (^), tilde (~), and dotless i (\i).
LATEX_TO_UTF8 = {
    # acute accent (\')
    "\\'a": "á",
    "\\'e": "é",
    "\\'i": "í",
    "\\'o": "ó",
    "\\'u": "ú",
    "\\'A": "Á",
    "\\'E": "É",
    "\\'I": "Í",
    "\\'O": "Ó",
    "\\'U": "Ú",
    # grave accent (\`)
    "\\`a": "à",
    "\\`e": "è",
    "\\`i": "ì",
    "\\`o": "ò",
    "\\`u": "ù",
    "\\`A": "À",
    "\\`E": "È",
    "\\`I": "Ì",
    "\\`O": "Ò",
    "\\`U": "Ù",
    # umlaut (\")
    '\\"a': "ä",
    '\\"e': "ë",
    '\\"i': "ï",
    '\\"o': "ö",
    '\\"u': "ü",
    '\\"A': "Ä",
    '\\"E': "Ë",
    '\\"I': "Ï",
    '\\"O': "Ö",
    '\\"U': "Ü",
    # circumflex (\^)
    "\\^a": "â",
    "\\^e": "ê",
    "\\^i": "î",
    "\\^o": "ô",
    "\\^u": "û",
    "\\^A": "Â",
    "\\^E": "Ê",
    "\\^I": "Î",
    "\\^O": "Ô",
    "\\^U": "Û",
    # tilde (\~)
    "\\~a": "ã",
    "\\~n": "ñ",
    "\\~o": "õ",
    "\\~A": "Ã",
    "\\~N": "Ñ",
    "\\~O": "Õ",
    # cedilla (\c)
    "\\cc": "ç",
    "\\cC": "Ç",
    # dotless i (used in combinations like {\'\i} → í)
    "\\i": "ı",
}

# Pattern matching LaTeX accent encodings in braces, e.g., {\"u}, {\'\i}, {\'A}
_LATEX_ACCENT_PATTERN = re.compile(r"\{(\\['\"`~^c])(\\i|[a-zA-Z])\}")


def _replace_accent(match: Match[str]) -> str:
    r"""
    Replace a single LaTeX accent match with its UTF-8 equivalent.

    EXAMPLES::

        >>> import re
        >>> m = _LATEX_ACCENT_PATTERN.search("{\\\"u}")
        >>> _replace_accent(m)
        'ü'

        >>> m = _LATEX_ACCENT_PATTERN.search("{\\'\\i}")
        >>> _replace_accent(m)
        'í'

    Falls back to removing the braces if the combination is unknown::

        >>> m = _LATEX_ACCENT_PATTERN.search("{\\\"z}")
        >>> _replace_accent(m)
        '{\\"z}'

    """
    command = match.group(1)  # e.g., \' or \"
    char = match.group(2)  # e.g., a or \i

    # Handle dotless i: {\'\i} → the accent is applied to 'i'
    if char == "\\i":
        lookup = command + "i"
    else:
        lookup = command + char

    return LATEX_TO_UTF8.get(lookup, match.group(0))


def latex_to_utf8(text):
    r"""
    Convert LaTeX accent encodings in a string to UTF-8 characters.

    Converts patterns like ``{\"u}`` to ``ü`` and ``{\'\i}`` to ``í``.

    EXAMPLES::

        >>> latex_to_utf8("{\\\"u}")
        'ü'

        >>> latex_to_utf8("Tam{\\'a}s")
        'Tamás'

        >>> latex_to_utf8("Valent{\\'\\i}n")
        'Valentín'

        >>> latex_to_utf8("Gr{\\\"a}tzel")
        'Grätzel'

        >>> latex_to_utf8("G{\\'o}mez-Mar{\\'\\i}n")
        'Gómez-Marín'

    Text without LaTeX encodings is returned unchanged::

        >>> latex_to_utf8("plain text")
        'plain text'

        >>> latex_to_utf8("Gómez")
        'Gómez'

    """
    return _LATEX_ACCENT_PATTERN.sub(_replace_accent, text)


def has_latex_accents(text):
    r"""
    Check whether a string contains LaTeX accent encodings.

    EXAMPLES::

        >>> has_latex_accents("Tam{\\'a}s")
        True

        >>> has_latex_accents("Tamás")
        False

        >>> has_latex_accents("{\\\"u}")
        True

        >>> has_latex_accents("plain text")
        False

    """
    return bool(_LATEX_ACCENT_PATTERN.search(text))


def load_bib_keys(bib_path="literature/bibliography/bibliography.bib"):
    r"""
    Load all citation keys from a BibTeX file.

    EXAMPLES::

        >>> import tempfile, os
        >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.bib', delete=False) as f:
        ...     _ = f.write('@article{test_2024_example_1,\n  author={Test},\n}\n')
        ...     name = f.name
        >>> keys = load_bib_keys(name)
        >>> 'test_2024_example_1' in keys
        True
        >>> os.unlink(name)

    """
    keys = set()
    with open(bib_path, encoding="utf-8") as f:
        for line in f:
            match = re.match(r"@\w+\{([^,]+)", line)
            if match:
                keys.add(match.group(1).strip())
    return keys


def _escape_non_latin1(text):
    r"""
    Return ``text`` with characters outside latin-1 replaced by their
    LaTeX escape sequence (e.g. ``ć`` becomes ``\'c``).

    Hotfix for https://github.com/echemdb/svgdigitizer/issues/300:
    ``svgdigitizer.pdf.Pdf.build_identifier`` translates LaTeX escapes
    via a latin-1 round-trip and raises ``UnicodeEncodeError`` on UTF-8
    characters outside latin-1 (which ``bibliography.bib`` deliberately
    contains, since LaTeX accent encodings are forbidden by
    ``validate-bib-utf8``). Remove once fixed upstream.

    EXAMPLES::

        >>> _escape_non_latin1("Jović")
        "Jovi\\'c"

        >>> _escape_non_latin1("plain text")
        'plain text'

    """
    return "".join(
        char if ord(char) < 256 else char.encode("latex+latin1").decode("latin-1")
        for char in text
    )


def validate_bib_keys(
    bib_path="literature/bibliography/bibliography.bib",
):
    r"""
    Validate that BibTeX keys match the identifier convention.

    For each entry in the bibliography, computes the expected key
    using ``svgdigitizer.pdf.Pdf.build_identifier`` and compares
    it to the actual key. The expected format is::

        {first_author_last_name}_{year}_{first_meaningful_title_word}_{first_page}

    Returns a list of error messages (empty if all valid).

    EXAMPLES::

        >>> validate_bib_keys()  # doctest: +SKIP

    Entries with UTF-8 characters outside latin-1 (e.g. ``ć`` in author
    names or an em dash in the title) are validated without crashing
    (regression test for
    https://github.com/echemdb/svgdigitizer/issues/300)::

        >>> import tempfile, os
        >>> bib = (
        ...     '@article{jovic_1996_morphology_1,\n'
        ...     '  author = {Jović, B. M. and Adžić, R. R.},\n'
        ...     '  title = {Morphology of things — a study},\n'
        ...     '  year = {1996},\n'
        ...     '  pages = {1--10},\n'
        ...     '  journal = {J. Electroanal. Chem.},\n'
        ...     '}\n'
        ... )
        >>> with tempfile.NamedTemporaryFile(
        ...     mode='w', suffix='.bib', delete=False, encoding='utf-8'
        ... ) as f:
        ...     _ = f.write(bib)
        ...     name = f.name
        >>> validate_bib_keys(name)
        Validation of bibliography keys: checked 1 files, found 0 errors.
        []
        >>> os.unlink(name)

    """
    # Hotfix for https://github.com/echemdb/svgdigitizer/issues/300:
    # escape non-latin-1 characters as LaTeX sequences so that
    # Pdf.build_identifier's latin-1 round-trip does not crash.
    with open(bib_path, encoding="utf-8") as bib_file:
        content = _escape_non_latin1(bib_file.read())
    bib_data = parse_string(content, bib_format="bibtex")

    errors = []
    checked = 0

    for key, entry in bib_data.entries.items():
        checked += 1
        single = BibliographyData(entries={key: entry})
        try:
            expected = Pdf.build_identifier(single)
        except KeyError as exc:
            errors.append(
                f"MISSING FIELD: entry '{key}' is missing " f"required field {exc}"
            )
            continue

        if expected != key:
            errors.append(f"KEY MISMATCH: '{key}' != " f"expected '{expected}'")

    _print_validation_summary("bibliography keys", checked, errors)
    return errors


def validate_bib_utf8(
    bib_path="literature/bibliography/bibliography.bib",
):
    r"""
    Validate that a BibTeX file does not contain LaTeX accent encodings.

    Checks each line for patterns like ``{\"u}`` or ``{\'\i}``
    that should be replaced with UTF-8 characters.

    Returns a list of error messages (empty if all valid).

    EXAMPLES::

        >>> validate_bib_utf8()  # doctest: +SKIP

    """
    errors = []
    lineno = 0

    with open(bib_path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            matches = _LATEX_ACCENT_PATTERN.findall(line)
            if matches:
                encodings = _LATEX_ACCENT_PATTERN.finditer(line)
                for match in encodings:
                    errors.append(
                        f"LATEX ACCENT: line {lineno}: "
                        f"'{match.group(0)}' should be "
                        f"'{_replace_accent(match)}'"
                    )

    checked = lineno
    _print_validation_summary("bib UTF-8 encoding", checked, errors)
    return errors


def fix_bib_utf8(
    bib_path="literature/bibliography/bibliography.bib",
    dry_run=False,
):
    r"""
    Convert all LaTeX accent encodings to UTF-8 in a BibTeX file.

    Replaces patterns like ``{\"u}`` with ``ü`` and ``{\'\i}`` with ``í``.

    Use ``dry_run=True`` to preview changes without modifying the file.

    Returns a list of changes made (or that would be made).

    EXAMPLES::

        >>> fix_bib_utf8(dry_run=True)  # doctest: +SKIP

    """
    with open(bib_path, encoding="utf-8") as f:
        content = f.read()

    new_content = latex_to_utf8(content)

    if new_content == content:
        print("No LaTeX accent encodings found.")
        return []

    # Collect the individual changes for reporting
    changes = []
    for match in _LATEX_ACCENT_PATTERN.finditer(content):
        replacement = _replace_accent(match)
        changes.append(f"  '{match.group(0)}' -> '{replacement}'")

    if dry_run:
        print(f"Dry run: {len(changes)} LaTeX accents to convert:")
        for change in changes:
            print(change)
    else:
        with open(bib_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Converted {len(changes)} LaTeX accents to UTF-8.")

    return changes


def normalize_bib(
    bib_path="literature/bibliography/bibliography.bib",
    dry_run=False,
):
    r"""
    Normalize the formatting of a BibTeX file.

    Loads the BibTeX file with pybtex and re-saves it to produce
    consistent formatting (indentation, field delimiters, spacing).

    Use ``dry_run=True`` to preview whether changes would be made.

    Returns ``True`` if changes were made (or would be made), ``False`` otherwise.

    EXAMPLES::

        >>> normalize_bib(dry_run=True)  # doctest: +SKIP

    """
    with open(bib_path, encoding="utf-8") as f:
        original = f.read()

    bib_data = parse_file(bib_path, bib_format="bibtex")
    normalized = bib_data.to_string("bibtex")

    if normalized == original:
        print("Bibliography formatting is already normalized.")
        return False

    if dry_run:
        print("Dry run: bibliography formatting would be normalized.")
        return True

    with open(bib_path, "w", encoding="utf-8") as f:
        f.write(normalized)
    print("Bibliography formatting normalized.")
    return True


def _print_validation_summary(label, checked, errors):
    r"""Print a summary of validation results.

    EXAMPLES::

        >>> _print_validation_summary("test", 5, [])
        Validation of test: checked 5 files, found 0 errors.

        >>> _print_validation_summary("test", 3, ["error1", "error2"])
        error1
        error2
        Validation of test: checked 3 files, found 2 errors.

    """
    for error in errors:
        print(error)
    print(
        f"Validation of {label}: checked {checked} files, found {len(errors)} errors."
    )
