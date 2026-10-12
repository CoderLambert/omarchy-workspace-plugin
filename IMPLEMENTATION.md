# 实现说明 · 1.2.0

## 目标与边界

本工具在现有工作区管理后端上增加 Omarchy 原生 `panel` 插件。应用登记、窗口复用和事务恢复继续由 Python 3.11+ 标准库后端处理，图形面板负责交互与展示。

主目标为 Omarchy 4.0.4 / Hyprland Lua。旧版 Hyprland 有 conf/v2 规则生成兼容代码，但原生面板依赖 Omarchy Shell 的插件 API。无兼容 Shell 时保留终端配置，不宣称旧桌面具有同样图形支持。

源码包来自本次实现，不是用户桌面的配置导出。`examples/` 中 desktop ID 和身份只是结构示例；实际值由目标机器登记。

## 原生插件结构

根目录 `manifest.json` 的稳定 ID 是 `lambert.workspaces`，类型为 `panel`，入口是 `Panel.qml`。这一层就是可以直接发布的 Git 仓库根目录。

Omarchy Shell 加载 QML 并注入插件上下文，面板通过 `open(payloadJson)` / `close()` 生命周期展示或隐藏。CLI `gui` 通过 Shell IPC 召唤插件；菜单和配置 desktop 默认进入 `gui`，面板不可用时回退终端。

面板读取已登记应用与窗口状态，支持工作区、复用策略、单应用整理、启动、取消管理、检查和恢复。Python 进程按操作启动，结果通过结构化输出回到面板；不引入 Web 服务，也不为窗口复用添加轮询守护进程。交互式新增、预设识别和高级向导在终端运行，回到面板再刷新。

`keepLoaded` 只影响面板对象在 Omarchy Shell 中的生命周期，不能理解为后台持续扫描。隐藏面板不需要持续运行 Python。

## 关键文件与模块

| 文件 | 职责 |
| --- | --- |
| `manifest.json`、`Panel.qml` | 原生插件声明、面板及 Shell 生命周期 |
| `src/omarchy_workspaces/core.py` | XDG 路径、TOML 校验、精确身份、原子写入、文件锁 |
| `discover.py` | 预设应用、PWA、浏览器与终端的发现 |
| `registration.py` | 任意名称、原 desktop、可执行命令与可信窗口的关联 |
| `desktop.py` | 原入口读取、代理生成、保留动作与关联、委托启动 |
| `hypr.py` | IPC、规则和快捷键生成、移动、聚焦、重载 |
| `manager.py` | 应用事务、备份、漂移检测、回滚、启动锁和复用 |
| `tmux.py` | 将 tmux 客户端进程关联到已有独立终端 |
| `menu.py` | Omarchy JSONC 根菜单登记、旧 XDG 路径迁移、修复与恢复 |
| `cli.py` | CLI、终端菜单、预设与高级向导、GUI 入口 |
| `gui.py`、`scripts/bridge.py` | 单次 JSON 请求/响应桥接、状态快照、修改前版本核对 |
| `plugin.py` | 原生插件发现/启用/召唤、终端回退和插件副本移除 |
| `installer.py`、`scripts/install.py` | 安装计划、受管文件验证、暂存替换与失败回滚 |
| `install.sh` | 用户级安装、升级、原生插件接入和降级模式 |
| `build_release.py`、`build_source.py` | 单文件离线安装器、完整 ZIP 与校验清单 |
| `tests/` | 后端、菜单、安装及插件相关回归验证 |
| `reference/` | 核对过的 Omarchy 源码、来源与许可证，非运行依赖 |

## 安装位置与记录

