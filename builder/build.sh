#!/usr/bin/env bash
set -euo pipefail

DEVICE="${1:?device is required}"
FULL_CLEAN="${2:-No}"

if [[ "$FULL_CLEAN" == "Yes" ]]; then
    echo "Cleaning out/"
    rm -rf out
fi

: "${BUILD_COMMAND:?BUILD_COMMAND is required}"
echo "Building $DEVICE with the configured ROM command"

# BUILD_COMMAND comes only from the version-controlled source catalog.  The
# resolver substitutes the documented placeholders before this point.
bash -lc "$BUILD_COMMAND"

DEFAULT_ARTIFACT_GLOB='out/target/product/{device}/*.zip'
IFS=':' read -r -a artifact_globs <<< "${ARTIFACT_GLOBS:-$DEFAULT_ARTIFACT_GLOB}"
for pattern in "${artifact_globs[@]}"; do
    pattern="$(printf '%s' "$pattern" | sed "s/{device}/$DEVICE/g")"
    while IFS= read -r artifact; do
        [[ -n "$artifact" ]] || continue
        echo "ROM_ZIP: $artifact"
        exit 0
    done < <(compgen -G "$pattern" || true)
done

echo "Build finished but no configured artifact was found." >&2
exit 1
