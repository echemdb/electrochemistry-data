**Changed:**

* Changed metadata-schema version (``mdstools`` git tag and ``SCHEMA_VERSION``) from 0.8.3 to 0.9.0 and migrated the input YAML with ``pixi run -e dev migrate-metadata``. Breaking change: ``system.electrochemicalCell.cleaningProcedure`` was replaced by ``system.electrochemicalCell.preparationProcedure.description``.
