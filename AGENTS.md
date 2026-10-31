# Working on session2md

## Set up the checkout

Use Python 3.11 or newer. The app runs from the repository root with no runtime dependencies.

1. Read [setup](docs/setup.md) when installing or starting the app. For an editable install or packaging work, use the virtual-environment steps in [development](docs/development.md#environment).
2. Run `python3 -m session2md --help` to confirm the module loads.
3. Smoke-test setup with fictional data in a temporary directory:

   ```bash
   session2md_smoke=$(mktemp -d)
   python3 -m session2md export --demo --output "$session2md_smoke/vault"
   ```

   On Windows, use `py -3` and a temporary directory from PowerShell.
4. Setup is complete when the command exits successfully, reports three imported conversations without warnings, and creates `session2md home.md` and `.session2md-manifest.json` in the temporary vault.

## Configure an export

Read [folder matching](docs/exporting.md#how-folder-matching-works) and [privacy](docs/privacy.md) before configuring real history.

1. Identify the requested source history paths, project working folder, and output vault. These are three separate inputs. Use `python3 -m session2md discover` to find local history locations; its output contains local paths.
2. Use `--folder` for a project export. Select `--all` only when the user requests the full history. Preserve recursive versus exact-folder intent.
3. Keep private values in a local UTF-8 literal file supplied through `--redact-file`; keep that file outside the repository. Read the [custom-rule format](docs/privacy.md#add-your-own-private-values) when adding values. Redaction is built in and always enabled.
4. Run the requested selection with `--dry-run` first. Configuration is verified when the result has the intended matched/excluded counts and import warnings are resolved or explained. A preview creates no files. Zero matches means there is no export selection to write.
5. For an authorized export, reuse those arguments without `--dry-run`. Report the destination, counts, and any conflicts. Read [repeat-export rules](docs/exporting.md#repeat-exports-and-existing-vaults) if a policy or legacy-vault error occurs; use a fresh destination for a new policy.

The app has no configuration file. CLI flags and interface fields control an export; `CODEX_HOME` changes Codex discovery. Use [CLI and source reference](docs/reference.md) for supported inputs and options. Paths refer to the machine running the app.

## Change the code

Read [development](docs/development.md) for checks and module responsibilities. Keep the README short and put detailed instructions in the relevant `docs/` guide.

- Use fictional transcripts and temporary vaults for verification; keep real histories, literal files, and user vaults outside Git.
- Preserve read-only source handling, explicit export scope, redaction before generated output, and edit-aware manifest behavior.
- When changing detection rules, increment `session2md.privacy.VERSION` so older vaults cannot silently reuse a different policy.
- For reader changes, verify metadata and message parsing with fixtures for the affected source. For export/privacy changes, verify filenames, metadata, indexes, reports, and original-source immutability.
- After code changes, run the checks in [validation](docs/development.md#validation). For documentation-only changes, check local links and any commands you changed; the full test suite is optional.
