**Added:**

* Added a scheduled GitHub Actions workflow (``check-metadata-schema.yml``)
  that checks weekly for new ``echemdb/metadata-schema`` releases and opens a
  pull request bumping ``SCHEMA_VERSION`` in ``echemdb_ecdata/validate.py``
  when a newer version is available. The run is idempotent (it skips when an
  update branch or PR already exists) and uses an optional
  ``METADATA_SCHEMA_PAT`` secret so the generated PR triggers CI, falling back
  to ``GITHUB_TOKEN`` when the secret is not configured.
