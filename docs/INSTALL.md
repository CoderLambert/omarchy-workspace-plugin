# 安装、升级与卸载

适用于 Omarchy Workspaces 1.2.0，主目标为 Omarchy 4.0.4。

## 1. 安装前提

在实际登录 Omarchy / Hyprland 的用户终端执行，**不使用 `sudo bash install.sh`**。这是用户级安装；以 root 运行会写进 root 家目录，也不代表你的桌面会话。

| 功能 | 所需组件 |
| --- | --- |
| 后端 | Python 3.11+、`hyprctl`、`gtk-launch`、`omarchy-launch-tui` |
| 原生面板 | Omarchy Shell/Quickshell，以及插件验证、发现、启用命令 |
| tmux 预设 | `tmux` |
| 命令行解压 | `unzip`，也可用文件管理器 |

安装器检查必要依赖，不下载系统包。缺少 `gtk-launch` 时按提示安装 `gtk3`；缺少 Omarchy 专用命令时先确认当前是目标桌面环境。

## 2. 安装完整插件包

```bash
unzip ~/Downloads/omarchy-workspaces-plugin-1.2.0.zip -d ~/Downloads/omarchy-workspaces-1.2.0
cd ~/Downloads/omarchy-workspaces-1.2.0/omarchy-workspaces
bash install.sh
```

若用文件管理器解压，进入包含 `manifest.json`、`Panel.qml`、`install.sh` 的 `omarchy-workspaces` 目录，执行最后一条命令。

默认安装会：

1. 安装或升级 Python 后端与 `~/.local/bin/omarchy-workspaces`。
2. 安装 `lambert.workspaces` 面板，尝试重新发现、启用插件。
3. 注册系统菜单及应用启动器中的“工作区配置”。
4. 保留已有 `apps.toml`、规则、窗口位置和恢复记录。

默认不会扫描应用、重新应用分配或自动 `--adopt`。已有规则继续生效；全新安装需要下一节的首次配置。缺少原生插件所需命令时，安装器说明原因并回退到终端入口；在完整 Omarchy Shell 环境重复安装即可补装。

打开 **Omarchy 系统菜单 → 工作区配置**，或运行：

```bash
~/.local/bin/omarchy-workspaces gui
```

面板不可用时自动回退终端。显式使用终端配置：

```bash
~/.local/bin/omarchy-workspaces config
```

## 3. 首次登记应用

使用默认 `1 AI / 2 开发 / 3 浏览器 / 4 通信` 分配：

```bash
~/.local/bin/omarchy-workspaces setup
```

建议先打开常用应用。它保留已有登记，补齐可识别的预设，并整理当前已登记窗口；部分应用可能通过探测启动确认身份，不能确定的会跳过并报告。想安装后立即执行，可用 `bash install.sh --setup`。

只登记一个应用，先打开它，再执行：

```bash
~/.local/bin/omarchy-workspaces add Obsidian --workspace 2
```

唯一入口和身份直接登记，不唯一才询问；身份未确认不提交，不为识别再次启动应用。新增成功只整理该应用。

## 4. 从 1.1.3 升级

在新版解压目录执行：

```bash
bash install.sh --no-setup
~/.local/bin/omarchy-workspaces --version
```

预期显示 `1.2.0`。无需先卸载，不要删除 `apps.toml`、状态目录或恢复记录。旧分配继续使用，原“工作区配置”改为优先打开面板。

以后升级仍重复运行新版安装器。`--no-setup` 是兼容参数，与 1.2.0 默认行为一致；旧版无参数会扫描，新版已经改为显式 `--setup`。

若存在中断的配置事务，也可先补装/更新后端；安装器原样保留 `pending.json` 和配置现场。安装后先执行 `omarchy-workspaces recover`，再继续修改分配。

