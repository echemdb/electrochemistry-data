**Added:**

* Added validation of filenames and identifiers against YAML/SVG metadata
  (``validate-identifiers``, ``validate-svgdigitizer-filenames``,
  ``validate-source-filenames``, ``validate-generated-identifiers``).
* Added validation of bibliography keys against the expected identifier
  convention (``validate-bib-keys``).
* Added validation that ``bibliography.bib`` uses UTF-8 instead of LaTeX
  accent encodings (``validate-bib-utf8``).
* Added ``fix-identifiers`` / ``fix-identifiers-dry-run`` tasks to
  auto-detect and rename directories and files where the directory name
  does not match the YAML ``citationKey``.
* Added ``fix-bib-utf8`` / ``fix-bib-utf8-dry-run`` tasks to convert
  LaTeX accent encodings (e.g., ``{\'o}``) to UTF-8 in ``bibliography.bib``.
* Added ``fix-lowercase`` / ``fix-lowercase-dry-run`` tasks to enforce
  lowercase SVG labels and filenames.
* Added ``rename-identifiers`` task for manual directory/file renames
  after a bibliography key change.
* Added ``echemdb_ecdata.bibliography`` module for bibliography validation
  and LaTeX-to-UTF-8 conversion utilities.
* Added ``echemdb_ecdata.validate`` module for identifier and filename
  validation and fix utilities.

**Fixed:**

* Fixed mismatched bibliography keys, YAML ``citationKey`` values, and
  filenames across the repository.
* Fixed LaTeX accent encodings in ``bibliography.bib`` (converted to UTF-8).
