import copy
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from omarchy_workspaces.cli import PRESETS, menu, setup
from omarchy_workspaces.core import binding_shortcut, empty_config
from omarchy_workspaces.discover import discover, entry_identity, observed_match, probe, score_entry, web_identity
from omarchy_workspaces.hypr import generate
from test_workspaces import Environment, cfg, client


class DiscoveryTests(Environment):
    def add_entry(self, name, desktop, identity="", command=None):
        path = self.system.parent / desktop
        path.write_text('[Desktop Entry]\nType=Application\nName=' + name + '\nExec=' + (command or desktop.removesuffix('.desktop')) + '\n' + ('StartupWMClass=' + identity + '\n' if identity else ''))

    def test_screenshot_mouse_binding_does_not_break_web_shortcut(self):
        self.assertIsNone(binding_shortcut({'modmask':64,'key':'mouse:272','arg':'window.drag'}))
        c = cfg()
        c['apps']['slack']['shortcuts'] = ['CTRL + SHIFT + A']
        c['apps']['slack']['replace_shortcuts'] = True
        text,_ = generate(c,'lua',self.p.binary,[{'modmask':64,'key':'mouse:272','arg':'window.drag'}])
        self.assertIn('hl.bind',text)

    def test_alacritty_is_detected_without_terminal_name_search(self):
        self.add_entry('Alacritty','Alacritty.desktop','Alacritty')
        self.h.clients = [client(cls='Alacritty')]
        result,status = discover(self.m,empty_config(),[next(p for p in PRESETS if p[0]=='terminal')],preferred_browser='')
        self.assertEqual(result['apps']['terminal']['desktop'],'Alacritty.desktop')
        self.assertEqual(result['apps']['terminal']['workspace'],2)
        self.assertFalse(result['apps']['terminal']['replace_shortcuts'])

    def test_native_chatgpt_and_web_are_separate_and_existing_setting_preserved(self):
        self.add_entry('ChatGPT','chatgpt.desktop','chatgpt')
        self.h.clients = [client(cls='chatgpt'),client('0x2',cls='chrome-chatgpt.com__-Default')]
        c=empty_config()
        c['apps']['chatgpt_app']={'name':'ChatGPT','workspace':1,'desktop':'chatgpt.desktop','matches':[{'initial_class':'chatgpt'}]}
        with patch('omarchy_workspaces.discover.shutil.which',return_value='/usr/bin/helper'):
            result,status=discover(self.m,c,[p for p in PRESETS if 'chatgpt' in p[0]],preferred_browser='')
        self.assertNotIn('chatgpt_web',result['aliases'])
        self.assertEqual(result['apps']['chatgpt_web']['matches'],[{'initial_class':'chrome-chatgpt.com__-Default'}])
        self.assertEqual(result['apps']['chatgpt_web']['shortcuts'],['SHIFT + CTRL + A'])
        self.assertEqual(result['apps']['chatgpt_app']['workspace'],1)

    def test_default_browser_beats_other_installed_browsers(self):
        self.add_entry('Google Chrome','google-chrome.desktop','google-chrome')
        self.add_entry('Firefox','firefox.desktop','firefox')
        result,_=discover(self.m,empty_config(),[next(p for p in PRESETS if p[0]=='browser')],preferred_browser='google-chrome.desktop')
        self.assertEqual(result['apps']['browser']['desktop'],'google-chrome.desktop')

    def test_grok_bot_does_not_silently_become_grok_website(self):
        entry={'id':'grok.desktop','Name':'Grok','Exec':'omarchy-launch-webapp https://grok.com'}
        self.assertEqual(score_entry('grok_bot',entry),0)

    def test_missing_or_ambiguous_apps_are_skipped_without_questions(self):
        self.add_entry('Visual Studio Code','code.desktop','Code')
        self.add_entry('Visual Studio Code','other-code.desktop','Code')
        with patch('builtins.input',side_effect=AssertionError('Must not prompt')):
            result,status=discover(self.m,empty_config(),[p for p in PRESETS if p[0] in ('vscode','grok_bot')],preferred_browser='')
        self.assertNotIn('vscode',result['apps'])
        self.assertNotIn('grok_bot',result['apps'])

    def test_native_app_does_not_use_generic_chrome_identity(self):
        self.h.clients=[client(cls='Google-chrome')]
        self.assertIsNone(observed_match(self.m,'chatgpt_app'))

    def test_auto_setup_has_no_input_and_arranges_existing_windows(self):
        self.add_entry('ChatGPT','chatgpt.desktop','chatgpt')
        self.h.clients=[client(cls='chatgpt',workspace=3)]
        presets=[next(p for p in PRESETS if p[0]=='chatgpt_app')]
        with patch('omarchy_workspaces.cli.PRESETS',presets),patch('builtins.input',side_effect=AssertionError('Must not prompt')),redirect_stdout(io.StringIO()):
            setup(self.m)
        self.assertEqual(self.h.moved,[('0x1',1)])

    def test_simple_menu_changes_workspace_and_moves_window(self):
        self.m.apply(cfg())
        self.h.clients=[client(workspace=4)]
        with patch('builtins.input',side_effect=['1','1','5','0']),redirect_stdout(io.StringIO()):
            menu(self.m)
        self.assertEqual(self.m.applied_config()['apps']['slack']['workspace'],5)
        self.assertEqual(self.h.moved,[('0x1',5)])

    def test_already_open_discord_webapp_is_detected_without_relaunch(self):
        self.add_entry('Discord','discord.desktop',command='omarchy-launch-webapp https://discord.com/app')
        self.h.clients=[client(cls='chrome-discord.com__app-Default')]
        with patch.object(self.m.desktops,'launch',side_effect=AssertionError('Already open')):
            result,_=discover(self.m,empty_config(),[next(p for p in PRESETS if p[0]=='discord')],preferred_browser='')
        self.assertEqual(result['apps']['discord']['matches'],[{'initial_class':'chrome-discord.com__app-Default'}])
        self.assertEqual(result['apps']['discord']['workspace'],4)

    def test_discord_pwa_matches_installed_app_id(self):
        app_id='a'*32
        entry={'Exec':'google-chrome --profile-directory=Default --app-id='+app_id}
        self.assertTrue(entry_identity(entry,'chrome-crx_'+app_id+'-Default'))
        self.assertFalse(entry_identity(entry,'chrome-crx_'+'b'*32+'-Default'))
        self.h.clients=[client(cls='chrome-crx_'+app_id+'-Default')]
        self.assertEqual(observed_match(self.m,'discord',entry),{'initial_class':'chrome-crx_'+app_id+'-Default'})

    def test_discord_webapp_never_matches_generic_chrome_or_other_domain(self):
        self.assertFalse(web_identity('discord','google-chrome'))
        self.assertFalse(web_identity('discord','chrome-chatgpt.com__-Default'))
        self.assertFalse(web_identity('discord','chrome-fake-discord.com__app-Default'))

    def test_discord_ptb_native_identity(self):
        self.h.clients=[client(cls='discord-ptb')]
        self.assertEqual(observed_match(self.m,'discord'),{'initial_class':'discord-ptb'})


if __name__=='__main__':
    unittest.main()
