**Added:**

* Added support for authoring the Zenodo release description in a separate
  Markdown file (``zenodo-description.md``) via the ``--description`` option of
  ``zenodo-publish``. Markdown is rendered to HTML at publish time, so the
  description no longer has to be maintained as an escaped JSON string in
  ``zenodo.json``.

**Fixed:**

* Fixed the generated data archive (and thus the release zip and Zenodo upload)
  not containing the license files. The ``convert`` task now copies
  ``LICENSE.md``, ``LICENSE-GPL-3.0-or-later``, ``LICENSE-CC-BY-4.0`` and
  ``LICENSE-ODC-By-1.0`` into ``data/generated``.

**Changed:**

* Changed the ``data/Makefile`` license and directory-creation recipes to use
  Python instead of the ``cp``/``mkdir`` Unix utilities so they also work on
  Windows.
