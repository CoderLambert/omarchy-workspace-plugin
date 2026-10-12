# 图形面板与日常使用

## 1. 打开配置

选择 **Omarchy 系统菜单 → 工作区配置**，或执行：

```bash
omarchy-workspaces gui
```

找不到命令时使用完整路径 `~/.local/bin/omarchy-workspaces`。图形插件不可用时回退终端。终端入口始终保留：

```bash
omarchy-workspaces config
omarchy-workspaces config --advanced
```

## 2. 面板操作

面板显示已登记应用及当前窗口情况。搜索只筛选显示，不改变配置。

| 功能 | 结果 |
| --- | --- |
| 修改目标工作区 | 设置 `1–999`，点击“保存并整理此应用”后立即移动该应用的已有窗口 |
| 修改复用方式 | `focus` 聚焦当前位置；`move` 归位后聚焦 |
| 打开应用 | 复用已有窗口，或调用原入口 |
| 保存并整理此应用 | 保存当前工作区及复用设置，只移动该应用的打开窗口 |
| 整理全部 | 将已登记应用的窗口放回分配位置 |
| 取消管理一个应用 | 删除其登记，恢复原入口和相关绑定，不关闭应用 |
| 检查配置 | 展示 `doctor` 报告 |
| 应用配置 | 按分配文件重新生成规则 |
| 接纳外部修改 | `apply --adopt`，使用前核对外部修改 |
| 恢复中断事务 | `recover`，撤回未完成变更 |
| 撤销全部设置 | `reset`，保留完整安装和分配文件 |

“添加应用…”、“自动预设…”和“高级设置…”会打开终端执行；结束后回面板刷新。文件操作运行时先等待结果，再关闭面板或执行下一项；显示成功前不要把修改视为已完成。

面板保存会整理当前应用；若只想修改以后新窗口的位置，使用下面的 CLI `set`。搜索框筛选应用，方向键选择应用，Tab 切换控件，Esc 请求关闭；存在未保存修改时按确认框处理。

## 3. 两种复用策略

假设 Slack 默认在 4，你手动把窗口移到了 5：

| 策略 | 再次点击受管入口 |
| --- | --- |
| `focus`，默认 | 跳到 5，聚焦已有窗口 |
| `move` | 将窗口移回 4，再聚焦 |

新窗口仍按配置进入默认工作区。有多个匹配窗口时选择最近使用的一个，不自动关闭其余窗口。托盘进程不是 Hyprland 窗口；应用仅在托盘时，工具调用原入口，由应用恢复或创建主窗口。

## 4. 新增应用

先正常打开应用，再执行：

```bash
omarchy-workspaces add Obsidian --workspace 2
```

工具查找名称、本地化名称和原 `.desktop`，关联当前窗口。名称不区分大小写，生成小写应用 ID；不唯一才询问。未传 `--workspace` 时询问工作区。身份未确认不提交，不为识别再次启动应用。

没有 desktop 的程序或 AppImage，先打开程序，然后指定可执行文件：

```bash
omarchy-workspaces add MyApp --command ~/Applications/MyApp.AppImage --workspace 2
```

`--command` 接受程序路径；多个参数用高级向导或 TOML 的 argv 数组。手动选择入口、身份、独立 Web App：

```bash
omarchy-workspaces add myapp --advanced
```

搜索列表可直接输入名称，也支持 `/关键词`；`/` 清空搜索，`q` 跳过。

## 5. 预设与快捷键

`setup` 保留已有登记，补齐可识别预设。只有成功登记后才接管相应入口和快捷键。

| 应用 | 工作区 | 预设快捷键 |
| --- | --- | --- |
| ChatGPT App、Grok Bot | 1 | 保留应用入口 |
| ChatGPT 网页 | 1 | `Ctrl + Shift + A` |
| 终端 | 2 | `Super + Return` |
| tmux | 2 | `Super + Alt + Return` |
| VS Code | 2 | `Super + Shift + N` |
| 浏览器 | 3 | `Super + Shift + Return`、`Super + Shift + B` |
| WeChat、Slack、Discord | 4 | 保留应用入口 |
| X | 4 | `Super + Shift + X` |

Grok Bot 不会被替换为 Grok 网站。ChatGPT App 与网页若共享同一窗口身份，应复用同一个登记，或使用具有独立身份的 PWA；不能仅凭不同标题把相同身份分到两个工作区。

## 6. 常用 CLI

`slack` 为示例应用 ID，用 `list` 查看本机实际 ID：

```bash
omarchy-workspaces list
omarchy-workspaces status
omarchy-workspaces status --json
omarchy-workspaces windows
omarchy-workspaces doctor

omarchy-workspaces set slack --workspace 5
omarchy-workspaces set slack --existing-window move
omarchy-workspaces arrange --app slack
omarchy-workspaces arrange --dry-run
omarchy-workspaces arrange

omarchy-workspaces launch slack
omarchy-workspaces launch slack --new
omarchy-workspaces remove slack
```

CLI `set --workspace` 修改默认位置，当前窗口保持原位；立即移动可紧接 `arrange --app slack`。`arrange --dry-run` 只显示计划。

`launch --new` 跳过工具的复用检查；原应用是否真正新建窗口由其自身决定。原 desktop 的“新建窗口”等动作保持原命令。

快捷键设置：

```bash
omarchy-workspaces set slack --shortcut 'SUPER + CTRL + S' --replace-shortcut
omarchy-workspaces set slack --clear-shortcuts
```

`--replace-shortcut` 表示接管已有冲突绑定。重载后检查实际绑定数量，重复或不正确时回滚。不要在其他快捷键工具里再添加相同组合。

同一应用可有 CLI 别名：

```bash
omarchy-workspaces alias chat slack
omarchy-workspaces launch chat
```

