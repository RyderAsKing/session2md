# Privacy and redaction

[Back to README](../README.md)

## Sensitive-content redaction

Automatic redaction is always enabled for exports and previews. It runs locally using deterministic patterns; no transcript is sent to an external model or service.

| Category | What it detects |
| --- | --- |
| `API_KEY` | Common OpenAI/Anthropic-style `sk-` tokens, GitHub token prefixes, Slack tokens, Google API key prefixes, and AWS access-key IDs |
| `PRIVATE_KEY` | Supported PEM/OpenSSH private-key blocks; a block without a closing marker is hidden through the end of that text field |
| `JWT` | JWT-shaped strings starting with `eyJ` and containing three encoded segments |
| `AUTHORIZATION` | Bearer and Basic authorization values |
| `URL_CREDENTIALS` | Username/password pairs in URLs such as database connection URLs |
| `SECRET_VALUE` | Values assigned to common password, token, secret, API-key, authorization, and cookie names in JSON, shell-style assignments, headers, and similar text |
| `EMAIL` | Common ASCII email-address forms |
| `SSN` | US Social Security number-shaped strings |
| `PAYMENT_CARD` | 13–19 digit card-shaped values that pass a Luhn checksum |
| `PHONE` | Common grouped ten-digit phone formats, optionally with an international prefix |
| `CUSTOM` | Your exact literal values |

For example, a message containing:

```text
DB_PASSWORD="fictional-example-password"
Contact: example.person@example.test
```

becomes:

```text
DB_PASSWORD="REDACTED-SECRET_VALUE"
Contact: REDACTED-EMAIL
```

Redaction covers normalized message bodies, tool calls and results, recorded reasoning text, user-derived titles, session metadata, project/workspace fields, branch labels, generated filenames, and generated indexes. Session IDs used as manifest lookup keys are hashed. User-visible session IDs are scanned before inclusion in frontmatter. Input warnings and export errors are scanned before display.

session2md writes **session2md privacy report.md** with rule-category counts for the current export. It stores no matched values, original excerpts, or recoverable secret map. The result returned by the CLI and interface also includes redaction counts. Counts represent matching occurrences across scanned fields, not unique secrets; a value repeated in a title and a message can count twice. A repeat export with a different set of input sources produces a report for that run, not the entire retained vault history.

Redaction changes the exported copy only. Original JSONL files and SQLite databases remain unchanged.

### Detection limits

Pattern matching can miss unknown token formats, encoded or split secrets, names, street addresses, medical details, proprietary prose, ungrouped phone numbers, and many international identifiers. It can also hide harmless examples and code values that look like credentials or personal details. A passing Luhn checksum does not prove that a number is a real payment card.

Workspace paths and ordinary project names remain visible unless a built-in rule matches them or you add a custom literal. This is a transcript exporter with a redaction pass, not an anonymity guarantee or encrypted vault. Review the generated files before sharing or publishing them.

Existing personal files in the destination are not scanned or scrubbed. A generated file you edited is preserved and reported as a conflict, so sensitive text you added to it remains there. Obsidian Sync, third-party plugins, and backup services operate separately from session2md.

## Add your own private values

Use custom literals for data that automatic patterns cannot identify, such as your name, a client name, an internal hostname, or a project directory.

In the interface, enter one exact value per line in **Also hide these exact values**. In the CLI, create a UTF-8 file, for example `~/private/session2md-redactions.txt`:

```text
Fictional Client Ltd
internal.example.test
/home/example/private-project
```

Then export:

```bash
python3 -m session2md export \
  --auto \
  --folder ~/projects/reading-app \
  --redact-file ~/private/session2md-redactions.txt \
  --output ~/Obsidian/reading-app-private
```

Custom literals are case-sensitive and are not regular expressions. Blank lines are ignored. Every nonblank value must have at least three characters. Leading and trailing spaces on a nonblank line are part of that value. Longer overlapping values take precedence. There is no comment syntax; a line beginning with `#` is still a literal value.

The literal file is read into memory. Its contents are not copied into the vault. The manifest stores a policy fingerprint derived from the literal hashes, not their original text. This fingerprint is not encryption for low-entropy values. Keep your own literal file private and use the same file on repeat exports.

Custom rules work after folder selection, so hiding the project directory does not prevent matching it. Changing the custom rule set requires a fresh output folder, as described in [repeat exports](exporting.md#repeat-exports-and-existing-vaults).
