# Omarchy Workspaces

**让应用各归其位，再次打开时直接回到已有窗口。**

[English](README.md) | [**简体中文**](README.zh-CN.md)

Omarchy Workspaces 是面向 [Omarchy](https://github.com/omacom/omarchy) 的原生工作区管理插件。你可以为应用指定默认 Hyprland 工作区，通过受管启动器复用已有窗口，不必手写窗口规则，也不必反复寻找应用。

> **发布状态：** `1.3.0-rc.1`（公开 Beta / RC）。主要适配 Omarchy 4.0.4 与 Hyprland Lua 配置。2026-10-13 已由用户完成新版界面的真实桌面验收，正式稳定版标签尚未发布。
>
> **新版界面：** 按工作区分组、点击应用再编辑的新版已通过 [PR #1](https://github.com/CoderLambert/omarchy-workspace-plugin/pull/1) 合并到 `main`，无需切换分支即可安装。

普通快捷键新建受管窗口时，画面会自动切到它的默认工作区；已有窗口请求激活时也会聚焦。通过受管入口再次唤出应用时，直接聚焦已有窗口；使用 focus 保留窗口当前位置，使用 move 则先移回默认工作区。默认不添加或替换系统快捷键。

## 实际使用截图

![Omarchy Workspaces 实际运行界面：按工作区分组管理应用](preview.png)

*来自真实 Omarchy 桌面，已获截图提供者许可使用。图中的应用分配可自行修改。*

## 核心功能

| 功能 | 说明 |
| --- | --- |
| **固定应用工作区** | 支持 `1–999` 工作区编号，受管应用新建窗口时按分配进入目标工作区。 |
| **已有窗口复用** | 通过受管菜单、启动器或已授权快捷键打开应用时，优先定位已有窗口，避免不必要的重复启动。 |
| **灵活的再次打开策略** | 可以保留已有窗口的当前位置并聚焦，也可以先移动回默认工作区再聚焦。 |
| **Scratchpad 兼容** | 在 `Super+S` 临时工作区可见时启动应用，可以让窗口留在临时工作区；普通启动仍遵守默认分配。 |
| **原生图形界面** | 跟随 Omarchy 主题、字体和缩放，提供中文、英文界面。 |
| **安全配置与恢复** | 快捷键冲突逐项确认、保留原有分配、检测受管文件外部修改，支持检查、恢复和撤销规则。 |

Python 后端只在需要时执行，不安装新的常驻后台服务。安装阶段**不会自动接管应用，也不会自动移动现有窗口**。

## 环境要求

- **Omarchy 4.0.4**（主要验证目标）、Omarchy Shell / Quickshell 及其原生插件管理命令。
- **Python 3.11+**、Hyprland `hyprctl`、`gtk-launch`、`omarchy-launch-tui`。
- 仅使用可选 tmux 功能时才需要 `tmux`。

请在已登录的 Omarchy 桌面终端、以普通用户身份安装，**不要使用 `sudo`**。

## 安装

### 推荐：通过 Omarchy 插件管理器

```bash
omarchy plugin add https://github.com/CoderLambert/omarchy-workspace-plugin.git --enable
bash ~/.config/omarchy/plugins/lambert.workspaces/install.sh --backend-only
~/.local/bin/omarchy-workspaces gui
```

第一条安装并启用原生面板；第二条安装 Python 后端及系统菜单入口，因为 **Omarchy 插件管理器不会自动执行本项目的后端安装器**；第三条打开配置面板。

如果已经安装过插件，请不要重复执行 `plugin add`，直接查看下方[升级](#升级)。

### 其他方式：克隆或下载源码

```bash
git clone https://github.com/CoderLambert/omarchy-workspace-plugin.git
cd omarchy-workspace-plugin
bash install.sh
~/.local/bin/omarchy-workspaces gui
```

也可以在 GitHub 点击 **Code → Download ZIP**，解压后进入包含 `manifest.json` 的目录运行 `bash install.sh`。这是用户级安装，**不需要作者的个人 dotfiles**。

### 新版工作区管理界面

当前 `main` 已包含新版：按工作区查看应用、点击应用编辑、区分 **“保存”** 与 **“保存并移动”**。详细设计及验证范围见[界面简化说明](docs/UI-SIMPLIFICATION.md)。已安装的用户按下方[升级](#升级)步骤同步界面和后端即可。

## 首次配置

打开面板本身不会接管任何应用。可以只添加一个应用，也可以明确选择推荐的工作区方案。

### 推荐工作区分配

| 工作区 | 示例应用 |
| --- | --- |
| **1 · AI** | ChatGPT App、ChatGPT 网页应用、Grok Bot |
| **2 · 开发** | 终端、tmux、VS Code |
| **3 · 浏览器** | 常用浏览器 |
| **4 · 通信** | WeChat、Slack、X、Discord |

这些只是**可修改的示例分配**，不会强制重命名或固定 Hyprland 工作区。建议先打开常用应用，再从面板选择推荐设置，或运行：

```bash
omarchy-workspaces setup
```

**注意：**`setup` 会识别受支持的应用、应用受管启动规则，并可能**整理已经登记的窗口**。在有正在进行的任务时请先确认影响。默认**不覆盖系统快捷键**；身份不明确的应用会跳过，而不是猜测窗口归属。

### 单独配置应用

先正常打开应用，再使用面板里的“添加应用”（当前会打开终端向导），或执行：

```bash
omarchy-workspaces add Obsidian --workspace 2
omarchy-workspaces list
```

在面板中选择应用、设置工作区和再次打开策略。新版界面默认的 **“保存”只修改配置，不移动已有窗口**；只有明确勾选立即移动，才使用“保存并移动”。

### 再次打开已有窗口时如何处理

假设 Slack 的默认工作区是 **4**，但你手动把窗口移到了 **5**：

| 模式 | 从受管入口再次打开 Slack |
| --- | --- |
| `focus`（默认） | 直接切换到 **5** 的现有窗口，不改变其位置。 |
| `move` | 将现有窗口移回 **4**，然后切换并聚焦。 |

```bash
omarchy-workspaces set slack --workspace 4
omarchy-workspaces set slack --existing-window focus
omarchy-workspaces arrange --dry-run
omarchy-workspaces arrange --app slack
```

`slack` 只是示例 ID，请用 `omarchy-workspaces list` 查阅真实 ID。`arrange --dry-run` 只预览移动计划。整理默认跳过 scratchpad 和其他特殊工作区，只有显式授权才会包含它们。

### 可选快捷键与临时工作区

```bash
omarchy-workspaces setup --with-shortcuts
```

快捷键接管是**可选操作**。若检测到冲突，会先显示原命令与拟替换命令，并要求对每一个冲突分别确认；不授权则保留 Omarchy 原有绑定。

使用 scratchpad 时，先按 `Super+S` 显示临时工作区，再从受管入口启动应用；该窗口可以留在 scratchpad，继续通过原生 `Super+S` 显示或隐藏。

## 升级

如果使用 Git 方式安装，先通过 Omarchy 更新插件，**再同步 Python 后端**：

```bash
omarchy plugin update lambert.workspaces
bash ~/.config/omarchy/plugins/lambert.workspaces/install.sh --backend-only
omarchy restart shell
```

如果正在试用预览分支，正常执行插件更新可能改变所处的提交，请先确认目标分支。源码 / ZIP 安装则下载新版后运行 `bash install.sh --no-setup`。

`apps.toml` 中已经登记的应用和分配会保留。无需为了更新 UI 删除配置或先卸载。

## 排错与恢复

```bash
omarchy-workspaces --version
omarchy-workspaces doctor           # 检查配置、受管文件和规则
hyprctl configerrors                # 检查 Hyprland 配置错误
omarchy-workspaces recover          # 恢复中断的配置事务
omarchy-workspaces reset            # 撤销受管规则，但保留应用分配
omarchy-workspaces apply            # 重新应用已保存的分配
```

如果 `doctor` 报告受管 `.desktop` 被其他工具修改，请先检查差异，再决定是否执行 `apply --adopt`。它会更新恢复基线，**不是通用的忽略错误开关**。

只禁用或移除原生面板，并不会自动撤销此前接管的快捷键、应用入口和窗口规则；需要停止管理时应先执行 `reset`。`reset` 不会关闭程序或自动把已打开窗口移回原处。

| 数据 | 默认位置 |
| --- | --- |
| 原生插件 | `~/.config/omarchy/plugins/lambert.workspaces/` |
| 应用分配 | `~/.config/omarchy-workspaces/apps.toml` |
| 面板语言 | `~/.config/omarchy-workspaces/ui.ini` |
| Python 后端 | `~/.local/share/omarchy-workspaces/` |
| 恢复状态和日志 | `~/.local/state/omarchy-workspaces/` |

## 功能边界

窗口复用仅针对**受管启动入口**，不会拦截所有启动应用的方式；多个已有窗口不会自动合并或关闭。普通浏览器标签页不能作为独立 Hyprland 窗口分配工作区；网页应用 / PWA 必须具备可信、独立的窗口身份。第三方应用和多显示器等未覆盖组合仍建议根据环境验证；新版界面已完成用户真实桌面验收。

## 相关文档

- [安装、升级和卸载](docs/INSTALL.md) · [面板、命令行和配置](docs/USAGE.md) · [常见问题](docs/TROUBLESHOOTING.md)
- [UI 重设计与测试](docs/UI-SIMPLIFICATION.md)
- [发布验收清单](docs/RELEASE-CHECKLIST.md) · [变更记录](CHANGELOG.md)

**许可证：**[GPL-3.0-only](LICENSE)。`reference/` 中引用的 Omarchy 代码保留原始许可证，详见[第三方来源说明](reference/SOURCES.md)。
