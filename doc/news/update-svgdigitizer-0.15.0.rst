**Changed:**

* Changed svgdigitizer dependency from 0.14.5 to 0.15.0, which records the name and version of svgdigitizer as ``figureDescription.software`` in the generated data packages.

**Removed:**

* Removed the workaround for UTF-8 characters outside latin-1 in ``validate-bib-keys``, which svgdigitizer 0.15.0 handles itself.