升级代码不会接纳原 `.desktop` 被第三方修改的内容。遇到漂移报告，按[故障排查](TROUBLESHOOTING.md#受管文件被其他工具修改)核对后再决定是否 `apply --adopt`。

## 5. 安装参数

```bash
bash install.sh --help
```

| 参数 | 行为 |
| --- | --- |
| 无参数 | 安装后端、插件和菜单；保留分配与生效规则 |
| `--no-setup` | 与默认行为相同，兼容旧版升级命令 |
| `--setup` | 安装后自动识别预设并整理已登记窗口 |
| `--cli-only` | 安装后端和菜单，不安装原生面板；已有插件不会因此被删除 |
| `--backend-only` | 补装后端及菜单，不复制插件目录、不启用插件、不改写 Shell 配置 |
| `--help` | 显示参数说明 |

`--backend-only` 供原生插件管理器克隆后的首次引导使用，不是禁用或卸载命令。

## 6. 单文件离线安装

`install-omarchy-workspaces.sh` 内含源码、文档和测试，安装时无需下载本工具：

```bash
bash ~/Downloads/install-omarchy-workspaces.sh
```

支持相同安装参数，例如 `--no-setup`。只提取源码、不安装：

```bash
bash ~/Downloads/install-omarchy-workspaces.sh --extract ~/Downloads/omarchy-workspaces-source-1.2.0
```

目标目录必须尚不存在。提取目录本身就是源码根目录，包含 `install.sh`，不用再进入同名子目录。安装器会验证内置载荷的 SHA-256。完整 ZIP 内文件可在解压项目根目录检查：

```bash
sha256sum -c SHA256SUMS
```

## 7. 从 GitHub 安装原生插件

本项目的公开仓库是 [`CoderLambert/omarchy-workspace-plugin`](https://github.com/CoderLambert/omarchy-workspace-plugin)。在 Omarchy 桌面终端执行：

```bash
omarchy plugin add https://github.com/CoderLambert/omarchy-workspace-plugin.git --enable
```

官方命令将仓库克隆到 `~/.config/omarchy/plugins/lambert.workspaces/`，验证并启用插件，**不会执行 `install.sh`**。因此还需安装 Python 后端和菜单入口：

```bash
bash ~/.config/omarchy/plugins/lambert.workspaces/install.sh --backend-only
```

之后打开 **Omarchy 系统菜单 → 工作区配置**，或运行：

```bash
~/.local/bin/omarchy-workspaces gui
```

GitHub 仓库的 **Code → Download ZIP** 也可用于本地安装；解压后在仓库根目录运行 `bash install.sh`。发布与更新说明见 [PUBLISHING.md](PUBLISHING.md)。

## 8. 安装与配置位置

| 内容 | 默认位置 |
| --- | --- |
| 原生插件 | `~/.config/omarchy/plugins/lambert.workspaces/` |
| CLI | `~/.local/bin/omarchy-workspaces` |
| Python 后端及安装记录 | `~/.local/share/omarchy-workspaces/` |
| 应用分配 | `~/.config/omarchy-workspaces/apps.toml` |
| 生效规则恢复记录及日志 | `~/.local/state/omarchy-workspaces/` |
| 系统菜单扩展 | `~/.config/omarchy/extensions/omarchy-menu.jsonc` |
| 配置及应用代理入口 | `~/.local/share/applications/ows-*.desktop` |

**Omarchy 原生插件目录和系统菜单扩展均使用固定的 `$HOME/.config/omarchy`，不跟随 `XDG_CONFIG_HOME`。** 插件位于其 `plugins/lambert.workspaces/`，菜单为 `extensions/omarchy-menu.jsonc`，与 Omarchy 4.0.4 实际读取路径一致。后端应用配置、数据和状态分别遵循 `XDG_CONFIG_HOME`、`XDG_DATA_HOME`、`XDG_STATE_HOME`。CLI 固定在 `$HOME/.local/bin`。

旧版若曾把受管菜单写到自定义 XDG 目录，升级会将本工具的菜单登记迁移到官方路径，保留新旧文件中的用户菜单项。无需手动复制或覆盖整份 JSONC。

桌面菜单与终端需使用一致的 XDG 环境；只在交互 shell 临时设置 XDG，可能让面板与终端读到不同配置。用 `doctor` 显示的实际路径核对。

## 9. 撤销、禁用和卸载

| 目的 | 操作 | 结果 |
| --- | --- | --- |
| 暂停所有工作区及入口接管 | `omarchy-workspaces reset` | 恢复原规则、入口、绑定，保留程序、面板、菜单及分配表 |
| 恢复已保存分配 | `omarchy-workspaces apply` | 重新应用 `apps.toml` |
| 只禁用面板 | `omarchy plugin disable lambert.workspaces` | 只关闭图形插件，规则及后端保留 |
| 重新启用面板 | `omarchy plugin enable lambert.workspaces` | 恢复图形插件 |
| 卸载本工具 | `omarchy-workspaces uninstall` | 先恢复规则，再移除受管命令、菜单和可移除的插件副本，保留应用配置、后端副本及日志 |

`reset`、`uninstall` 不会回移已整理或手动移动的窗口。有外部修改或待恢复事务时，先按报告处理；不能把部分步骤完成视为完整卸载。

插件目录只有在由本安装器创建且内容未被修改时才直接删除。Git 管理、手工安装或含本地修改的目录会保留；先核对输出，再按提示执行 `omarchy plugin remove lambert.workspaces`。应用规则此时已由前面的 `uninstall` 恢复。后端副本保留在数据目录供诊断、重装，不再保留命令与菜单入口。

官方 `omarchy plugin remove lambert.workspaces` 不调用本工具的恢复逻辑。计划用它移除面板时，先执行 `omarchy-workspaces reset`。一次性撤销接管并卸载，使用本工具的 `uninstall`。

## 10. 安装后验收

1. `omarchy-workspaces --version` 显示 `1.2.0`。
2. 系统菜单只有一个“工作区配置”，能打开面板并显示原登记。
3. 选一个已登记应用，从其他工作区再次打开，聚焦原窗口。
4. 完全关闭它的窗口，连续点击受管入口，检查没有重复拉起。
5. 手动移开窗口，验证 `focus` 保留位置；单应用“整理”只移动它。
6. 运行 `omarchy-workspaces doctor`，检查报告及 `hyprctl configerrors`。

本机结果代表真实窗口身份和桌面行为；测试桩不能替代这些检查。