| 位置，按默认环境 | 用途 |
| --- | --- |
| `~/.config/omarchy/plugins/lambert.workspaces/` | 原生插件源码 |
| `~/.local/bin/omarchy-workspaces` | 受管命令入口 |
| `~/.local/share/omarchy-workspaces/` | 已安装 Python 模块及 `installation.json` 安装记录 |
| `~/.local/share/applications/ows-config.desktop` | 配置应用入口 |
| `~/.config/omarchy/extensions/omarchy-menu.jsonc` | 带受管标记的系统菜单项 |
| `~/.config/omarchy-workspaces/apps.toml` | 应用分配配置 |
| `~/.config/hypr/app-workspaces.lua` | 生成的 Lua 规则，旧后端使用 `.conf` |
| Hyprland 主入口 | 只在 begin/end 标记内增加规则加载语句 |
| `~/.local/share/applications/ows-应用ID.desktop` | 受管应用代理 |
| 原 desktop 的用户级同名路径 | 加入 NoDisplay 的覆盖副本，保留原启动信息 |
| `~/.local/state/omarchy-workspaces/manifest.json` | 规则/desktop 恢复基线、校验值及最后成功配置 |
| 同目录 `pending.json` | 未完成事务恢复记录，成功后删除 |
| 同目录 `menu-registration.json` | 独立菜单恢复记录 |
| 同目录 `launch.log` | 原入口启动输出 |
| `$XDG_RUNTIME_DIR/omarchy-workspaces-locks/` | 启动锁和短期标记；无 runtime dir 时用状态目录 |

插件目录固定使用 `$HOME/.config/omarchy/plugins`，系统菜单固定使用 `$HOME/.config/omarchy/extensions/omarchy-menu.jsonc`，与 Omarchy 4.0.4 官方脚本及 `Menu.qml` 一致，均不遵循 `XDG_CONFIG_HOME`。后端应用配置、数据、状态继续尊重对应 XDG 变量；CLI 固定在 `$HOME/.local/bin`。

菜单升级将旧版自定义 XDG 路径中的受管登记迁移到官方固定路径，只处理本工具的受管块，保留新旧文件中的用户项。菜单恢复记录仍位于本工具的 XDG 状态目录。

安装记录、菜单恢复记录、规则应用事务分别管理各自文件。安装器在安装事务锁与规则事务锁内更新后端，随后自动刷新上一次已启用的规则。刷新不会应用或改写 TOML 草稿，不移动窗口，不自动接纳外部修改。规则刷新失败时保留已更新的后端供恢复，CLI 非零退出、GUI 报告部分完成。停用状态和中断事务现场保留。

## 安装与原生管理器的分工

| 入口 | 行为 |
| --- | --- |
| `bash install.sh` | 安装后端、面板和菜单，不扫描、不 apply |
| `--setup` | 安装后显式预设发现、应用和整理 |
| `--no-setup` | 默认行为的兼容别名 |
| `--cli-only` | 后端与菜单，不复制安装面板 |
| `--backend-only` | 补装后端与菜单，不复制现有插件，不启用、不改 Shell 配置 |
| 原生 `plugin add` | 克隆、验证、可选启用，不执行 `install.sh` |

因此原生 Git 安装后面板可以引导安装后端。官方 `plugin disable/remove` 没有本工具的卸载钩子；生命周期与规则恢复必须在用户指南中分别说明。

## 登记和默认工作区

普通 `add NAME` 使用入口名称、desktop ID、StartupWMClass、当前 initialClass/class、PWA app ID 等证据关联。不从动态聊天标题推断独立应用，没有可信身份就要求先打开目标窗口。普通新增不通过探测启动再开实例；预设 `setup` 的发现流程可显式探测部分应用。

`.desktop` 按 XDG 应用目录读取，不依赖 Flatpak，也不扫描包管理器缓存。命令型应用使用 argv 数组，不拼接 shell。`gtk-launch` 负责解析原 desktop 的启动行为。

`Manager.apply()` 校验配置，识别 Hyprland 规则后端，为精确身份生成目标工作区规则。特殊正则字符会转义。主目标的 Lua 示例：

```lua
hl.window_rule({
  name = "ows-slack-0",
  match = { initial_class = "^Slack$", workspace = "s[false]" },
  workspace = "4",
  focus_on_activate = true
})
```

CLI `set` 更新默认位置；`arrange --app APP` 只移动一个已登记应用，`arrange` 整理全部。默认复用采用 `focus` 保留手动移动的位置，`move` 表示复用时归位。

