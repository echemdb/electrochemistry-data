r"""
This module migrates literature metadata YAML files across breaking
metadata-schema releases.

It is a thin wrapper around the migration engine shipped with the
`metadata-schema repository <https://github.com/echemdb/metadata-schema>`_
(``mdstools.schema.migrate``). The individual migration steps (e.g. the 0.8.0
move of ``system.electrolyte.temperature`` to
``experimental.operationParameters.temperature``) are declared in
``mdstools.schema.migrations``; this module only applies them to all input
YAML files in ``literature/``.

Files with structural changes are rewritten with a comment-preserving YAML
round-trip (ruamel), so curator comments survive. All other files only get
their ``echemdbSchemaVersion`` line replaced (or appended), which leaves
their layout untouched. Thus every file is stamped with the target schema
version, which ``validate-input`` checks and future migrations use to
determine the pending steps.

EXAMPLES:

Preview the pending migrations without modifying any file::

    >>> migrate_metadata(dry_run=True)  # doctest: +SKIP

Apply them::

    >>> migrate_metadata()  # doctest: +SKIP

"""

# ********************************************************************
#  This file is part of electrochemistry-data.
#
#        Copyright (C) 2026 Albert Engstfeld
#
#  electrochemistry-data is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  electrochemistry-data is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with electrochemistry-data. If not, see <https://www.gnu.org/licenses/>.
# ********************************************************************

import glob
import os
import re

import yaml

from echemdb_ecdata.bibliography import _print_validation_summary
from echemdb_ecdata.validate import SCHEMA_VERSION

#: Input directories whose YAML files are migrated.
DATA_DIRS = ("literature/svgdigitizer", "literature/source_data")

#: A top-level ``echemdbSchemaVersion`` line (without its line break).
_STAMP_LINE = re.compile(r"^echemdbSchemaVersion:[^\r\n]*", re.MULTILINE)


def stamp_text(text, version):
    r"""
    Return the YAML ``text`` with its top-level ``echemdbSchemaVersion`` set
    to ``version``.

    An existing stamp line is replaced in place, otherwise the stamp is
    appended. Everything else, including the line endings, is left untouched.

    EXAMPLES::

        >>> stamp_text("source: x\necho: 1\nechemdbSchemaVersion: 0.8.2\n", "0.9.0")
        'source: x\necho: 1\nechemdbSchemaVersion: 0.9.0\n'
        >>> stamp_text("source: x\r\n", "0.9.0")
        'source: x\r\nechemdbSchemaVersion: 0.9.0\r\n'
        >>> stamp_text("source: x", "0.9.0")
        'source: x\nechemdbSchemaVersion: 0.9.0\n'

    Indented keys of the same name are not touched::

        >>> stamp_text("a:\n  echemdbSchemaVersion: 1\n", "0.9.0")
        'a:\n  echemdbSchemaVersion: 1\nechemdbSchemaVersion: 0.9.0\n'

    """
    line = f"echemdbSchemaVersion: {version}"
    if _STAMP_LINE.search(text):
        return _STAMP_LINE.sub(line, text, count=1)
    newline = "\r\n" if "\r\n" in text else "\n"
    if text and not text.endswith("\n"):
        text += newline
    return text + line + newline


def _stamp_file(yaml_file, version):
    r"""
    Set ``echemdbSchemaVersion`` in ``yaml_file`` to ``version`` with a
    text-level edit (see :func:`stamp_text`).

    EXAMPLES::

        >>> import os, tempfile
        >>> with tempfile.TemporaryDirectory() as tmp:
        ...     path = os.path.join(tmp, "entry.yaml")
        ...     with open(path, "w", encoding="utf-8", newline="") as f:
        ...         _ = f.write("source: x  # comment\n")
        ...     _stamp_file(path, "0.9.0")
        ...     with open(path, encoding="utf-8", newline="") as f:
        ...         f.read()
        'source: x  # comment\nechemdbSchemaVersion: 0.9.0\n'

    """
    with open(yaml_file, encoding="utf-8", newline="") as f:
        text = f.read()
    with open(yaml_file, "w", encoding="utf-8", newline="") as f:
        f.write(stamp_text(text, version))


