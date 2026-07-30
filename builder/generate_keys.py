#!/usr/bin/env python3
"""Generate signing keys using a source-owned, version-controlled recipe."""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def load_source(config_dir: Path, source_name: str):
    try:
        sources = json.loads((config_dir / "sources.json").read_text())["sources"]
        return sources[source_name]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load source '{source_name}': {exc}") from exc


def safe_path(root: Path, configured_path: str) -> Path:
    path = Path(configured_path)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Signing path must stay inside the source tree: {configured_path}")
    return root / path


def lineage_template(recipe: dict, source_dir: Path):
    template = safe_path(source_dir, recipe.get("template_path", "lineage/scripts/lineage-priv-template"))
    keys_dir = safe_path(source_dir, recipe.get("keys_path", "vendor/lineage-priv/keys"))
    if not template.is_dir():
        raise ValueError(f"Key template does not exist: {template}")
    if keys_dir.exists() and any(keys_dir.iterdir()):
        print(f"Keys already exist at {keys_dir}; leaving them untouched.")
        return
    keys_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template, keys_dir, dirs_exist_ok=True)
    key_script = keys_dir / "keys.sh"
    if not key_script.is_file():
        raise ValueError(f"Template does not contain keys.sh: {key_script}")
    print(f"Generating keys in {keys_dir}")
    subprocess.run(["bash", "./keys.sh"], cwd=keys_dir, check=True)


def scripted(recipe: dict, source_dir: Path):
    working_dir = safe_path(source_dir, recipe.get("working_directory", "."))
    commands = recipe.get("commands", [])
    if not working_dir.is_dir() or not isinstance(commands, list) or not commands or not all(isinstance(c, str) and "\n" not in c for c in commands):
        raise ValueError("Script signing recipe needs an existing working_directory and non-empty commands list")
    for command in commands:
        print(f"Running configured key-generation command in {working_dir}")
        subprocess.run(["bash", "-lc", command], cwd=working_dir, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--config-dir", default="config")
    args = parser.parse_args()

    recipe = load_source(Path(args.config_dir), args.source).get("signing", {"mode": "none"})
    mode = recipe.get("mode", "none")
    source_dir = Path(args.source_dir).resolve()
    if mode == "none":
        print("No signing-key recipe is configured for this source.")
    elif mode == "lineage-template":
        lineage_template(recipe, source_dir)
    elif mode == "script":
        scripted(recipe, source_dir)
    else:
        raise ValueError(f"Unsupported signing mode: {mode}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, subprocess.CalledProcessError) as exc:
        print(f"Key generation failed: {exc}", file=sys.stderr)
        sys.exit(2)
