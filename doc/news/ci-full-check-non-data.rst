**Changed:**

* Changed the ``data``, ``Test`` and ``Validate Examples`` CI workflows to
  trigger via ``paths-ignore`` instead of an allowlist, so that changes
  outside the data/documentation fast-path (e.g. workflows, ``util/``,
  ``pixi.lock``, root config) now run the full checks. Pure-documentation PRs
  are still skipped; ``Test`` and ``Validate Examples`` additionally skip
  pure-data PRs (covered by ``data`` and ``Quick Data Check``).
