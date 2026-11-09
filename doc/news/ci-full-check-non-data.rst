**Added:**

* Added ``validate-citation-keys`` to ``validate-input``, checking that every
  ``citationKey`` resolves to a bibliography entry.

**Changed:**

* Changed the ``data`` and ``Test`` CI workflows to trigger via
  ``paths-ignore`` instead of an allowlist, so that changes outside the
  data/documentation fast-path (e.g. workflows, ``util/``, ``pixi.lock``, root
  config) now run the full checks. Pure-documentation PRs are still skipped;
  ``Test`` additionally skips pure-data PRs.
* Changed the ``Validate Examples`` CI workflow to run ``validate-input`` on
  every PR.

**Removed:**

* Removed the ``Quick Data Check`` CI workflow, which is covered by
  ``Validate Examples``.

**Fixed:**

* Fixed ``validate-new-input`` skipping renamed entries and, for changes
  without a changed entry (e.g. bibliography only), the bibliography checks.
