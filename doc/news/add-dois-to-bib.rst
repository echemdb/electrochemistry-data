**Added:**

* Added DOIs to all entries in ``literature/bibliography/bibliography.bib`` that have one, taken from ``source.url`` of the corresponding YAML files, so that the ``bibdata`` shipped with each datapackage includes a persistent identifier (#179).
* Added ``pixi run -e dev validate-bib-dois`` (part of ``validate-input`` and ``validate-new-input``), which checks that the ``doi`` of each bibliography entry is a bare DOI and agrees with ``source.url`` of every entry citing it.

**Changed:**

* Changed the ``doi`` of ``sato_2006_effect_725`` from a URL to a bare DOI and removed the redundant ``url`` field of ``blizanac_2004_anion_625``.
