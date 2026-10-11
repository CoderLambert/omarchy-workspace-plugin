# 对照源码

以下文件取自 Omarchy v4.0.4，保留其 MIT 许可证 `omarchy-LICENSE`；仅用于理解平台接入，不是本工具运行依赖。

| 本地文件 | 原始路径 |
|---|---|
| `bin_omarchy-menu` | bin/omarchy-menu |
| `bin_omarchy-pkg-install` | bin/omarchy-pkg-install |
| `bin_omarchy-pkg-aur-install` | bin/omarchy-pkg-aur-install |
| `omarchy-menu.sample.jsonc` | config/omarchy/extensions/omarchy-menu.jsonc |
| `bin_omarchy-launch-tui` | bin/omarchy-launch-tui |
| `bin_omarchy-launch-terminal-tmux` | bin/omarchy-launch-terminal-tmux |
| `bin_omarchy-launch-webapp` | bin/omarchy-launch-webapp |
| `bin_omarchy-launch-or-focus` | bin/omarchy-launch-or-focus |
| `default_hypr_helpers.lua` | default/hypr/helpers.lua |
| `default_hypr_bindings_applications.lua` | default/hypr/bindings/applications.lua |
| `default_hypr_windows.lua` | default/hypr/windows.lua |
| `shell_services_AppLibrary.qml` | shell/services/AppLibrary.qml |

原始文件基址：<https://github.com/basecamp/omarchy/tree/v4.0.4>。

参考说明：<https://github.com/basecamp/omarchy/blob/v4.0.4/config/omarchy/extensions/omarchy-menu.jsonc>。

另核对基础包清单中的 obsidian：<https://github.com/omacom/omarchy/blob/v4.0.4/install/omarchy-base.packages>，以及 Arch 包提供的 desktop 路径：<https://archlinux.org/packages/extra/x86_64/obsidian/files/>。

Lua 快捷键取消行为对照 Hyprland v0.56.2 的 `src/config/lua/bindings/LuaBindingsToplevel.cpp` 和 `src/managers/KeybindManager.cpp`。本文不分发 Hyprland 的 C++ 源码：

- <https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/lua/bindings/LuaBindingsToplevel.cpp>
- <https://github.com/hyprwm/Hyprland/discussions/16095>

## 1.2.0 原生插件接口参考

以下追加文件同样来自 Omarchy v4.0.4，沿用本目录 `omarchy-LICENSE`。核对日期：2026-10-12（Asia/Shanghai）。

| 本地文件 | 官方源文件 | SHA-256 |
| --- | --- | --- |
| `bin_omarchy-plugin-add` | [bin/omarchy-plugin-add](https://github.com/omacom/omarchy/blob/v4.0.4/bin/omarchy-plugin-add) | `fc8eb1486275e308037ca8f284fbb0eb4e010dec593260519695c79414a4b9fb` |
| `bin_omarchy-plugin-validate` | [bin/omarchy-plugin-validate](https://github.com/omacom/omarchy/blob/v4.0.4/bin/omarchy-plugin-validate) | `f7507e5042eb970e3dc918bdf6bf251c7557443892a77e71a17d7019ddde72c8` |
| `bin_omarchy-plugin-remove` | [bin/omarchy-plugin-remove](https://github.com/omacom/omarchy/blob/v4.0.4/bin/omarchy-plugin-remove) | `ea4e4462ab75b28f249d5e03c03890a1821fd9f095346df34bcb431b2c1e3cc2` |
| `docs_omarchy-shell.md` | [docs/omarchy-shell.md](https://github.com/omacom/omarchy/blob/v4.0.4/docs/omarchy-shell.md) | `d68ce397fed867642b446533e506e6bd4fcde61872e5778e5518bf8bee26e3a3` |
| `shell_services_PluginShellApi.qml` | [shell/services/PluginShellApi.qml](https://github.com/omacom/omarchy/blob/v4.0.4/shell/services/PluginShellApi.qml) | `ff0cb5ec5fcdda0b21af447b11f07a24e065a3557796639364109aaa2ce5c763` |

另外核对 [PluginRegistry](https://github.com/omacom/omarchy/blob/v4.0.4/shell/services/PluginRegistry.qml) 的固定插件路径，以及 [Menu.qml](https://github.com/omacom/omarchy/blob/v4.0.4/shell/plugins/menu/Menu.qml) 的固定用户菜单路径。

Quickshell 异步命令与 Wayland 面板接口：[Process](https://quickshell.org/docs/v0.3.0/types/Quickshell.Io/Process/)、[WlrLayershell](https://quickshell.org/docs/v0.3.2/types/Quickshell.Wayland/WlrLayershell/)。这些在线类型说明不随包分发。
