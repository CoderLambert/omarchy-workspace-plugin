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

### 查看和编辑一个应用

「工作区安排」首页按应用的默认工作区编号分组，宽屏显示两列，窄屏显示一列。分组使用实际编号，不会强制命名为 AI、开发等用途；这些用途仅属于可选推荐分配。

应用行显示名称、运行情况；当前窗口不在默认位置时，会显示实际工作区。搜索可匹配应用名称、ID 或工作区编号，只筛选显示，不改变配置。

点击应用行打开编辑弹层：

1. 在“打开位置”选择 `1–4` 快选，或输入 `1–999` 的工作区编号。
2. 在“再次打开应用”选择“直接切换到已有窗口”或“先移回默认工作区，再切换”。普通工作区中两种方式的差异见下一节；临时工作区另遵循 Scratchpad 打开方式。
3. 点击“保存”更新配置。**默认不移动已打开窗口**；只有勾选“现在也移动已打开的窗口”，按钮才变为“保存并移动”，且仅整理此应用。

“更多应用选项”中保留快捷键信息、“打开或切换到此应用”、“高级设置…”和“停止管理此应用…”。停止管理会恢复原入口和相关绑定，不关闭正在运行的应用。

需要移动特殊工作区中的窗口时，先勾选“现在也移动已打开的窗口”，再在“更多应用选项”中勾选“整理时包含临时工作区”。该授权仅用于本次操作；重新打开编辑弹层后默认不勾选。未选择立即移动时，该特殊工作区选项不可用。

### 添加应用、全部整理和诊断

| 入口 | 结果 |
| --- | --- |
| 首页 → 添加应用 | 打开终端向导，选择已安装应用或识别已打开窗口 |
| 更多 → 使用推荐分组… | 先说明识别和整理行为，确认后在面板内执行预设 |
| 更多 → 整理已打开窗口… | 独立确认后，将已登记的普通工作区窗口移回各自默认工作区 |
| 更多 → 配置与诊断 | 查看操作结果、问题、版本和配置路径；完整文本可选择复制 |
| 配置与诊断 → 检查配置 | 执行 `doctor`，更新完整报告 |
| 配置与诊断 → 接纳外部修改… | 核对后执行 `apply --adopt`，更新恢复基线；有问题时显示该入口 |
| 更多 → 重新读取状态 | 重新读取当前配置和窗口情况 |
| 更多 → 高级设置… | 打开终端向导管理快捷键、匹配与其他选项 |
| 更多 → 中文 / English | 切换面板语言，并保存选择 |
| 更多 → 停用全部规则… | 确认后执行 `reset`，保留安装和应用分配；已打开窗口不会自动搬回 |
| 首页异常提示 → 恢复任务 / 应用配置 | 对应 `recover` / `apply`，处理被中断的操作或尚未生效的配置 |

“整理已打开窗口…”每次都会显示确认，默认跳过 scratchpad 和其他 `special:*`。确认框中的“整理时包含临时工作区”只授权这一次整理，下次重新打开确认框恢复为未勾选；不关闭窗口中的任务。

“使用推荐分组…”会先提示打开常用应用，并说明工作区分配与整理行为。确认后在面板内执行，显示忙碌状态；完成后展示新增应用数、受管应用数、整理窗口数和逐项识别结果，并自动刷新列表。未识别的应用可先打开再用“添加应用”。取消准备提示不会执行操作。

诊断报告放在独立弹层，支持鼠标滚轮、滚动条和选择复制；更新报告时回到顶部。首页保留简短结果或问题提示，可点击“查看详情”或“查看问题”进入报告。接纳外部修改前需先返回并处理未保存的应用编辑，再核对将成为恢复基线的文件内容。

“添加应用”和“高级设置…”仍在终端完成；结束后回到面板，选择“更多 → 重新读取状态”。文件操作运行时先等待结果，再关闭面板或执行下一项；显示成功前不要把修改视为已完成。

### 未保存修改、错误和键盘操作

保存失败会保留工作区、复用方式、立即移动选项，以及打开编辑时读取的配置版本。若其他面板或 CLI 已修改配置，本次保存不会擅自使用新版本覆盖。先查看错误；需要载入新配置时，返回并明确确认放弃编辑，再执行“更多 → 重新读取状态”。

返回、关闭或执行会重新读取配置的操作时，未保存修改需要确认放弃；取消确认可继续编辑。诊断查看不会替你保存或丢弃字段。

上下方向键移动应用焦点，Enter 打开编辑，Tab 切换控件，Esc 逐层返回或请求关闭。退出弹层后焦点返回对应应用或原入口；存在未保存修改时仍需确认。

## 3. 两种复用策略

