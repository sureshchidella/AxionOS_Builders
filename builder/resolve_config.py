#!/usr/bin/env python3
"""Resolve a trusted ROM source and device definition for a workflow run."""
import argparse
import json
import os
import re
import sys
from pathlib import Path

IDENTIFIER = re.compile(r"^[A-Za-z0-9._-]+$")
SAFE_BUILD_FLAGS = re.compile(r"^[A-Za-z0-9_./:=+@%,\- \t]*$")
REQUIRED_SOURCE = ("manifest_url", "manifest_branch", "build_command")


def load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read {path}: {exc}") from exc


def expand(value, device, build_type, variant):
    return value.format(
        device=device,
        build_type=build_type,
        variant=variant,
        # Keep this token intact until source defaults and per-build flags have
        # been combined and validated below.
        build_flags="{build_flags}",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--build-type", default="userdebug")
    parser.add_argument("--variant", default="")
    parser.add_argument("--extra-build-flags", default="")
    parser.add_argument("--config-dir", default="config")
    parser.add_argument("--github-env")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not IDENTIFIER.fullmatch(args.source) or not IDENTIFIER.fullmatch(args.device):
        raise ValueError("Source and device names may contain only letters, numbers, '.', '_' and '-'")
    if len(args.extra_build_flags) > 500 or not SAFE_BUILD_FLAGS.fullmatch(args.extra_build_flags):
        raise ValueError("Build flags may contain only argument characters (letters, numbers, spaces, -_.:/=+@%,)")

    root = Path(args.config_dir)
    sources = load_json(root / "sources.json").get("sources", {})
    source = sources.get(args.source)
    if not source:
        raise ValueError(f"Unknown ROM source '{args.source}'. Add it to {root}/sources.json")
    missing = [key for key in REQUIRED_SOURCE if not source.get(key)]
    if missing:
        raise ValueError(f"Source '{args.source}' is missing: {', '.join(missing)}")

    device = load_json(root / "devices" / f"{args.device}.json")
    local_manifest = device.get("local_manifest_url", "")
    if not local_manifest:
        raise ValueError(f"Device '{args.device}' needs local_manifest_url")

    build_flags = " ".join(filter(None, [source.get("build_flags", "").strip(), args.extra_build_flags.strip()]))
    build_command = expand(source["build_command"], args.device, args.build_type, args.variant)
    if "{build_flags}" not in source["build_command"] and build_flags:
        raise ValueError("Source build_command must include {build_flags} when build_flags are configured")
    build_command = build_command.replace("{build_flags}", build_flags)

    values = {
        "ROM_NAME": args.source,
        "ROM_MANIFEST_URL": source["manifest_url"],
        "ROM_MANIFEST_BRANCH": source["manifest_branch"],
        "BUILD_COMMAND": build_command,
        "BUILD_FLAGS": build_flags,
        "POST_SYNC_COMMAND": expand(source.get("post_sync_command", ""), args.device, args.build_type, args.variant),
        "ARTIFACT_GLOBS": ":".join(source.get("artifact_globs", ["out/target/product/{device}/*.zip"])),
        "LOCAL_MANIFEST_URL": local_manifest,
        "DEVICE_LABEL": device.get("name", args.device),
    }
    if args.github_env:
        with open(args.github_env, "a", encoding="utf-8") as output:
            for key, value in values.items():
                if "\n" in value or "\r" in value:
                    raise ValueError(f"{key} cannot contain a newline")
                output.write(f"{key}={value}\n")
    if args.json:
        print(json.dumps(values, indent=2))


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(2)
