# Setup

[Back to README](../README.md)

Clone the repository first:

```bash
git clone https://github.com/RyderAsKing/session2md.git
cd session2md
```

Run from the repository root:

```bash
python3 --version
python3 -m session2md
```

On Windows:

```powershell
py -3 --version
py -3 -m session2md
```

The app opens at `http://127.0.0.1:8765`. Keep the terminal running while you use it. Stop it with Ctrl+C.

1. Check the detected history paths for Claude Code, T3 Code, and Codex. Disable sources you do not want to read.
2. Under **Which project do you want to export?**, enter the project working folder, such as `~/projects/reading-app`.
3. Keep **Include sessions started in subfolders** enabled, or turn it off for an exact directory match.
4. Add any private names, paths, or other exact values you want hidden in the custom-redaction field. Automatic detection is already on.
5. Choose a fresh destination, such as `~/Obsidian/reading-app-chats`.
6. Click **Preview counts** to check the selection and redaction counts without writing files.
7. Click **Export to Obsidian** when the selection is right.
8. Open the destination folder as a vault in Obsidian and start with **session2md home**.

The interface defaults to project-folder selection. An empty project field does not mean all chats. To export all available sessions, deliberately select **All chats from the enabled sources**.

To try it without reading your history, click **Create a sample vault**. That button exports three fictional conversations to a separate destination ending in `-demo`. A generated [sample vault](../examples/session2md/session2md%20home.md) is included in the repository.

If the port is busy or you do not want a browser opened automatically:

```bash
python3 -m session2md serve --port 8766 --no-browser
```

You can optionally install a `session2md` command:

```bash
python3 -m pip install .
session2md
```

For an isolated editable installation, see [development setup](development.md#environment). For export selection and repeat runs, see [exporting](exporting.md).
