"""Build a complete source ZIP, offline installer and SHA-256 file manifest."""
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


root = Path(__file__).resolve().parent
version = re.search(r'__version__ = "([^"]+)"', (root / 'src/omarchy_workspaces/__init__.py').read_text()).group(1)
output = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root.parent / f'omarchy-workspaces-plugin-{version}.zip'
output.parent.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='ows-source-') as temp:
    temp = Path(temp)
    installer = temp / 'install-omarchy-workspaces.sh'
    subprocess.run([sys.executable, str(root / 'build_release.py'), str(installer)], check=True)
    source = temp / 'source'
    subprocess.run(['bash', str(installer), '--extract', str(source)], check=True)
    shutil.copy2(installer, source / installer.name)
    files = sorted(p for p in source.rglob('*') if p.is_file())
    hashes = '\n'.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + str(p.relative_to(source)) for p in files) + '\n'
    (source / 'SHA256SUMS').write_text(hashes)
    files.append(source / 'SHA256SUMS')
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, str(Path('omarchy-workspaces') / path.relative_to(source)))
print(f'{output}: {output.stat().st_size} bytes, {len(files)} files')
