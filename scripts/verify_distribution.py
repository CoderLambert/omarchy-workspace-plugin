"""Verify a built ZIP and its offline installer without installing on the host."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

sys.dont_write_bytecode = True
with tempfile.TemporaryDirectory(prefix='workspaces-distribution-') as directory:
    folder = Path(directory)
    with zipfile.ZipFile(sys.argv[1]) as archive:
        for name in archive.namelist():
            path = Path(name)
            if path.is_absolute() or '..' in path.parts:
                raise SystemExit('Unsafe ZIP path')
        archive.extractall(folder)
    root = folder / 'omarchy-workspaces'
    for line in (root / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        path = Path(name)
        if path.is_absolute() or '..' in path.parts:
            raise SystemExit('Unsafe checksum path')
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != digest:
            raise SystemExit('Checksum mismatch: ' + name)
    required = ['LICENSE', 'qml/Strings.js', 'qml/Theme.qml', 'tests/ui/tst_workspaces.qml', 'src/omarchy_workspaces/build.py']
    for name in required:
        if not (root / name).is_file():
            raise SystemExit('Missing distribution file: ' + name)
    extracted = folder / 'offline'
    subprocess.run(['bash', str(root / 'install-omarchy-workspaces.sh'), '--extract', str(extracted)], check=True)
    for name in required:
        if (extracted / name).read_bytes() != (root / name).read_bytes():
            raise SystemExit('Offline payload mismatch: ' + name)
print('ZIP checksums, GPL license, backend build identity and offline payload verified')
