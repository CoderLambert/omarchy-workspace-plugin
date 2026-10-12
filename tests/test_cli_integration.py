"""Installed CLI exercised through subprocesses with an isolated fake desktop IPC.

This checks our IPC orchestration and rollback, not the real Hyprland compositor.
"""
import ctypes
import ctypes.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from omarchy_workspaces.core import dumps, load
from omarchy_workspaces.hypr import generate


FAKE_TOOL = r'''
import json, os, re, sys, time
from pathlib import Path
path = Path(os.environ['OWS_TEST_IPC'])
data = json.loads(path.read_text())
args = sys.argv[1:]
tool = Path(sys.argv[0]).name
if tool == 'hyprctl':
    if args[:1] == ['-j']:
        if args[1] == 'version': print(json.dumps({'version':'0.55.0'}))
        elif args[1] == 'binds': print(json.dumps(data.get('binds',[])))
        elif args[1] == 'clients': print(json.dumps(data['clients']))
        elif args[1] == 'monitors': print(json.dumps(data.get('monitors', [])))
    elif args[:1] == ['reload']:
        data['binds'] = list(data.get('original_binds',[]))
        generated = Path(os.environ['XDG_CONFIG_HOME']) / 'hypr/app-workspaces.lua'
        for line in (generated.read_text() if generated.exists() else '').splitlines():
            found = re.match(r'hl\.(unbind|bind)\(("(?:\\.|[^"\\])*")',line)
            if not found: continue
            operation, encoded = found.groups()
            combo = json.loads(encoded)
            if operation == 'unbind': data['binds'] = [b for b in data['binds'] if b['combo'] != combo]
            else:
                mods = {'SHIFT':1,'CTRL':4,'ALT':8,'SUPER':64}
                parts = combo.split(' + ')
                desc = json.loads(re.search(r'description = ("(?:\\.|[^"\\])*")',line).group(1))
                data['binds'].append({'combo':combo,'modmask':sum(mods[m] for m in parts[:-1]),'key':parts[-1],'dispatcher':'__lua','arg':'42','description':desc})
        path.write_text(json.dumps(data))
        print('ok')
    elif args[:1] == ['configerrors']:
        generated = Path(os.environ['XDG_CONFIG_HOME']) / 'hypr/app-workspaces.lua'
        source = generated.read_text() if generated.exists() else ''
        print('simulated compositor error' if 'workspace = "13"' in source else '')
    elif args[:1] == ['dispatch']:
        expression = args[1]
        address = re.search(r'address:(0x[0-9a-f]+)', expression).group(1)
        if 'window.move' in expression:
            workspace = int(re.search(r'workspace = "(\d+)"', expression).group(1))
            for c in data['clients']:
                if c['address'] == address: c['workspace'] = {'id':workspace,'name':str(workspace)}
        else: data['focused'] = address
        path.write_text(json.dumps(data))
        print('ok')
elif tool == 'gtk-launch':
    data['launches'].append(args)
    count = len(data['launches'])
    data['clients'].append({'address':hex(count),'class':'Slack','initialClass':'Slack','title':'Slack','initialTitle':'Slack','mapped':True,'workspace':{'id':1,'name':'1'},'focusHistoryID':0})
    path.write_text(json.dumps(data))
elif tool == 'uwsm-app':
    os.execvp(args[1], args[1:])
elif tool == 'omarchy-menu':
    data['menu_refreshes'] = data.get('menu_refreshes',0) + 1
    path.write_text(json.dumps(data))
elif tool == 'omarchy-launch-tui':
    data.setdefault('tui_launches',[]).append(args)
    path.write_text(json.dumps(data))
'''


class InstalledCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='ows home ')
        self.root = Path(self.tmp.name)
        self.fakebin = self.root / 'fakebin'
        self.fakebin.mkdir()
        for name in ['hyprctl', 'gtk-launch', 'uwsm-app', 'omarchy-menu', 'omarchy-launch-tui']:
            path = self.fakebin / name
            path.write_text('#!' + sys.executable + '\n' + FAKE_TOOL)
            path.chmod(0o755)
        self.ipc = self.root / 'ipc.json'
        self.ipc.write_text(json.dumps({'clients':[], 'launches':[], 'focused':None}))
        self.env = dict(os.environ, HOME=str(self.root), XDG_CONFIG_HOME=str(self.root / 'config'), XDG_DATA_HOME=str(self.root / 'data'), XDG_STATE_HOME=str(self.root / 'state'), XDG_RUNTIME_DIR=str(self.root / 'run'), XDG_DATA_DIRS=str(self.root / 'system'), OWS_TEST_IPC=str(self.ipc), PATH=str(self.fakebin) + ':' + os.environ['PATH'], HYPRLAND_INSTANCE_SIGNATURE='integration')
        main = self.root / 'config/hypr/hyprland.lua'
        main.parent.mkdir(parents=True)
        main.write_text('-- custom user config\n')
        desktop = self.root / 'system/applications/slack.desktop'
        desktop.parent.mkdir(parents=True)
        desktop.write_text('[Desktop Entry]\nType=Application\nName=Slack\nExec=/usr/bin/slack %U\n')
        package = Path(__file__).resolve().parents[1]
        result = subprocess.run(['bash',str(package / 'install.sh'),'--no-setup'],capture_output=True,text=True,env=self.env,timeout=10)
        self.assertEqual(result.returncode,0,result.stdout + result.stderr)
        self.binary = self.root / '.local/bin/omarchy-workspaces'
        self.config = self.root / 'config/omarchy-workspaces/apps.toml'
        self.config.parent.mkdir(parents=True)
        self.c = {'defaults':{'launch_timeout':2,'backend':'auto'},'aliases':{},'apps':{'slack':{'name':'Slack','workspace':4,'desktop':'slack.desktop','matches':[{'initial_class':'Slack'}],'shortcuts':[]}}}
        self.config.write_text(dumps(self.c))

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self,*args,success=True):
        result = subprocess.run([str(self.binary),*args],capture_output=True,text=True,env=self.env,timeout=10)
        if success:
            self.assertEqual(result.returncode,0,result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode,0)
        return result

    def test_install_apply_launch_reuse_set_arrange_remove_and_uninstall(self):
        self.run_cli('apply')
        self.run_cli('launch','slack')
        self.run_cli('launch','slack')
        data = json.loads(self.ipc.read_text())
        self.assertEqual(len(data['launches']),1)
        self.assertEqual(data['clients'][0]['workspace']['id'],4)
        self.run_cli('set','slack','--workspace','5')
        self.run_cli('launch','slack')
        self.assertEqual(json.loads(self.ipc.read_text())['clients'][0]['workspace']['id'],4)
        self.run_cli('arrange')
        self.assertEqual(json.loads(self.ipc.read_text())['clients'][0]['workspace']['id'],5)
        self.run_cli('doctor')
        self.run_cli('launch','slack','--new')
        # GTK is launched asynchronously; wait on the observable effect, bounded.
        import time
        until = time.monotonic() + 2
        while len(json.loads(self.ipc.read_text())['launches']) < 2 and time.monotonic() < until:
            time.sleep(.02)
        self.assertEqual(len(json.loads(self.ipc.read_text())['launches']),2)
        self.run_cli('remove','slack')
        self.assertFalse((self.root / 'data/applications/slack.desktop').exists())
        self.run_cli('uninstall')
        self.assertFalse(self.binary.exists())
        self.assertFalse((self.root / '.config/omarchy/extensions/omarchy-menu.jsonc').exists())
        self.assertEqual((self.root / 'config/hypr/hyprland.lua').read_text().strip(),'-- custom user config')

    def test_compositor_rejection_rolls_back_through_installed_cli(self):
        self.run_cli('apply')
        config = self.config.read_bytes()
        source = self.root / 'config/hypr/app-workspaces.lua'
        generated = source.read_bytes()
        self.run_cli('set','slack','--workspace','13',success=False)
        self.assertEqual(self.config.read_bytes(),config)
        self.assertEqual(source.read_bytes(),generated)
        self.run_cli('doctor')

    def test_add_obsidian_automatically_finds_installed_entry_and_only_moves_it(self):
        desktop = self.root / 'system/applications/obsidian.desktop'
        desktop.write_text('[Desktop Entry]\nType=Application\nName=Obsidian\nExec=obsidian %U\n')
        data = json.loads(self.ipc.read_text())
        data['clients'] = [
            {'address':'0xa','class':'obsidian','initialClass':'obsidian','mapped':True,'workspace':{'id':6,'name':'6'}},
            {'address':'0xb','class':'Slack','initialClass':'Slack','mapped':True,'workspace':{'id':7,'name':'7'}},
        ]
        self.ipc.write_text(json.dumps(data))
        result = self.run_cli('add','Obsidian','--workspace','2')
        self.assertNotIn('入口类型', result.stdout)
        self.assertEqual(load(self.config)['apps']['obsidian']['desktop'], 'obsidian.desktop')
        updated = json.loads(self.ipc.read_text())
        self.assertEqual(updated['clients'][0]['workspace']['id'], 2)
        self.assertEqual(updated['clients'][1]['workspace']['id'], 7)
        self.assertEqual(updated['launches'], [])

    def test_advanced_add_rejects_flags_it_cannot_apply(self):
        before = self.config.read_bytes()
        result = self.run_cli('add','Obsidian','--advanced','--workspace','2',success=False)
        self.assertIn('不能同时指定', result.stderr)
        self.assertEqual(self.config.read_bytes(), before)

    def test_installed_cli_replaces_omarchy_binding_once_with_lua_callback_ipc(self):
        data = json.loads(self.ipc.read_text())
        data['original_binds'] = [{'combo':'SUPER + ALT + RETURN','modmask':72,'key':'RETURN','dispatcher':'__lua','arg':'7','description':'Tmux'}]
        self.ipc.write_text(json.dumps(data))
        self.c['apps']['slack'].update(shortcuts=['SUPER + ALT + Return'],replace_shortcuts=True)
        self.config.write_text(dumps(self.c))
        for _ in range(2):
            self.run_cli('apply')
            binds = json.loads(self.ipc.read_text())['binds']
            self.assertEqual(len(binds),1)
            self.assertEqual(binds[0]['description'],'工作区: Slack')

    def test_installer_adds_gui_menu_with_terminal_fallback(self):
        from omarchy_workspaces.menu import KEY, parse_jsonc
        from omarchy_workspaces.desktop import parse
        menu = self.root / '.config/omarchy/extensions/omarchy-menu.jsonc'
        row = parse_jsonc(menu.read_text())[KEY]
        self.assertEqual(row['label'],'工作区配置')
        result = subprocess.run(['bash','-c',row['action']],env=self.env,capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr)
        import time
        deadline = time.monotonic() + 2
        while 'tui_launches' not in json.loads(self.ipc.read_text()) and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertEqual(json.loads(self.ipc.read_text())['tui_launches'],[['--app-id=org.omarchy-workspaces.config',str(self.binary),'config']])
        desktop = parse((self.root / 'data/applications/ows-config.desktop').read_text())
        self.assertEqual(desktop['Terminal'],'false')
        self.assertIn('"gui"',desktop['Exec'])
        menu.unlink()
        self.run_cli('repair-menu')
        self.assertIn(KEY,parse_jsonc(menu.read_text()))


