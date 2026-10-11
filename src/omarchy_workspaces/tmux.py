"""Find terminal windows already attached to the configured tmux session."""
import subprocess
from pathlib import Path


TERMINALS = {'alacritty', 'kitty', 'foot', 'com.mitchellh.ghostty', 'org.wezfurlong.wezterm'}


def ancestors(pid):
    seen = set()
    while pid > 1 and pid not in seen and len(seen) < 64:
        seen.add(pid)
        try:
            # Process names may contain spaces and ')' characters.
            fields = (Path('/proc') / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()
            pid = int(fields[1])
        except (OSError, ValueError, IndexError):
            break
    return seen


def windows(app, clients):
    command = app.get('command', [])
    if 'tmux' not in command or '-s' not in command:
        return []
    try:
        session = command[command.index('-s') + 1]
        result = subprocess.run(['tmux', 'list-clients', '-F', '#{client_session}\t#{client_pid}'],
                                capture_output=True, text=True, timeout=2)
    except (OSError, subprocess.TimeoutExpired, IndexError):
        return []
    if result.returncode:
        return []
    pids = set()
    for line in result.stdout.splitlines():
        name, separator, pid = line.rpartition('\t')
        if separator and name == session and pid.isdigit():
            pids.update(ancestors(int(pid)))
    return [c for c in clients if c.get('mapped', True) and c.get('pid', 0) in pids
            and (c.get('initialClass') or c.get('class') or '').lower() in TERMINALS]