假设 Slack 默认在 4，你手动把窗口移到了 5：

| 策略 | 再次点击受管入口 |
| --- | --- |
| 直接切换到已有窗口（`focus`，默认） | 跳到 5，聚焦已有窗口 |
| 先移回默认工作区，再切换（`move`） | 将窗口移回 4，再聚焦 |

普通启动的新窗口按配置进入默认工作区；显示 scratchpad 时的启动和复用另见本文“Scratchpad 临时工作区”。有多个匹配窗口时选择最近使用的一个，不自动关闭其余窗口。托盘进程不是 Hyprland 窗口；应用仅在托盘时，工具调用原入口，由应用恢复或创建主窗口。

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

`setup` 保留已有应用登记和个人快捷键，仅补齐应用工作区分配；默认不添加预设快捷键。下表的键是可选的应用启动/复用入口，不是工作区切换键。它们与 Omarchy 系统启动键重合，因此新机器无需启用它们，也无需逐项处理冲突。

需要快捷键复用功能时执行 `omarchy-workspaces setup --with-shortcuts`。冲突先展示原绑定与新命令，输入 yes 才逐项授权；默认跳过，非交互运行不接管冲突。授权保存在 `replace_shortcut_keys`，不会把一个键的批准扩展到其他键。旧的手工 `replace_shortcuts` 字段仍兼容。已有用户主动设置的键不会被默认预设清空。

例如原来的 `Super+Return` 调用系统终端启动器；启用插件对应键后改为 `omarchy-workspaces launch terminal`，先查找并复用终端窗口，没有窗口时再启动。不改键时仍可通过受管菜单，或编辑弹层“更多应用选项 → 打开或切换到此应用”使用窗口复用。

| 应用 | 工作区 | 可选快捷键 |
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
omarchy-workspaces arrange --include-special --dry-run # 明确包含特殊工作区的计划
omarchy-workspaces arrange

omarchy-workspaces launch slack
omarchy-workspaces launch slack --new
omarchy-workspaces remove slack
```

CLI `set --workspace` 与面板默认“保存”均保留当前窗口位置；立即移动可紧接 `arrange --app slack`，或在面板勾选立即移动后使用“保存并移动”。`arrange --dry-run` 只显示计划。

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
| `replace_shortcut_keys` | 逐项明确确认过的冲突键；存在时优先于旧的 replace_shortcuts 布尔字段 |
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

工作区安排面板使用 Omarchy Shell 的 `qs.Commons`：背景、文字、遮罩来自
`Color.menu`，强调色来自 `Color.accent`，错误提示来自 `Color.urgent`。
面板外框使用官方 `BorderSurface`，支持主题的渐变及各边宽度。字体、
字号、间距和圆角使用 `Style`；按钮的悬停、选中及焦点填充沿用共享状态
规则。更换主题后，已打开的面板也通过绑定更新，无需单独配置插件配色。

首页按工作区分组，宽屏两列、窄屏一列，内容可滚动。运行状态用圆点和
文字提示，键盘焦点有独立边框；点击应用后才打开编辑弹层。保存留在
编辑弹层底部，全局整理、诊断和维护操作集中在“更多”。面板与弹层尺寸
受可用显示区域约束，不再依赖固定宽度的左右配置栏。

开发验证（需 Qt 6 QtTest / qmltestrunner；Qt 适配器不改变实际桌面主题、不执行后端操作）：

```bash
python3 scripts/verify_qml.py
# 可选 PySide6 适配器：python scripts/verify_ui.py --theme dark
```

测试包含打开状态下切换深浅调色板、字号和圆角，宽/窄布局、搜索、
键盘操作和确认对话框。实际桌面运行仍需 Omarchy Shell 的 `qs.Commons`
与 `qs.Ui`。旧宿主的 QML 缓存若保留旧样式，可执行 `omarchy restart shell`
后重新打开面板；该操作不重启应用或 tmux。

Qt 离屏与适配器检查只覆盖相应测试环境，不代表用户真实桌面验收。
2026-10-13 界面简化已合并 main，用户确认真实桌面验收通过；仍保持 RC 版本，
其他环境兼容性范围与自动化测试见 [界面简化说明](UI-SIMPLIFICATION.md)。

## 中文 / English

“更多”中的 `中文 / English` 按钮立即切换界面语言，默认中文。
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

## RC1 前后端同步

状态包含 `buildId` / `backendBuildId`，根据真实 Python 文件计算，不信任安装记录里的自报值。版本或指纹不同，面板阻止修改并提供“更新组件”。安装保留分配、菜单与恢复现场；不自动接纳外部修改、不启动应用、不整理窗口。手工 Git 更新也可运行 `install.sh --backend-only` 同步。
