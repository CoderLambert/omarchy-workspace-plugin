"""Create an offline self-extracting installer from this source tree."""
import base64
import hashlib
import io
import re
import shlex
import sys
import textwrap
import zipfile
from pathlib import Path


root = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(root / 'src'))
from omarchy_workspaces.installer import payload_files

buffer = io.BytesIO()
files = payload_files(root)
with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in files:
        archive.write(path, str(Path('omarchy-workspaces') / path.relative_to(root)))
payload = buffer.getvalue()
code = '''
import base64, hashlib, io, pathlib, shutil, subprocess, sys, tempfile, zipfile
source = pathlib.Path(sys.argv[1]).read_text()
encoded = source.split('\\n# __OWS_WORKSPACES_PAYLOAD__\\n', 1)[1]
payload = base64.b64decode(''.join(encoded.splitlines()), validate=True)
if hashlib.sha256(payload).hexdigest() != DIGEST:
    raise SystemExit('安装包校验失败')
with tempfile.TemporaryDirectory(prefix='omarchy-workspaces-') as temp:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for item in archive.infolist():
            parts = pathlib.PurePosixPath(item.filename)
            if parts.is_absolute() or '..' in parts.parts:
                raise SystemExit('安装包含无效路径')
        archive.extractall(temp)
    root = pathlib.Path(temp) / 'omarchy-workspaces'
    args = sys.argv[2:]
    if args[:1] == ['--extract']:
        if len(args) != 2:
            raise SystemExit('用法: bash install-omarchy-workspaces.sh --extract 新目录')
        target = pathlib.Path(args[1]).expanduser()
        shutil.copytree(root, target)
        print('已解压完整源码、测试与文档到 ' + str(target))
    else:
        # Preserve terminal stdin for the optional configuration menu.
        result = subprocess.run(['bash', str(root / 'install.sh'), *args])
        raise SystemExit(result.returncode)
'''.replace('DIGEST', repr(hashlib.sha256(payload).hexdigest()))
output = Path(sys.argv[1] if len(sys.argv) > 1 else root.parent / 'install-omarchy-workspaces.sh')
version = re.search(r'__version__ = "([^"]+)"', (root / 'src/omarchy_workspaces/__init__.py').read_text()).group(1)
# Linux bounds each argv string. Keep the loader small and read the payload
# from this file, while leaving stdin attached to the user's terminal.
encoded_payload = '\n'.join(textwrap.wrap(base64.b64encode(payload).decode(), 100))
output.write_text('#!/usr/bin/env bash\n# Omarchy Workspaces ' + version + ' — offline installer\nset -euo pipefail\nexec python3 -B -c ' + shlex.quote(code) + ' "${BASH_SOURCE[0]}" "$@"\n# __OWS_WORKSPACES_PAYLOAD__\n' + encoded_payload + '\n')
output.chmod(0o755)
print(f'{output}: {output.stat().st_size} bytes')
