"""Deterministic identity of the executable backend, independent of metadata."""
import hashlib
from pathlib import Path


def fingerprint(directory):
    directory = Path(directory)
    if directory.is_symlink() or not (directory / "__init__.py").is_file():
        return ""
    digest = hashlib.sha256()
    try:
        paths = sorted(directory.rglob("*"))
        if any(p.is_symlink() for p in paths):
            return ""
        for path in paths:
            if path.is_file() and path.suffix == ".py" and "__pycache__" not in path.parts:
                name = path.relative_to(directory).as_posix().encode()
                data = path.read_bytes()
                digest.update(name + b"\0" + len(data).to_bytes(8, "big") + data)
    except OSError:
        return ""
    return digest.hexdigest()


def source_build(root):
    return fingerprint(Path(root) / "src/omarchy_workspaces")


def backend_build(paths):
    return fingerprint(paths.data / "omarchy-workspaces/omarchy_workspaces")
