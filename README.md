# Configurable Android ROM Builder

This repository runs Android ROM builds on a self-hosted GitHub Actions runner and reports their progress through the optional Telegram bot. It is ROM-agnostic: ROM source details, device manifests, build commands and artifact locations are version-controlled configuration instead of being hard-coded for AxionOS.

## Configure a ROM source

Add a source to [config/sources.json](config/sources.json). A source defines the manifest repository and branch, the command used to compile a device, default build flags, optional post-sync setup, and where the completed ZIP is expected. Commands support `{device}`, `{build_type}`, `{variant}`, and `{build_flags}` placeholders.

```json
"my-rom": {
  "manifest_url": "https://github.com/example/android.git",
  "manifest_branch": "android-16.0",
  "build_flags": "-j32",
  "build_command": ". build/envsetup.sh && lunch myrom_{device}-{build_type} && mka bacon {build_flags}",
  "artifact_globs": ["out/target/product/{device}/*.zip"]
}
```

Default flags are version-controlled with the source. A requester may additionally supply argument-only flags through GitHub Actions' `EXTRA_BUILD_FLAGS` input or `/build <source> <device> [flags]`; shell operators, quotes and command substitutions are rejected. Put `{build_flags}` at the command location where those flags should be applied. Commands themselves remain version-controlled rather than accepted from Telegram or workflow input.

`sample_build_flags` is documentation-only and can be used to show maintainers valid flags for a source without enabling them by default. The included source lists `-j32` and `TARGET_BUILD_APPS=Settings` as examples.

## Signing keys

Each source can define an optional `signing` recipe. Choose **Generate signing keys** in GitHub Actions, or toggle it in the Telegram build menu (admin/owner only). Existing key directories are never overwritten.

Most Lineage-style ROMs use the built-in template mode, which performs the equivalent of `mkdir -p vendor/lineage-priv`, copies `lineage/scripts/lineage-priv-template` to `vendor/lineage-priv/keys`, and runs `./keys.sh` there:

```json
"signing": {
  "mode": "lineage-template",
  "template_path": "lineage/scripts/lineage-priv-template",
  "keys_path": "vendor/lineage-priv/keys"
}
```

For ROMs with a different signing layout, including Infinity-style trees, use `script` mode. Commands are source configuration reviewed in Git and run after syncing the tree:

```json
"signing": {
  "mode": "script",
  "working_directory": ".",
  "commands": [
    "mkdir -p vendor/infinity-priv/keys",
    "./vendor/infinity-priv/keys/generate-keys.sh"
  ]
}
```

Set `"mode": "none"` (or omit `signing`) for ROMs that do not generate keys this way.

## Configure a device

Create [config/devices/example.json](config/devices/example.json) as `config/devices/<codename>.json` and point `local_manifest_url` to the device manifest containing the device, vendor, kernel and common-tree projects.

```json
{
  "name": "My phone",
  "local_manifest_url": "https://raw.githubusercontent.com/my-org/manifests/main/mydevice.xml"
}
```

## Start a build

In GitHub Actions, run **Configurable ROM Builder** and supply:

- `ROM_SOURCE`: the key in `config/sources.json`.
- `DEVICE`: the device configuration filename without `.json`.
- The normal build type, clean and upload options.

With Telegram enabled, run:

```
/build <rom-source> <device> [build flags]
```

For example, `/build lineage example -j32`. The bot lets the requester select the remaining build options, then GitHub Actions resolves the source and device configuration from the checked-out revision. `/validate <manifest-url>` remains available to validate a local manifest before adding it to the device configuration.

## Runner requirements

The self-hosted Linux runner needs Android's `repo` tool, `git`, `git-lfs`, `tmux`, Python 3 and all build dependencies required by the chosen ROM. The workflow uses `$HOME/android/source` as the persistent source checkout; it requires enough disk space for that tree and its build output.

Install the Python dependencies for the bot/reporter with:

```bash
pip install -r requirements.txt
```

Copy `private.env.example` to `telegram-bot/private.env` when using the Telegram bot. Add the corresponding Actions secrets (`GH_PAT`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` and optional R2 credentials) in the repository settings.

## Operational notes

The workflow is designed for a self-hosted runner because a full Android checkout and build exceeds the practical limits of standard hosted runners. Build logs are streamed with tmux, successful artifact paths are detected from the configured glob, and the reporter can upload ROM ZIPs, images and optional R2 mirrors.
