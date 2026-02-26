**Added:**

* Added ``echemdb_ecdata.digitize`` module with batch conversion functions
  ``digitize_svgdigitizer_data()`` and ``convert_source_data()`` that process
  all files in a single Python process, avoiding ~3 s import overhead per file.
* Added ``verify_batch_conversion()`` and ``compare_generated_output()`` utilities
  to verify that batch conversion produces output identical to existing data.
* Added pixi tasks ``convert-force``, ``convert-svg-force``, ``convert-raw-force``
  for full rebuilds ignoring timestamps.
* Added pixi tasks ``verify-svg``, ``verify-raw``, ``verify-all`` for output
  verification.

**Changed:**

* Raw source-data conversion (``convert-raw``) now uses the same batch approach
  as SVG conversion instead of spawning one subprocess per file via Make.

**Performance:**

* Full rebuild of 273 SVG files reduced from ~15 min to ~30-50 s by eliminating
  per-file Python startup and import overhead.
* Source-data conversion similarly improved by batch processing.
