# Omarchy Workspaces · 1.2.0

Omarchy 原生工作区配置插件。用图形面板管理应用默认工作区、再次点击时的窗口复用和快捷键，同时保留终端配置与恢复能力。

**主目标：Omarchy 4.0.4 / Hyprland Lua。** 插件 ID 为 `lambert.workspaces`，通过根目录的 `manifest.json` 和 `Panel.qml` 接入 Omarchy Shell。Python 3.11+ 后端只在操作时运行，不增加独立常驻服务。

## 从 GitHub 安装与打开

在 Omarchy 桌面终端运行：

```bash
omarchy plugin add https://github.com/CoderLambert/omarchy-workspace-plugin.git --enable
bash ~/.config/omarchy/plugins/lambert.workspaces/install.sh --backend-only
```

第一条命令安装并启用原生面板；第二条安装 Python 后端和系统菜单入口。原生插件管理器只克隆仓库，不会执行后端安装脚本。之后打开 **Omarchy 系统菜单 → 工作区配置**，或执行：

```bash
~/.local/bin/omarchy-workspaces gui
```

也可从 GitHub 仓库选择 **Code → Download ZIP**，解压后在包含 `manifest.json`、`Panel.qml` 和 `install.sh` 的目录执行 `bash install.sh`；或者先克隆源码，再运行安装器：

```bash
git clone --depth 1 https://github.com/CoderLambert/omarchy-workspace-plugin.git ~/Downloads/omarchy-workspace-plugin
cd ~/Downloads/omarchy-workspace-plugin
bash install.sh
```

如需单文件离线安装，可下载仓库中的 `install-omarchy-workspaces.sh`。完整步骤见[安装、升级与卸载](docs/INSTALL.md)。

本项目源码托管于 [`CoderLambert/omarchy-workspace-plugin`](https://github.com/CoderLambert/omarchy-workspace-plugin)。目前没有单独的 GitHub Release 附件或插件市场条目。

## 首次配置

**默认安装只更新程序、插件和菜单，保留已有应用分配及生效规则。** 不会自动识别应用、打开探测窗口、整理当前窗口或接纳外部修改。已有 1.1.3 配置可以继续使用。

首次使用，在面板选择“自动预设…”，或执行：

```bash
~/.local/bin/omarchy-workspaces setup
```

`setup` 登记尚未配置的预设并整理已登记窗口；已有设置保留。识别部分应用时可能启动窗口。没有可信身份的应用会跳过。

| 工作区 | 预设应用 |
| --- | --- |
| 1 · AI | ChatGPT App、ChatGPT 网页、Grok Bot |
| 2 · 开发 | 终端、tmux、VS Code |
| 3 · 浏览器 | 普通浏览器 |
| 4 · 通信 | WeChat、Slack、X、Discord |

也可以先打开一个应用，再单独登记：

```bash
~/.local/bin/omarchy-workspaces add Obsidian --workspace 2
```

## 平时如何使用

面板支持搜索已登记应用、修改工作区与复用策略、打开应用、整理单个或全部应用，以及检查、应用、接纳外部修改、异常恢复和撤销设置。新增应用、预设识别和高级配置会打开终端，操作后回面板刷新。

| 需求 | 操作 |
| --- | --- |
| 从受管菜单再次打开应用 | 有窗口时聚焦最近使用的窗口，没有时调用原入口 |
| 保留手动移动的位置 | 复用策略 `focus`，默认值 |
| 每次打开都回到目标工作区 | 复用策略 `move` |
| 立即把窗口放回分配位置 | “保存并整理此应用”，或“整理全部” |
| 快捷键或重新捕获身份 | 高级配置，或 `omarchy-workspaces config --advanced` |
| 暂时撤销规则，保留插件 | `omarchy-workspaces reset`；以后用 `apply` 恢复 |
| 撤销接管并卸载入口 | `omarchy-workspaces uninstall` |

原 `.desktop` 的文件关联、D-Bus 设置和新建窗口等动作保留。复用针对受管菜单入口与快捷键；从其他程序直接执行原应用命令时，行为仍由应用自身决定。

## 从 1.1.3 升级

在新版解压目录执行：

```bash
bash install.sh --no-setup
~/.local/bin/omarchy-workspaces --version
~/.local/bin/omarchy-workspaces gui
```

`--no-setup` 与新版默认行为相同，明确保留原分配、不重新扫描。无需卸载旧版，不要删除状态目录。

此前若遇到 `grok-bot.desktop`“受管文件被其他工具修改”，先执行 `doctor`，核对报告指出的文件；确认改动应保留后再手动执行 `apply --adopt`。安装器不会替你做这一步。详见[故障排查](docs/TROUBLESHOOTING.md)。

## 其他安装方式与边界

| 方式 | 命令与说明 |
| --- | --- |
| 安装后立即识别预设 | `bash install.sh --setup` |
| 仅后端和配置菜单 | `bash install.sh --cli-only`，不安装面板 |
| 已由原生插件管理器克隆 | 面板首开安装后端，或在插件目录执行 `bash install.sh --backend-only` |
| 单文件离线安装 | `bash ~/Downloads/install-omarchy-workspaces.sh`，支持相同参数 |
| 查看参数 | `bash install.sh --help` |

未检测到所需 Omarchy Shell 插件命令时，安装器说明原因并保留终端入口。完整插件需要 Omarchy Shell/Quickshell；后端依赖 Python 3.11+、`hyprctl`、`gtk-launch`、`omarchy-launch-tui`，tmux 功能另需 `tmux`。

**Omarchy 的 `plugin disable` / `plugin remove` 只管理插件界面，不执行本工具的规则恢复。** 需要撤销工作区及入口接管时，先用 `reset`，或直接用本工具的 `uninstall`。

`uninstall` 保留分配表、后端副本和日志；Git 管理、手工安装或存在本地修改的插件目录会保留，并提示后续用原生 `plugin remove` 处理。由安装器创建且未修改的插件副本可直接移除。

仓库根目录可直接作为 Omarchy 原生插件使用。官方命令只克隆并启用插件，不执行后端安装脚本；请按上面的步骤补装后端。

## 完整文档

- [安装、升级与卸载](docs/INSTALL.md)
- [面板、CLI 与配置文件](docs/USAGE.md)
- [重复启动、外部修改、PWA 与恢复](docs/TROUBLESHOOTING.md)
- [发布为 Git 插件仓库](docs/PUBLISHING.md)
- [实现说明](IMPLEMENTATION.md)
- [更新记录](CHANGELOG.md)
- [验证记录与本机验收边界](TEST-REPORT.md)

本包未在你的真实 Omarchy 桌面运行。自动化结果见验证记录；真实面板、Chrome/PWA、Grok Bot、微信和终端身份仍须本机验收。

设计依据：Omarchy v4.0.4 [Shell 插件文档](https://github.com/omacom/omarchy/blob/v4.0.4/docs/omarchy-shell.md)、[Shell 接口说明](https://github.com/omacom/omarchy/blob/v4.0.4/shell/README.md)和[插件安装脚本](https://github.com/omacom/omarchy/blob/v4.0.4/bin/omarchy-plugin-add)。核对日期：2026-10-12（Asia/Shanghai）。