## 7. 配置文件

默认 `~/.config/omarchy-workspaces/apps.toml`，遵循 `XDG_CONFIG_HOME`。实际路径见 `doctor`。

```toml
[defaults]
launch_timeout = 20
existing_window = "focus"
backend = "auto"

[aliases]
chat = "slack"

[apps.slack]
name = "Slack"
workspace = 4
desktop = "slack.desktop"
shortcuts = []
replace_shortcuts = false

[[apps.slack.matches]]
initial_class = "Slack"
```

这是结构示例，desktop ID 和窗口身份必须用本机实际值。

| 字段 | 含义 |
| --- | --- |
| `workspace` | `1–999` 的整数 |
| `desktop` | 原 desktop ID，不能引用代理 `ows-*.desktop` |
| `command` | argv 数组，与 `desktop` 只能选一个 |
| `existing_window` | 应用级 `focus` / `move`，省略时使用 defaults |
| `shortcuts` | 受管快捷键列表 |
| `matches` | 候选身份之间为“或”，每个身份内的字段为“且” |
| `launch_timeout` | 等待窗口秒数，范围 `1–120` |
| `hypr_config` | defaults 下可选的 Hyprland 主配置绝对路径 |

身份支持 `class`、`initial_class`、`initial_title` 的精确区分大小写匹配，不能仅用标题登记。工具转义正则字符，不需要填写正则表达式。

手工编辑后执行：

```bash
omarchy-workspaces apply
```

手工 `apply` 保留 TOML 文本；图形/终端菜单和 `set` 会重新序列化受支持字段，可能改变注释与顺序。复用读取最后成功应用的配置，未应用草稿不会直接改变启动行为。

## 8. 浏览器、PWA 与 tmux

普通标签页没有可独立分配的 Hyprland 窗口。ChatGPT、X 要进不同工作区，需独立 Web App/PWA 窗口及可信的独立身份；标题不同不能证明身份不同。

优先登记已有 PWA。高级向导可创建 `omarchy-launch-webapp` 入口，先捕获真实身份再登记；浏览器未产生独立身份时，拒绝用普通浏览器 class 接管网页。

专用 tmux 入口：

```text
omarchy-launch-tui --app-id=org.omarchy-workspaces.tmux tmux new-session -A -s Work
```

工具通过 `tmux list-clients` 和父进程关系寻找已经连接 `Work` 的独立终端，尝试复用旧窗口。VS Code 内置终端不会被当作独立终端，也不会自动关闭已有多余窗口。

## 9. 恢复命令的区别

| 命令 | 用途 |
| --- | --- |
| `doctor` | 检查配置、受管文件、窗口及快捷键 |
| `recover` | 根据恢复记录处理被中断的事务 |
| `reset` | 撤销全部生效接管，保留分配和安装 |
| `apply` | 按保存分配重新接管 |
| `apply --adopt` | 核对后接纳外部改动，更新恢复基线 |

`--adopt` 不是忽略错误开关。安装器和普通保存不会自动执行它，处理顺序见[故障排查](TROUBLESHOOTING.md)。

## 跟随 Omarchy 主题的面板

工作区管理面板使用 Omarchy Shell 的 `qs.Commons`：背景、文字、遮罩来自
`Color.menu`，强调色来自 `Color.accent`，错误提示来自 `Color.urgent`。
面板外框使用官方 `BorderSurface`，支持主题的渐变及各边宽度。字体、
字号、间距和圆角使用 `Style`；按钮的悬停、选中及焦点填充沿用共享状态
规则。更换主题后，已打开的面板也通过绑定更新，无需单独配置插件配色。

宽屏保留左侧可搜索的应用列表和右侧设置；窄屏自动改为纵向，内容可
滚动。选中应用同时显示强调色侧条和工作区编号；键盘焦点另有边框。
保存、启动和取消管理放在应用设置附近，全局操作保留独立位置。

开发验证（需 Qt 6 QtTest / qmltestrunner；Qt 适配器不改变实际桌面主题、不执行后端操作）：

```bash
python3 scripts/verify_qml.py
# 可选 PySide6 适配器：python scripts/verify_ui.py --theme dark
```

测试包含打开状态下切换深浅调色板、字号和圆角，宽/窄布局、搜索、
键盘操作和确认对话框。实际桌面运行仍需 Omarchy Shell 的 `qs.Commons`
与 `qs.Ui`。旧宿主的 QML 缓存若保留旧样式，可执行 `omarchy restart shell`
后重新打开面板；该操作不重启应用或 tmux。

## 中文 / English

面板右上角的 `中文 / English` 按钮立即切换界面语言，默认中文。
按钮、表单、说明、确认对话框和常见后端结果都支持两种语言。
操作执行中或确认对话框打开时，语言开关暂时禁用，避免中途混用语言。
应用名称、用户配置、快捷键与路径保留原始文字。

选择保存到 `~/.config/omarchy-workspaces/ui.ini` 的 `[ui] language`，
值为 `zh` 或 `en`；无效值按中文显示。退出面板或重启 Shell 后仍保留。
语言偏好是独立的公开配置；可由使用者的 dotfiles 工具选择同步。切换语言不修改工作区
规则或启动应用。高级设置打开的终端 CLI，以及未匹配的原始诊断日志，
保留程序输出语言，不自动翻译用户数据。

## Scratchpad 临时工作区

按 Super+S 显示 scratchpad 后启动受管应用，它会留在 scratchpad，
继续使用 Super+S 显示 / 隐藏；普通启动仍按固定工作区分配。
如果同一应用仅在隐藏的 scratchpad 中，普通入口会将它归回默认工作区。
工具捕获启动时的上下文；等待新窗口时若隐藏 scratchpad，不会再次展开。
