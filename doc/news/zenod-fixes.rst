**Added:**

* Added support for authoring the Zenodo release description in a separate
  Markdown file (``zenodo-description.md``) via the ``--description`` option of
  ``zenodo-publish``. Markdown is rendered to HTML at publish time, so the
  description no longer has to be maintained as an escaped JSON string in
  ``zenodo.json``.
* Added CC-BY-4.0 and ODC-By-1.0 data-license badges to the README.
* Added a direct download link to the latest release ZIP and a note on
  downloading the archive from Zenodo to the README "Accessing Data" section.
  The release link's version is bumped automatically via ``rever.xsh``.
* Added documentation to the README that data can also be submitted directly as
  raw CSV files (under ``literature/source_data/``), in addition to data
  digitized from publications with ``svgdigitizer``.

**Fixed:**

* Fixed the generated data archive (and thus the release zip and Zenodo upload)
  not containing the license files. The ``convert`` task now copies
  ``LICENSE.md``, ``LICENSE-GPL-3.0-or-later``, ``LICENSE-CC-BY-4.0`` and
  ``LICENSE-ODC-By-1.0`` into ``data/generated``.

**Changed:**

* Changed the ``data/Makefile`` license and directory-creation recipes to use
  Python instead of the ``cp``/``mkdir`` Unix utilities so they also work on
  Windows.
