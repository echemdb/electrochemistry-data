#!/usr/bin/env python3
"""
Sync configuration values from config.toml to pyproject.toml.

This script reads the schema version from config.toml and updates
the default values in pyproject.toml task definitions.
"""

import re
import tomllib
from pathlib import Path


def sync_schema_version():
    """Read schema version from config.toml and update pyproject.toml."""
    # Get the repository root (script is in scripts/ subdirectory)
    repo_root = Path(__file__).parent.parent.resolve()

    # Read config.toml
    config_path = repo_root / "config.toml"
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    schema_version = config.get("schema", {}).get("version")
    if not schema_version:
        raise ValueError("schema.version not found in config.toml")

    # Read pyproject.toml
    pyproject_path = repo_root / "pyproject.toml"
    with open(pyproject_path, "r") as f:
        content = f.read()

    # Replace version in default tags
    old_pattern = r'"default"\s*=\s*"tags/[0-9]+\.[0-9]+\.[0-9]+"'
    new_value = f'"default" = "tags/{schema_version}"'

    updated_content = re.sub(old_pattern, new_value, content)

    if updated_content == content:
        print(f"✓ pyproject.toml already has version tags/{schema_version}")
    else:
        with open(pyproject_path, "w") as f:
            f.write(updated_content)
        print(f"✓ Updated pyproject.toml with schema version tags/{schema_version}")


if __name__ == "__main__":
    sync_schema_version()
