r"""
Publish a new version of the echemdb data set to Zenodo.

This module exposes a ``zenodo-publish`` command (run via
``pixi run -e release zenodo-publish ...``) that creates a new version of an
existing Zenodo record, attaches the given release archive, applies the
metadata from ``zenodo.json`` and publishes the draft. It is invoked both
from the release CI workflow and locally.

By default the script targets the Zenodo sandbox
(``https://sandbox.zenodo.org``) so that the workflow can be tested without
publishing real records. Pass ``--production`` (or set
``ZENODO_PRODUCTION=1`` in the environment) to target the production
instance (``https://zenodo.org``).

EXAMPLES::

    >>> from echemdb_ecdata.test.cli import invoke
    >>> from echemdb_ecdata.zenodo.zenodo import cli
    >>> invoke(cli, "--help")  # doctest: +NORMALIZE_WHITESPACE
    Usage: cli [OPTIONS] COMMAND [ARGS]...

      Publish releases of the echemdb data set to Zenodo.

    Options:
      --help  Show this message and exit.
    Commands:
      publish  Create and publish a new version of an existing Zenodo record.

"""

# ********************************************************************
#  This file is part of echemdb_ecdata.
#
#        Copyright (C) 2026 Albert Engstfeld
#
#  echemdb_ecdata is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  echemdb_ecdata is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with echemdb_ecdata. If not, see <https://www.gnu.org/licenses/>.
# ********************************************************************
import datetime
import json
import logging
import os
from pathlib import Path

import click
import requests

logger = logging.getLogger("echemdb_ecdata.zenodo")

PRODUCTION_BASE_URL = "https://zenodo.org/api"
SANDBOX_BASE_URL = "https://sandbox.zenodo.org/api"


def _base_url(production: bool) -> str:
    return PRODUCTION_BASE_URL if production else SANDBOX_BASE_URL


# Fields that the Zenodo API returns but rejects (or ignores) on PUT because
# they are computed/read-only.
_READONLY_METADATA_FIELDS = frozenset(
    {"doi", "relations", "prereserve_doi", "access_right"}
)


def _normalize_creator(creator):
    r"""
    Convert a legacy Zenodo creator entry of the form
    ``{"name": "Family, Given", "affiliation": "..."}`` to the InvenioRDM
    shape ``{"person_or_org": {"family_name": ..., "given_name": ...,
    "name": ..., "type": "personal"}, "affiliations": [{"name": ...}]}``.

    Creators already in InvenioRDM shape (``person_or_org`` present) are
    returned unchanged.
    """
    if "person_or_org" in creator:
        return creator

    name = creator.get("name") or ""
    person = {"name": name, "type": "personal"}
    if "," in name:
        family, _, given = name.partition(",")
        family = family.strip()
        given = given.strip()
        if family:
            person["family_name"] = family
        if given:
            person["given_name"] = given
    normalized = {"person_or_org": person}

    affiliation = creator.get("affiliation")
    if affiliation:
        normalized["affiliations"] = [{"name": affiliation}]
    return normalized


def _normalize_resource_type(resource_type):
    r"""
    Convert a legacy resource_type ``{"type": "dataset"}`` to the InvenioRDM
    shape ``{"id": "dataset"}``. Values already containing ``id`` are
    returned unchanged.
    """
    if not isinstance(resource_type, dict):
        return resource_type
    if "id" in resource_type:
        return {"id": resource_type["id"]}
    if "type" in resource_type:
        return {"id": resource_type["type"]}
    return resource_type


def _normalize_metadata(metadata):
    r"""
    Return a copy of ``metadata`` with read-only fields stripped and legacy
    Zenodo fields converted to the InvenioRDM shape accepted by the new
    publish endpoint.
    """
    normalized = {
        key: value
        for key, value in metadata.items()
        if key not in _READONLY_METADATA_FIELDS
    }
    if "creators" in normalized and isinstance(normalized["creators"], list):
        normalized["creators"] = [
            _normalize_creator(creator) for creator in normalized["creators"]
        ]
    if "resource_type" in normalized:
        normalized["resource_type"] = _normalize_resource_type(
            normalized["resource_type"]
        )
    return normalized


def _check(response: requests.Response, action: str) -> dict:
    r"""
    Raise a descriptive error if ``response`` indicates failure, otherwise
    return its JSON body (or an empty dict for responses without a body).
    """
    if not response.ok:
        try:
            payload = response.json()
        except ValueError:
            payload = response.text
        raise click.ClickException(
            f"Zenodo {action} failed with status {response.status_code}: {payload}"
        )
    if response.status_code == 204 or not response.content:
        return {}
    return response.json()