面板“保存并整理此应用”在配置事务成功后整理该应用，其他手动移动的窗口不受影响。GUI 写操作带状态版本，状态过期时要求刷新；未应用草稿先处理后再编辑应用，避免旧面板覆盖外部修改。

## 窗口复用与防重复启动

受管代理调用 `omarchy-workspaces launch APP`。原 desktop 用户级副本增加 `NoDisplay=true`，代理显示在菜单中；原 Exec、D-Bus、MIME 和 desktop action 保留，代理不声明 MIME 关联。

运行时读取最后成功应用的配置，先按 Hyprland 实例与应用 ID 加锁，再查询窗口。命中时选 focusHistoryID 最近的窗口并聚焦；无匹配窗口时只调用一次原入口，等待新窗口出现后分配、聚焦。启动锁和短期标记避免并发点击重复启动，超时后提示检查并进入短时冷却。

原应用启动委托 `uwsm-app` / `gtk-launch` 或配置 argv。`--new`、文件/URI 透传及原 desktop action 允许原应用处理，不承诺一定新建或一定复用。

现有 1.1.1 修复保留：Lua 解绑覆盖同一物理组合的修饰键顺序和 keysym 大小写，重载后检查默认 submap 的受管绑定数量。Lua IPC 的 `arg` 可为回调编号，不能误当 shell 命令验证。

## tmux 复用

专用入口使用固定 app ID，连接 `tmux new-session -A -s Work`。同时读取 tmux 客户端会话与 PID，沿 `/proc` 父进程定位已打开的独立终端，复用安装前已有窗口。VS Code 内置终端不作为独立终端。工具不关闭既有多余窗口。

## 事务、外部修改和撤销

应用前验证现有配置、受管文件与快捷键冲突，写事务记录后修改文件、重载，再检查配置错误和受管绑定。失败尝试恢复原内容；进程中断可用 `recover`。中断后文件又被修改，恢复拒绝覆盖。

`apply --adopt` 是核对后接纳外部内容为新恢复基线，不是默认升级行为或忽略错误开关。受管文件为符号链接、来源不明或恢复记录缺失时，不应强制覆盖。

对于未漂移、由本工具创建的 NoDisplay 副本，接纳其他外部修改时继续读取最新系统 desktop，不把旧副本当成原入口。草稿已删除应用时，明确 adopt 会保留相关外部更新为非受管文件并解除其登记；没有外部修改的旧受管文件按原恢复记录处理。

| 操作 | 规则/原入口 | 程序、面板与配置 |
| --- | --- | --- |
| `reset` | 撤销接管 | 完整保留 |
| `apply` | 按保存配置重新接管 | 保留 |
| `uninstall` | 先恢复 | 移除受管入口及未修改的安装器插件，保留应用配置、后端副本和日志 |
| 官方 `plugin disable/remove` | 不恢复 | 只处理插件启用或目录 |

撤销不回移窗口；主 Hyprland 入口中用户后来添加的其他设置保留。菜单注册保留原 JSONC 注释与自定义项，修复只处理受管块，无法识别的同名项拒绝覆盖。

插件副本通过 `.ows-install.json` 检查归属和内容。Git 管理、手工安装、含符号链接或本地修改的目录保留并报告，提示后续使用原生管理器处理，不静默删除仓库。

## 验证与发布

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
bash -n install.sh
python3 build_release.py /tmp/install-omarchy-workspaces.sh
python3 build_source.py /tmp/omarchy-workspaces-plugin-1.2.0.zip
```

真实结果、测试数量和限制统一记录在 [TEST-REPORT.md](TEST-REPORT.md)，本文不把隔离 IPC 或 QML 测试替身视为真实桌面验收。安装后用户验收见 [docs/INSTALL.md](docs/INSTALL.md)。

Omarchy 协议依据与发布流程见 [docs/PUBLISHING.md](docs/PUBLISHING.md)。本次没有创建远端仓库或发布插件市场。