def validate_schema_version_stamps(literature_dir="literature", version=None):
    r"""
    Validate that every YAML file below ``literature_dir`` declares
    ``echemdbSchemaVersion`` equal to ``version``.

    The stamp records the metadata-schema version a file is valid against, and
    the migration engine uses it to determine pending migration steps. All
    input files are therefore stamped by :func:`migrate_metadata` whenever
    :data:`echemdb_ecdata.validate.SCHEMA_VERSION` changes, and new files must
    carry the current stamp.

    Parameters
    ----------
    literature_dir : str
        Directory to search recursively for ``*.yaml`` files.
    version : str or None
        Expected version. Defaults to
        :data:`echemdb_ecdata.validate.SCHEMA_VERSION` when ``None``.

    Returns a list of error messages.

    EXAMPLES::

        >>> import os, tempfile
        >>> with tempfile.TemporaryDirectory() as tmp:  # doctest: +ELLIPSIS
        ...     for name, text in [("ok", "echemdbSchemaVersion: 0.9.0\n"),
        ...                        ("old", "echemdbSchemaVersion: 0.8.2\n"),
        ...                        ("none", "source: x\n")]:
        ...         with open(os.path.join(tmp, f"{name}.yaml"), "w") as f:
        ...             _ = f.write(text)
        ...     errors = validate_schema_version_stamps(tmp, "0.9.0")
        SCHEMA VERSION: ...none.yaml has no echemdbSchemaVersion. Add the line ...
        SCHEMA VERSION: ...old.yaml has echemdbSchemaVersion 0.8.2, expected 0.9.0. ...
        Validation of schema version stamps: checked 3 files, found 2 errors.

    """
    if version is None:
        version = SCHEMA_VERSION

    checked = 0
    errors = []
    for yaml_file in sorted(glob.glob(f"{literature_dir}/**/*.yaml", recursive=True)):
        checked += 1
        with open(yaml_file, encoding="utf-8") as f:
            metadata = yaml.safe_load(f) or {}
        stamp = metadata.get("echemdbSchemaVersion")
        if stamp is None:
            problem = "has no echemdbSchemaVersion"
            fix = (
                f"Add the line 'echemdbSchemaVersion: {version}' at the end of the file"
            )
        elif str(stamp) != version:
            problem = f"has echemdbSchemaVersion {stamp}, expected {version}"
            fix = f"Set it to {version}"
        else:
            continue
        errors.append(
            f"SCHEMA VERSION: {yaml_file} {problem}. {fix} "
            f"(after a schema update: run 'pixi run -e dev migrate-metadata')."
        )

    _print_validation_summary("schema version stamps", checked, errors)
    return errors


def migrate_metadata(data_dirs=DATA_DIRS, target_version=None, dry_run=False):
    r"""
    Migrate all input metadata YAML files to ``target_version``.

    Applies the migration steps registered in ``mdstools.schema.migrations``
    to every YAML file in ``data_dirs`` and stamps all files with
    ``echemdbSchemaVersion: <target_version>``.

    Files whose content changes beyond the version stamp are rewritten in
    place with a comment-preserving YAML round-trip. All other files only get
    their stamp line replaced or appended, since the round-trip renormalizes
    the YAML layout (indentation, line wrapping) and would reformat large
    parts of the repository for no structural gain.

    Parameters
    ----------
    data_dirs : iterable of str
        Directories to search recursively for ``*.yaml`` files.
    target_version : str or None
        Metadata-schema version to migrate to. Defaults to
        :data:`echemdb_ecdata.validate.SCHEMA_VERSION` when ``None``.
    dry_run : bool
        If ``True``, only report which files would change without modifying
        anything.

    Returns a list of the files that changed (or would change).

    EXAMPLES::

        >>> migrate_metadata(dry_run=True)  # doctest: +SKIP

    """
    # Imported lazily: mdstools requires Python >= 3.11 and is only installed
    # in the dev environment (see pyproject.toml).
    # pylint: disable=import-outside-toplevel
    from mdstools.schema.migrate import MetadataMigrator, migrate_file
    from mdstools.schema.validator import _load_data

    # pylint: enable=import-outside-toplevel

    if target_version is None:
        target_version = SCHEMA_VERSION

    yaml_files = sorted(
        f
        for data_dir in data_dirs
        for f in glob.glob(os.path.join(data_dir, "**/*.yaml"), recursive=True)
    )

    if not yaml_files:
        raise FileNotFoundError(f"No YAML files found in {', '.join(data_dirs)}")

    migrated_files = []
    stamped_files = []
    for yaml_file in yaml_files:
        data = _load_data(yaml_file)
        migrator = MetadataMigrator(data, target_version=target_version)
        migrated = migrator.migrated()
        if migrated == data:
            continue
        # Only the stamp changes: edit the stamp line, keep the layout.
        if migrated == {
            **data,
            "echemdbSchemaVersion": migrated["echemdbSchemaVersion"],
        }:
            stamped_files.append(yaml_file)
            if not dry_run:
                _stamp_file(yaml_file, target_version)
            continue
        migrated_files.append(yaml_file)
        steps = ", ".join(m.description for m in migrator.pending())
        print(f"{'[DRY RUN] ' if dry_run else ''}MIGRATE: {yaml_file} ({steps})")
        if not dry_run:
            migrate_file(yaml_file, target_version=target_version, in_place=True)

    verb = "would be" if dry_run else "were"
    print(
        f"\n{len(migrated_files)} file(s) {verb} migrated and "
        f"{len(stamped_files)} only stamped, out of {len(yaml_files)} checked; "
        f"target version {target_version}."
    )
    return migrated_files + stamped_files
