# 故障排查

先保留报错里的路径与完整输出。不要先删除 `apps.toml`、`manifest.json`、`pending.json` 或状态目录；恢复原入口需要其中记录。

## 受管文件被其他工具修改

典型错误：

```text
受管文件被其他工具修改：…/applications/grok-bot.desktop；doctor 检查后可 apply --adopt 保留现状作为恢复基线
```

含义：该文件在上次成功应用后被外部工具或手工改写。可能是应用升级、Omarchy 更新了 desktop，也可能是你自己改了启动参数。工具停止覆盖，保护当前文件及原恢复记录。

处理顺序：

1. 执行检查，确认具体文件：

   ```bash
   omarchy-workspaces doctor
   ```

2. 打开报告中的文件，与当前实际启动方式对照。对于 Grok Bot，核对 `Exec`、名称及启动器是否仍指向期望程序，而不是无关的网页或旧路径。
3. 确认外部更新应保留后，再执行：

   ```bash
   omarchy-workspaces apply --adopt
   omarchy-workspaces doctor
   ```

`--adopt` 将当前外部修改作为新的恢复基线，再重新生成受管内容。以后撤销会恢复这份新基线，不再恢复被替代的旧版本。它不是强制覆盖所有错误的选项；若同时报告其他未知文件，先逐个核对。

没有外部修改的本工具 desktop 隐藏副本不会被误当成新基线；原本来自系统目录的入口会继续读取最新系统版本，避免应用升级后的 `Exec` 被旧副本遮住。若手工草稿已经移除一个应用，`apply --adopt` 会保留其已被外部改写的文件并解除管理，不要求把已删除登记加回来。

不确认外部变更时，保留现状并检查来源。升级到 1.2.0 可以先执行 `bash install.sh --no-setup`，只更新程序和面板，不会触发这一步，也不会自动接纳变更。

## 点击一次却打开两个窗口

先区分“两个入口”“两条启动指令”和“应用自己打开多个窗口”。从一个已登记应用开始排查：

```bash
omarchy-workspaces list
omarchy-workspaces doctor
omarchy-workspaces windows
hyprctl -j binds
```

| 观察 | 检查方向 |
| --- | --- |
| 只有快捷键会双开 | 同一物理组合是否同时保留原绑定、受管绑定或第三方热键；注意修饰键顺序与 Return 大小写 |
| 菜单显示两个同名图标 | 是否同时存在原 desktop、旧代理或手工创建入口；用 `doctor` 检查漂移 |
| CLI 复用正常，某个菜单仍新开 | 该菜单可能仍调用原命令，未走受管代理 |
| 已有窗口，`doctor` 仍显示 0 个登记窗口 | 窗口身份不匹配，应用升级、安装渠道或启动方式可能改变了 class |
| 完全关闭后，单次受管调用仍产生两个窗口 | 检查原应用的会话恢复和启动行为；工具不自动关闭窗口 |

可直接比较受管入口的行为：

```bash
omarchy-workspaces launch grok_bot
```

用 `list` 中本机实际 ID 替换 `grok_bot`。若能正确聚焦，而某个菜单或快捷键还会新开，继续检查那个入口的指令。不要给相同快捷键再叠加一条 `launch`。

1.1.1 起保留了 Lua 解绑变体及重载后实际绑定数量检查。配置已被外部改动、入口没有走受管命令或窗口身份改变，仍可能绕过这些保护。`config --advanced` 可重新捕获身份；修改后再检查。

启动过程中，同一应用的重复点击由应用锁拦截；超时后有短时冷却。已有重复窗口不会被自动关闭，先自行保留需要的窗口，再验证受管入口。

Omarchy 菜单短暂显示“Launching…”本身不等于新增窗口，以实际窗口数量为准。

## 只有托盘，点击后又出现窗口

窗口复用检查的是 `hyprctl clients` 中的实际窗口，不是进程列表。微信、Slack、Discord 关闭主窗口后可能留在托盘；这时调用原入口以恢复主窗口是正常流程。

如果恢复后的窗口始终不匹配，比较 `omarchy-workspaces windows` 中的 `class`、`initialClass` 与登记内容，再通过高级配置重新捕获。不要仅凭进程名或聊天标题补身份。

## ChatGPT、X 或浏览器被一起移动

普通标签页共用浏览器窗口，不能按网页分工作区。检查目标是否真的是独立 Web App/PWA，以及是否具有独立窗口身份。

不同 Chrome Profile、不同浏览器或重新安装 PWA 可能产生不同身份。不要把 `google-chrome` 等通用 class 直接用于 ChatGPT/X 的独立登记；先正常打开对应入口，再重新登记可信身份。

如果 ChatGPT App 与 ChatGPT 网页实际上是同一个窗口，应使用同一登记或别名；若必须分开，则需要具有不同窗口身份的入口。

## 面板没有显示或退回终端

依次确认原生插件已发现并启用：