class LuaSyntaxTests(unittest.TestCase):
    def test_generated_lua_loads_and_runs_in_native_lua_vm(self):
        name = ctypes.util.find_library('lua5.4')
        if not name:
            self.skipTest('native Lua 5.4 unavailable; compositor validation still required')
        lib = ctypes.CDLL(name)
        lib.luaL_newstate.restype = ctypes.c_void_p
        lib.luaL_openlibs.argtypes = [ctypes.c_void_p]
        lib.luaL_loadstring.argtypes = [ctypes.c_void_p,ctypes.c_char_p]
        lib.lua_pcallk.argtypes = [ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_longlong,ctypes.c_void_p]
        lib.lua_tolstring.argtypes = [ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(ctypes.c_size_t)]
        lib.lua_tolstring.restype = ctypes.c_char_p
        lib.lua_close.argtypes = [ctypes.c_void_p]
        c = {'defaults':{},'aliases':{},'apps':{'web':{'name':'聊天 "应用"','workspace':1,'command':['example'],'matches':[{'initial_class':'a.b[你好]'}],'shortcuts':['CTRL + SHIFT + A'],'replace_shortcuts':True}}}
        source, _ = generate(c,'lua',Path('/a path/ows'),[])
        harness = '''
        hl = { dsp = {} }
        function hl.window_rule(rule) assert(type(rule.match.initial_class) == 'string'); assert(rule.workspace == '1'); assert(rule.focus_on_activate == true) end
        function hl.unbind(key) assert(type(key) == 'string') end
        function hl.dsp.exec_cmd(cmd) assert(type(cmd) == 'string'); return cmd end
        function hl.bind(key, cmd, opts) assert(type(opts.description) == 'string') end
        '''
        state = lib.luaL_newstate()
        try:
            lib.luaL_openlibs(state)
            loaded = lib.luaL_loadstring(state,(harness + source).encode())
            self.assertEqual(loaded,0,lib.lua_tolstring(state,-1,None))
            executed = lib.lua_pcallk(state,0,0,0,0,None)
            self.assertEqual(executed,0,lib.lua_tolstring(state,-1,None))
        finally:
            lib.lua_close(state)
