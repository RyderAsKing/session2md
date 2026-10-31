import argparse
import json
from pathlib import Path
from .privacy import Redactor
from .exporter import export_vault
from .readers import discover


def main():
    parser = argparse.ArgumentParser(description='Export AI chats into an Obsidian vault. Run without arguments for the local interface.')
    commands = parser.add_subparsers(dest='command')
    ui = commands.add_parser('serve', help='Open the local browser interface')
    ui.add_argument('--port', type=int, default=8765)
    ui.add_argument('--no-browser', action='store_true')
    commands.add_parser('discover', help='Print detected local source paths')
    export = commands.add_parser('export', help='Export transcripts to Markdown')
    export.add_argument('--claude', help='Claude projects folder or JSONL file')
    export.add_argument('--t3', help='T3 userdata folder or SQLite database')
    export.add_argument('--codex', help='Codex home, sessions folder, or rollout JSONL file')
    export.add_argument('--chatgpt', help='ChatGPT export ZIP, JSON, or extracted folder')
    export.add_argument('--auto', action='store_true', help='Detect local Claude, T3, and Codex paths')
    export.add_argument('--output', '-o', required=True, help='Destination Obsidian vault folder')
    scope = export.add_mutually_exclusive_group()
    scope.add_argument('--folder', help='Only sessions recorded in this project folder or its descendants')
    scope.add_argument('--all', dest='all_chats', action='store_true', help='Explicitly export all sessions from selected sources')
    export.add_argument('--exact-folder', action='store_true', help='Exclude descendant working directories; requires --folder')
    export.add_argument('--dry-run', action='store_true', help='Scan and report counts without creating or changing any files')
    export.add_argument('--redact-file', help='UTF-8 file containing literal values to hide, one per line')
    export.add_argument('--reasoning', action='store_true', help='Include recorded Claude and Codex reasoning summaries')
    export.add_argument('--no-style', action='store_true', help='Do not write an Obsidian CSS snippet')
    export.add_argument('--demo', action='store_true', help='Export three sample conversations')
    args = parser.parse_args()
    if args.command in (None, 'serve'):
        from .server import serve
        serve(getattr(args, 'port', 8765), not getattr(args, 'no_browser', False))
        return 0
    if args.command == 'discover':
        print(json.dumps(discover(), indent=2))
        return 0
    sources = discover() if args.auto else {}
    for key in ('claude', 't3', 'codex', 'chatgpt'):
        if getattr(args, key):
            sources[key] = getattr(args, key)
    if not any(sources.values()) and not args.demo:
        parser.error('Choose --claude, --t3, --codex, --chatgpt, --auto, or --demo')
    if not args.folder and not args.all_chats and not args.demo:
        parser.error('Choose --folder PROJECT_PATH, or explicitly choose --all')
    literals = []
    try:
        if args.redact_file:
            literals = [line for line in Path(args.redact_file).expanduser().read_text(encoding='utf-8').splitlines() if line.strip()]
        result = export_vault(sources, args.output, reasoning=args.reasoning, style=not args.no_style, demo=args.demo, folder=args.folder, exact_folder=args.exact_folder,
                              all_chats=args.all_chats, literals=literals, dry_run=args.dry_run)
    except (ValueError, OSError) as exc:
        parser.exit(1, 'Export failed: ' + Redactor(literals if all(len(v) >= 3 for v in literals) else []).clean(str(exc)) + '\n')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result['warnings'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
