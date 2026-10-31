"""Match recorded working directories, not paths mentioned in a message."""
from pathlib import Path, PureWindowsPath


def normalize_folder(value: str):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Project folder must be a non-empty path')
    windows = PureWindowsPath(value)
    if windows.is_absolute():
        # PureWindowsPath does not collapse '..' itself.
        import ntpath
        return ('windows', tuple(p.casefold() for p in PureWindowsPath(ntpath.normpath(value)).parts))
    return ('posix', Path(value).expanduser().resolve().parts)


def matches_folder(workspace: str, folder: str, exact=False):
    if not workspace or not (Path(workspace).is_absolute() or PureWindowsPath(workspace).is_absolute() or workspace.startswith('~/')):
        return False
    kind, parts = normalize_folder(workspace)
    selected_kind, selected = normalize_folder(folder)
    return kind == selected_kind and (parts == selected if exact else parts[:len(selected)] == selected)