# This function is a linear orchestration of the Zenodo REST workflow
# (fetch metadata, create draft, update metadata, replace files, publish);
# splitting it would obscure rather than clarify the flow, so we accept
# the larger argument and statement counts here.
# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-branches,too-many-statements
def publish_new_version(
    file_path: Path,
    version: str,
    record_id: str,
    token: str,
    production: bool = False,
    license_id: str = "cc-by-4.0",
    metadata_file: Path | None = None,
    publisher: str = "Zenodo",
    debug: bool = False,
) -> dict:
    r"""
    Create a new draft version of ``record_id`` on Zenodo, replace its files
    with ``file_path``, update its metadata and publish it.

    If ``metadata_file`` is given, its contents are used as the metadata base
    (the file may either be a Zenodo deposition metadata document wrapped in
    ``{"metadata": {...}}`` or the bare metadata object itself, in either the
    legacy Zenodo or the new InvenioRDM shape). Otherwise the metadata of the
    currently latest published version of ``record_id`` is used.

    Returns the published deposition resource as returned by Zenodo.
    """
    base_url = _base_url(production)
    headers = {"Authorization": f"Bearer {token}"}

    file_path = Path(file_path)
    if not file_path.is_file():
        raise click.ClickException(f"File not found: {file_path}")

    if metadata_file is not None:
        metadata_file = Path(metadata_file)
        if not metadata_file.is_file():
            raise click.ClickException(f"Metadata file not found: {metadata_file}")
        click.echo(f"Loading metadata from {metadata_file}.")
        with metadata_file.open("r", encoding="utf-8") as fp:
            loaded = json.load(fp)
        if (
            isinstance(loaded, dict)
            and "metadata" in loaded
            and isinstance(loaded["metadata"], dict)
        ):
            base_metadata = dict(loaded["metadata"])
        elif isinstance(loaded, dict):
            base_metadata = dict(loaded)
        else:
            raise click.ClickException(
                f"Metadata file {metadata_file} must contain a JSON object."
            )
    else:
        # Fetch the full metadata of the currently latest published version.
        # The POST /versions response and even the subsequent GET /draft strip
        # some required fields (``publication_date`` is intentionally cleared
        # on versioning, and records created via the legacy deposit UI may be
        # missing ``creators`` / ``resource_type`` from the draft response).
        # Using the published record as the metadata base avoids those gaps.
        click.echo(f"Fetching current metadata of record {record_id}.")
        latest = _check(
            requests.get(
                f"{base_url}/records/{record_id}/versions/latest",
                headers=headers,
                timeout=60,
            ),
            "latest version retrieval",
        )
        base_metadata = dict(latest.get("metadata") or {})
    if debug:
        click.echo(
            "Latest published metadata:\n"
            + json.dumps(base_metadata, indent=2, sort_keys=True)
        )

    click.echo(
        f"Creating a new draft version of record {record_id} on "
        f"{'production' if production else 'sandbox'} Zenodo ({base_url})."
    )
    draft = _check(
        requests.post(
            f"{base_url}/records/{record_id}/versions",
            headers=headers,
            timeout=60,
        ),
        "version creation",
    )
    draft_id = draft["id"]
    click.echo(f"Created draft deposition {draft_id}.")

    click.echo(f"Setting draft metadata (version={version!r}, license={license_id!r}).")
    # The new Zenodo API does a full replacement of ``metadata`` on PUT, so we
    # carry the metadata of the previously published version forward and only
    # override the fields we want to change for the new release. Records
    # originally created via the legacy deposit UI store metadata in the
    # legacy shape (e.g. ``creators[].name``, ``resource_type.type``); the
    # publish endpoint however validates against the new InvenioRDM schema,
    # so we transform the inherited metadata to that shape before sending.
    metadata = _normalize_metadata(base_metadata)
    metadata["version"] = version
    metadata["publication_date"] = datetime.date.today().isoformat()
    # ``publisher`` is required by the new Zenodo API for DOI registration
    # and is not part of the legacy deposit schema, so older records do not
    # expose it. Set a default if it is not already provided.
    metadata.setdefault("publisher", publisher)
    # The legacy API exposes the license as ``metadata.license = {"id": ...}``;
    # the new API uses ``metadata.rights = [{"id": ...}]`` (which also
    # supports listing multiple licenses, e.g. CC-BY-4.0 OR ODC-By-1.0 for
    # dual-licensed data). Anything provided in the metadata source
    # (typically ``zenodo.json``) takes precedence; otherwise fall back to
    # the ``--license`` value.
    if "rights" not in metadata:
        metadata["rights"] = [{"id": license_id}]
    if "license" not in metadata:
        # Mirror the first entry in ``rights`` for the legacy field.
        first = metadata["rights"][0]
        if isinstance(first, dict) and "id" in first:
            metadata["license"] = {"id": first["id"]}
    if debug:
        click.echo(
            "Metadata to PUT on draft:\n"
            + json.dumps(metadata, indent=2, sort_keys=True)
        )
    _check(
        requests.put(
            f"{base_url}/records/{draft_id}/draft",
            headers={**headers, "Content-Type": "application/json"},
            json={"metadata": metadata},
            timeout=60,
        ),
        "metadata update",
    )

    click.echo("Removing files inherited from the previous version.")
    files = _check(
        requests.get(
            f"{base_url}/records/{draft_id}/draft/files",
            headers=headers,
            timeout=60,
        ),
        "file listing",
    )
    for entry in files.get("entries", []):
        key = entry["key"]
        click.echo(f"  Deleting {key}.")
        _check(
            requests.delete(
                f"{base_url}/records/{draft_id}/draft/files/{key}",
                headers=headers,
                timeout=60,
            ),
            f"deletion of {key}",
        )

    upload_name = file_path.name
    click.echo(f"Registering {upload_name} on the draft.")
    _check(
        requests.post(
            f"{base_url}/records/{draft_id}/draft/files",
            headers={**headers, "Content-Type": "application/json"},
            json=[{"key": upload_name}],
            timeout=60,
        ),
        f"registration of {upload_name}",
    )

    click.echo(f"Uploading {file_path} as {upload_name}.")
    with file_path.open("rb") as fp:
        _check(
            requests.put(
                f"{base_url}/records/{draft_id}/draft/files/{upload_name}/content",
                headers={**headers, "Content-Type": "application/octet-stream"},
                data=fp,
                timeout=None,
            ),
            f"upload of {upload_name}",
        )
    _check(
        requests.post(
            f"{base_url}/records/{draft_id}/draft/files/{upload_name}/commit",
            headers=headers,
            timeout=60,
        ),
        f"commit of {upload_name}",
    )

    click.echo("Publishing the new version.")
    published = _check(
        requests.post(
            f"{base_url}/records/{draft_id}/draft/actions/publish",
            headers=headers,
            timeout=60,
        ),
        "publication",
    )
    doi = published.get("doi") or published.get("metadata", {}).get("doi")
    if doi:
        click.echo(f"Published new version with DOI {doi}.")
    else:
        click.echo("Published new version.")
    return published


