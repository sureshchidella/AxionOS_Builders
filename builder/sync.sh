#!/usr/bin/env bash
set -euo pipefail

# Inputs are resolved from config/sources.json and devices/<codename>.json by
# resolve_config.py.  Do not put user supplied shell commands in this script.
LOCAL_MANIFEST_URL="${1:-}"
LOCAL_MANIFEST_PATH=".repo/local_manifests/rom-builder-device.xml"
MANIFEST_URL="${ROM_MANIFEST_URL:?ROM_MANIFEST_URL is required}"
MANIFEST_BRANCH="${ROM_MANIFEST_BRANCH:?ROM_MANIFEST_BRANCH is required}"

mkdir -p .repo/local_manifests
rm -f "$LOCAL_MANIFEST_PATH"

echo "Initializing $MANIFEST_URL ($MANIFEST_BRANCH)"
repo init -u "$MANIFEST_URL" -b "$MANIFEST_BRANCH" --depth=1 --git-lfs

if [[ -n "$LOCAL_MANIFEST_URL" ]]; then
    curl --fail --location --retry 3 --output "$LOCAL_MANIFEST_PATH" "$LOCAL_MANIFEST_URL"
fi

repo sync -c --no-clone-bundle --no-tags --optimized-fetch --prune --force-sync -j"$(nproc --all)"

if [[ -n "${POST_SYNC_COMMAND:-}" ]]; then
    echo "Running configured post-sync command"
    bash -lc "$POST_SYNC_COMMAND"
fi
