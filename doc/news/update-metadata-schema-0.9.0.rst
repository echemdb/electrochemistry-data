**Added:**

* Added a checklist for updating the metadata-schema version to ``CONTRIBUTING.md``, and the rule that news entries for bulk changes describe what changed instead of listing the affected entries.
* Added a check to ``validate-input`` that every input YAML declares ``echemdbSchemaVersion`` equal to the current schema version.

**Changed:**

* Changed metadata-schema version from 0.8.3 to 0.9.0.
* Changed ``migrate-metadata`` to set ``echemdbSchemaVersion`` in all input YAML files, editing only the stamp line in files without structural changes.