```bash
omarchy plugin list
omarchy-shell shell rescanPlugins
omarchy plugin enable lambert.workspaces
omarchy-workspaces gui
```

插件文件应位于 `~/.config/omarchy/plugins/lambert.workspaces/`，其中包含 `manifest.json` 和 `Panel.qml`。

缺少 `omarchy-shell` 或插件验证命令时，安装器会回退终端；这不代表已验证图形界面。确认系统版本与插件支持后重跑安装器。不要通过安装另一个不相关的系统 Shell 来绕过缺失依赖。

已有插件加载但面板报 QML 错误时，保留原始错误并使用 `omarchy-workspaces config` 继续操作。重新安装同版本/更新版本后执行 `rescanPlugins`；不要把“重新发现成功”视为界面加载成功。

## 首开提示未安装后端

这通常发生在使用 `omarchy plugin add` 后。官方插件安装命令只克隆仓库，不执行 Python 后端安装。

点击面板的安装后端按钮，或执行：

```bash
bash ~/.config/omarchy/plugins/lambert.workspaces/install.sh --backend-only
```

它补装后端和菜单，不复制、覆盖当前插件目录，也不重新启用插件或改写 Shell 配置。完成后回面板刷新；用 `~/.local/bin/omarchy-workspaces --version` 核对。

## 系统菜单缺少“工作区配置”

```bash
omarchy-workspaces repair-menu
omarchy-menu refresh
```

`repair-menu` 只修复菜单登记，不重新应用工作区规则，不会自动处理 Grok Bot 等启动项漂移。原生菜单扩展固定在 `~/.config/omarchy/extensions/omarchy-menu.jsonc`，不跟随 `XDG_CONFIG_HOME`。旧版自定义 XDG 路径中的受管登记会迁移到此处，同时保留新旧文件的用户项。

同名非受管项、损坏的 JSONC 或符号链接会让登记停止。按报错核对原文件，保留自己的菜单内容；不要整份覆盖。

## 终端与面板看到不同配置

检查两边环境中的 `XDG_CONFIG_HOME`、`XDG_DATA_HOME`、`XDG_STATE_HOME` 是否一致，并用 `doctor` 确认真实路径。只在 `.bashrc` / `.zshrc` 给交互 shell 设置 XDG，不会自动改变已经运行的 Omarchy Shell。

原生插件路径按 Omarchy 4.0.4 固定为 `$HOME/.config/omarchy/plugins/lambert.workspaces`，系统菜单扩展固定为 `$HOME/.config/omarchy/extensions/omarchy-menu.jsonc`；后端应用配置、数据、状态尊重各自 XDG 变量。不要把插件或原生菜单移到自定义 XDG 位置来修复后端路径问题。

## 配置应用失败或重载报错

```bash
omarchy-workspaces doctor
hyprctl configerrors
```

工具会先检查现有配置，再应用自身变更，最后校验重载结果和受管快捷键。事务失败时尝试回滚；原配置本来有错误时，先修复报告中的原配置问题。

使用自定义 `Hyprland --config` 入口时，在 TOML 的 `[defaults]` 下设置实际绝对路径：

```toml
hypr_config = "/home/你的用户名/.config/hypr/实际入口.lua"
```

该行只是格式示例，必须替换为本机真实路径。不要假定工具能从目录存在性推断自定义启动参数。

## 提示存在中断事务

```bash
omarchy-workspaces recover
omarchy-workspaces doctor
```

`recover` 根据 `pending.json` 处理尚未完成的文件变更。中断后若有人再次改了文件，工具拒绝覆盖；保留恢复记录并核对报错文件。删除 `pending.json` 会丢失判断依据，不是修复方式。

## 面板提示配置已经变化

另一个终端或面板可能刚修改了分配。刷新面板，核对最新配置后重新操作；不要反复提交旧页面。只刷新不应改变规则。

## 禁用插件后规则仍在

这是官方插件生命周期的边界：`plugin disable` / `plugin remove` 不执行工作区恢复。

```bash
omarchy-workspaces reset
```

这会撤销规则、原入口隐藏副本和相关快捷键接管，但保留工具和分配。以后 `omarchy-workspaces apply` 可恢复。

撤销接管并卸载入口使用：

```bash
omarchy-workspaces uninstall
```

先恢复受管规则，再移除受管入口、命令和未修改的安装器插件副本。应用配置、后端副本和日志保留；Git 管理、手工安装或有本地修改的插件目录会保留并提示后续原生移除。外部改写导致规则恢复被拒绝时，先处理该问题，不要直接删除程序或插件目录。

## 日志与问题反馈

原应用启动输出默认在 `~/.local/state/omarchy-workspaces/launch.log`，设置 `XDG_STATE_HOME` 时使用对应路径。反馈时附上：版本、具体应用 ID、操作入口、`doctor` 完整报告，以及相关窗口的 class/initialClass。实际窗口标题和日志可能包含自己的内容，按需要删去无关信息。
