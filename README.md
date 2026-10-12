# Omarchy Workspaces · 1.3.0-rc.1

**公开 Beta / RC1：尚未发布稳定版。** 当前优先验证可靠性，真实桌面验收未全部完成；升级后请同步后端。

把常用应用放到固定工作区，再次打开时直接回到已有窗口；需要临时处理任务时，也能留在 `Super+S` 的 scratchpad 中。

Omarchy Workspaces 是 Omarchy 的原生「工作区管理」插件（`lambert.workspaces`）。它将应用分配、窗口复用、快捷键和规则恢复集中到一个面板，适合同时使用 AI 工具、编辑器、浏览器和通信应用的人。

## 它解决什么问题

| 常见困扰 | 插件的处理方式 |
| --- | --- |
| 应用散落在多个工作区，找窗口靠逐个切换 | 为每个应用设置默认工作区；再次打开受管入口时聚焦已有窗口 |
| 快捷键反复打开同一应用，产生多个窗口 | 有匹配窗口时复用；没有时才调用原启动入口，并对重复启动加锁 |
| 手动把窗口移走后，希望保留位置或自动归位 | 可选“跳到已有窗口”或“先归位，再聚焦” |
| 在 scratchpad 打开应用，却被固定规则送到普通工作区 | scratchpad 可见时启动的应用留在其中，继续用 `Super+S` 显示 / 隐藏 |
| 手写窗口规则和快捷键容易冲突，也难撤回 | 图形配置、检查、变更恢复与撤销入口；检测外部改动后提示处理 |
| 插件颜色固定，切换主题后风格不一致 | 跟随 Omarchy 的颜色、字体、字号、圆角和边框；支持中文 / English |

## 功能一览

- **按应用管理工作区**：搜索已登记应用，设置 `1–999` 工作区，查看窗口数量和当前位置。
- **复用与整理**：聚焦 / 启动应用、保存并整理单个应用、整理全部、取消管理；默认保留 `special:*`，明确勾选后才迁移。
- **快速配置**：自动预设识别常见应用；也可从已打开的应用登记，自定义程序和 PWA 通过高级配置确认身份。
- **scratchpad 支持**：显示临时工作区时打开的应用留在临时工作区；普通启动仍按默认分配。普通入口再次使用隐藏 scratchpad 中的同一应用时，可归回默认工作区。
- **原生主题与双语面板**：右上角 `中文 / English` 立即切换并记住选择；宽屏双栏、窄屏纵向滚动；支持搜索、方向键、Tab 和 Esc。
- **可检查、可恢复**：提供 `doctor`、`recover`、`reset` 和 `apply`，保留规则变更前的恢复信息。

Python 后端只在操作时运行，不新增独立常驻服务。安装不会自动识别应用或整理现有窗口；首次分配由你显式执行。

## 快速安装：只安装这个插件

适用于 **Omarchy 4.0.4 / Hyprland Lua**，需要 Python 3.11+ 和运行中的 Omarchy Shell / Quickshell。后端使用 `hyprctl`、`gtk-launch`、`omarchy-launch-tui`；tmux 功能另需 `tmux`。

