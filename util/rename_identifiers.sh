#!/bin/bash
# Rename svgdigitizer directories and files to match updated citationKeys.
#
# Usage:
#   util/rename_identifiers.sh OLD_NAME NEW_NAME
#
# Example:
#   util/rename_identifiers.sh gomez_2003_effect_228 gomez_2004_effect_228
#
# This renames directories and files in both literature/svgdigitizer/ and
# data/generated/svgdigitizer/. Tracked files are renamed with `git mv`
# (two-step for Windows case-insensitive filesystem compatibility).
# Untracked files (e.g., PDFs) are renamed with plain `mv`.

set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 OLD_NAME NEW_NAME"
    echo "Example: $0 gomez_2003_effect_228 gomez_2004_effect_228"
    exit 1
fi

OLD_NAME="$1"
NEW_NAME="$2"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

cd "$REPO_DIR"

rename_dir() {
    local base_dir="$1"
    local old_path="$base_dir/$OLD_NAME"
    local new_path="$base_dir/$NEW_NAME"

    if [ ! -d "$old_path" ]; then
        echo "SKIP: $old_path does not exist"
        return
    fi

    echo "RENAMING: $old_path -> $new_path"

    # Rename files inside the directory first
    for f in "$old_path"/*; do
        [ -e "$f" ] || continue
        local basename
        basename=$(basename "$f")
        local newbasename="${basename/$OLD_NAME/$NEW_NAME}"
        if [ "$basename" != "$newbasename" ]; then
            if git ls-files --error-unmatch "$f" &>/dev/null; then
                # Two-step rename for Windows case-insensitive filesystem
                git mv "$f" "$f.tmp"
                git mv "$f.tmp" "$old_path/$newbasename"
            else
                mv "$f" "$old_path/$newbasename"
            fi
        fi
    done

    # Rename the directory itself
    if git ls-files "$old_path" | head -1 | grep -q .; then
        git mv "$old_path" "${old_path}.tmp"
        git mv "${old_path}.tmp" "$new_path"
    else
        mv "$old_path" "$new_path"
    fi
}

rename_dir "literature/svgdigitizer"
rename_dir "data/generated/svgdigitizer"

echo "Done: $OLD_NAME -> $NEW_NAME"
