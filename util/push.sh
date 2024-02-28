#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Run this script as "util/push.sh sync" to delete all files remotely that are not present locally.
ACTION=${1:-copy}

echo "Pushing modified and new PDF documents…"
rclone "$ACTION" --progress --update --fast-list --size-only --include '*.pdf' `dirname "$SCRIPT_DIR"`/literature/svgdigitizer echemdb-private-crypt:
echo "Ok. Documents have been uploaded."