源码仓库：[`CoderLambert/omarchy-workspace-plugin`](https://github.com/CoderLambert/omarchy-workspace-plugin)。

推荐在自己的 Omarchy 桌面终端通过原生插件管理器安装：

```bash
omarchy plugin add https://github.com/CoderLambert/omarchy-workspace-plugin.git --enable
bash ~/.config/omarchy/plugins/lambert.workspaces/install.sh --backend-only
~/.local/bin/omarchy-workspaces gui
```

第一条安装并启用面板，第二条安装后端和系统菜单。Omarchy 插件管理器
只克隆插件，不自动执行后端安装。也可首次打开面板时按提示安装组件。
这是用户级安装，直接运行即可，不需要 `sudo`。

也可克隆源码到一个尚不存在的下载目录，或在 GitHub 选择 **Code → Download ZIP**
后，在包含 manifest.json 的目录执行安装器：

```bash
git clone https://github.com/CoderLambert/omarchy-workspace-plugin.git ~/Downloads/omarchy-workspace-plugin
cd ~/Downloads/omarchy-workspace-plugin
bash install.sh
~/.local/bin/omarchy-workspaces gui
```

仅安装这个插件，不需要安装作者的个人 dotfiles。仓库提供
`install-omarchy-workspaces.sh` 单文件离线安装器，尚未发布独立 GitHub Release
附件或插件市场条目；完整安装方式见 [安装说明](docs/INSTALL.md)。

**前后端一致性：**面板比较版本与后端 Python 源码指纹；即使版本字符串相同、代码不同也会阻止修改。点击“更新组件”会同步后端并保留应用分配。

**快捷键：**自动预设默认不添加插件快捷键，保留 Omarchy 的系统绑定。工作区分配和受管菜单的窗口复用仍可使用。需要用快捷键打开或复用应用时，运行 `omarchy-workspaces setup --with-shortcuts`；每个冲突都会展示原绑定与新命令，明确输入 `yes` 才接管，默认跳过。已有个人快捷键设置继续保留。

**首次使用：**打开 **Omarchy 系统菜单 → 工作区配置**，点“自动预设…”；或先打开某个应用，用“添加应用…”单独登记。自动预设会补齐可识别的应用并整理已登记窗口，部分应用可能通过探测启动确认身份，身份不确定的应用会跳过。

默认预设可自行修改：

| 工作区 | 预设用途 |
| --- | --- |
| 1 | AI：ChatGPT App / 网页、Grok Bot |
| 2 | 开发：终端、tmux、VS Code |
| 3 | 普通浏览器 |
| 4 | 通信：WeChat、Slack、X、Discord |

## 五分钟上手

1. 在菜单打开“工作区配置”，点“添加应用…”；先打开目标应用，便于识别它的窗口身份。
2. 选择左侧应用，设置默认工作区和再次打开时的复用方式。
3. 点“保存并整理此应用”。该操作同时保存设置，并移动这个应用的现有窗口。
4. 从其他工作区再次使用受管菜单或快捷键打开应用，检查是否回到已有窗口。
5. 点右上角 `中文 / English` 选择语言；以后重新打开面板仍保留。

例如 Slack 默认工作区为 4，你把它手动移到 5：

| 选择 | 再次打开时 |
| --- | --- |
| 跳到已有窗口（`focus`，默认） | 切到 5，保留窗口当前位置 |
| 先归位，再聚焦（`move`） | 把窗口移回 4，再切换并聚焦 |

“整理全部”和“保存并整理此应用”默认跳过 scratchpad 与其他 `special:*` 工作区。确需迁移它们时勾选“整理时包含临时工作区”，或执行 `omarchy-workspaces arrange --include-special`；可先加 `--dry-run` 查看计划。

临时工作区的用法：按 `Super+S` 显示 scratchpad，再启动受管应用；应用留在 scratchpad。再按 `Super+S` 可隐藏或显示。插件保留 Omarchy 原有的 scratchpad 快捷键。

“自动预设…”先显示准备与行为说明，再在面板内执行；完成后显示识别结果并自动刷新应用列表，失败时保留错误提示。“添加应用…”和“高级设置…”仍打开终端；完成后回面板刷新。语言切换覆盖面板与常见操作结果，终端 CLI 及未识别的原始诊断仍保留程序输出语言。

## 常用命令

```bash
omarchy-workspaces gui                         # 打开面板
omarchy-workspaces setup                       # 识别应用并整理，不添加预设快捷键
omarchy-workspaces add Obsidian --workspace 2 # 登记一个已经打开的应用
omarchy-workspaces list                        # 查看本机应用 ID
omarchy-workspaces doctor                      # 检查配置和规则
```

下面的 `slack` 是示例 ID，应替换为 `list` 显示的实际 ID：

```bash
omarchy-workspaces launch slack
omarchy-workspaces set slack --workspace 5
omarchy-workspaces arrange --app slack
omarchy-workspaces arrange --dry-run
```

CLI `set --workspace` 只修改分配，现有窗口保持原位；面板“保存并整理此应用”会立即移动现有窗口。

## 更新、配置与撤销

Git 插件用户通过 Omarchy 原生更新，审阅差异后更新插件；然后执行：

```bash
bash ~/.config/omarchy/plugins/lambert.workspaces/install.sh --backend-only
```

这会同步 Python 后端而保留 Git 插件目录和应用分配。ZIP / 克隆安装用户取得新版源码后再次执行 `bash install.sh --no-setup`。

| 内容 | 默认位置 |
| --- | --- |
| 插件面板与源码 | `~/.config/omarchy/plugins/lambert.workspaces/` |
| 应用分配 | `~/.config/omarchy-workspaces/apps.toml` |
| 面板语言选择 | `~/.config/omarchy-workspaces/ui.ini`，`[ui] language=zh` 或 `en` |
| 后端 | `~/.local/share/omarchy-workspaces/` |
| 规则恢复记录及日志 | `~/.local/state/omarchy-workspaces/` |

应用分配和语言配置遵循 `XDG_CONFIG_HOME`；后端及状态遵循各自的 XDG 路径。原生插件和 Omarchy 菜单使用官方固定的 `~/.config/omarchy` 路径。

```bash
omarchy-workspaces recover   # 处理被中断的配置事务
omarchy-workspaces reset     # 撤销工作区规则和入口接管，保留程序与分配
omarchy-workspaces apply     # 重新应用已保存的分配
```

单独禁用 / 移除 Omarchy 插件只影响界面，不恢复本工具的应用规则。需要撤销规则时先执行 `reset`；独立安装的完整卸载使用 `omarchy-workspaces uninstall`。这些操作不关闭应用，也不会把已移动的窗口搬回原位置。发现外部修改时先查看 `doctor`，确认后再决定是否使用 `apply --adopt`。

## 适用范围

窗口复用针对受管菜单、启动器和快捷键；其他程序直接运行原应用命令时，行为由应用自身决定。普通浏览器标签页不能独立分配工作区；PWA 必须有可信的独立窗口身份。多个窗口不会自动合并或关闭。

这次更新已在本机 Omarchy 桌面加载，主题和双语 UI 有隔离测试。其他实体机器、所有第三方应用、所有主题和多显示器组合尚未全部实测；详见仓库 [本次交付验证记录](docs/变更记录/2026-10-12-theme-language-scratchpad.md)。

## English quick start

Omarchy Workspaces assigns apps to default workspaces, reuses existing windows, and respects the `Super+S` scratchpad. The native panel follows your Omarchy theme and offers persistent Chinese / English settings.

On Omarchy 4.0.4 with Python 3.11+, install from `https://github.com/CoderLambert/omarchy-workspace-plugin.git` with the Omarchy plugin manager, then run `bash ~/.config/omarchy/plugins/lambert.workspaces/install.sh --backend-only`. Alternatively, clone this repository and run `bash install.sh` from its root. Then open **Omarchy menu → 工作区配置**, or run `~/.local/bin/omarchy-workspaces gui`. Installation preserves app assignments; choose **Auto setup…** or **Add app…** to configure them. Switch to English using the button at the top right.

Choose **Focus existing window** to keep its current position, or **Move, then focus** to return it to the assigned workspace. **Save and arrange app** immediately moves that app’s existing windows. Use `reset` to remove routing rules while keeping assignments, and `apply` to restore them. Terminal commands and raw diagnostics retain their original language.

## 进一步阅读

- [安装、升级与卸载](docs/INSTALL.md)
- [面板、CLI 与配置文件](docs/USAGE.md)
- [重复启动、外部修改、PWA 与恢复](docs/TROUBLESHOOTING.md)
- [独立插件发布](docs/PUBLISHING.md)
- [实现说明](IMPLEMENTATION.md)
- [更新记录](CHANGELOG.md)

开发验证：`python3 scripts/verify_qml.py`（需 Qt 6 QtTest），后端测试见项目测试目录。

## 兼容性与发布状态

| 项目 | 当前要求 / 验证范围 |
| --- | --- |
| 桌面 | 主要测试目标为 Omarchy 4.0.4；原生面板依赖该版本的 qs.Commons / qs.Ui |
| Hyprland | 主要目标为 Lua API 的 0.55+；旧后端仍保留，但未完成真实桌面兼容验收 |
| Python | 后端最低 3.11；CI 测试 3.11 / 3.13 |
| Qt | 面板的 QtCore.Settings 需要 Qt 6.5+，推荐 Omarchy 自带的 Quickshell |
| 本版 | 1.3.0-rc.1，公开 Beta 候选；不是稳定版 |

PR / main 的 CI 自动测试、验证离线包并保存 UI 报告及构建产物。是否发布稳定版以
[真实桌面验收清单](docs/RELEASE-CHECKLIST.md)为准，尤其需要复测 Grok Bot 的重复启动和 desktop 外部修改。未创建 Stable Release，也没有把适配器结果记成真实桌面验收。

## 许可证

原创代码与文档采用 [GPL-3.0-only](LICENSE)。`reference/` 中引用的 Omarchy 代码继续使用其原许可证，来源及第三方许可见 [reference/SOURCES.md](reference/SOURCES.md) 和 [reference/omarchy-LICENSE](reference/omarchy-LICENSE)。