def _production_default() -> bool:
    return os.environ.get("ZENODO_PRODUCTION", "").lower() in ("1", "true", "yes")


@click.group(help="Publish releases of the echemdb data set to Zenodo.")
def cli():
    r"""Entry point for the ``zenodo`` command line interface."""


@cli.command()
@click.option(
    "--file",
    "file_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to the file to upload (typically the release zip).",
)
@click.option(
    "--version",
    required=True,
    help="Version string to attach to the new deposition (e.g. the release tag).",
)
@click.option(
    "--record-id",
    envvar="ZENODO_RECORD_ID",
    required=True,
    help="Existing Zenodo record id whose concept is extended. "
    "Defaults to the ZENODO_RECORD_ID environment variable.",
)
@click.option(
    "--token",
    envvar="ZENODO_TOKEN",
    required=True,
    help="Zenodo personal access token. Defaults to the ZENODO_TOKEN "
    "environment variable.",
)
@click.option(
    "--production/--sandbox",
    default=None,
    help="Target the production Zenodo (https://zenodo.org) instead of the "
    "sandbox (https://sandbox.zenodo.org). Defaults to sandbox unless "
    "ZENODO_PRODUCTION=1 is set in the environment.",
)
@click.option(
    "--license",
    "license_id",
    default="cc-by-4.0",
    show_default=True,
    help="Fallback license identifier used only when the metadata source "
    "does not already define a `rights` list. To publish under multiple "
    "licenses, list them in `zenodo.json` under `metadata.rights` instead.",
)
@click.option(
    "--metadata",
    "metadata_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to a JSON file with the deposition metadata (either the raw "
    'metadata object or wrapped as `{"metadata": {...}}`, in either the '
    "legacy Zenodo or the InvenioRDM schema). If omitted, the metadata of "
    "the currently latest published version of the record is used.",
)
@click.option(
    "--publisher",
    default="Zenodo",
    show_default=True,
    help="Publisher name to record in the metadata if not already present. "
    "Zenodo requires this field for DOI registration.",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Print the metadata payload being sent to Zenodo. Useful for "
    "diagnosing validation errors from the API.",
)
# Each Click option maps 1:1 to a parameter of this command, so the argument
# count is determined by the user-facing CLI surface, not by internal design.
# pylint: disable=too-many-arguments,too-many-positional-arguments
def publish(
    file_path,
    version,
    record_id,
    token,
    production,
    license_id,
    metadata_file,
    publisher,
    debug,
):
    r"""Create and publish a new version of an existing Zenodo record."""
    if production is None:
        production = _production_default()
    publish_new_version(
        file_path=file_path,
        version=version,
        record_id=record_id,
        token=token,
        production=production,
        license_id=license_id,
        metadata_file=metadata_file,
        publisher=publisher,
        debug=debug,
    )


if __name__ == "__main__":
    cli()
