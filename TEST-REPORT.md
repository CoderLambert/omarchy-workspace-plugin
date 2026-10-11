# 验证记录 · 1.2.0

验证日期：2026-10-12（Asia/Shanghai）。主目标：Omarchy 4.0.4。

## 结论

**108 项 Python 自动化测试通过，0 失败、0 跳过；20 项 Qt 离屏界面断言通过。** 官方 v4.0.4 插件目录验证通过，安装脚本语法通过。完整交付 ZIP 还经过解压、逐文件 SHA-256 校验和从解压源码运行测试。

这些证据覆盖程序、文件事务与 Qt Quick 交互。**没有连接用户真实 Omarchy 桌面，不等于真实 Quickshell/Hyprland 或真实应用验收通过。**

## 1. 后端、安装及迁移

| 范围 | 核实内容 | 结果 |
| --- | --- | --- |
| 原有功能回归 | 应用发现、普通新增、PWA 身份、精确匹配、最近窗口、tmux 关联、启动锁、规则与快捷键、文件恢复 | PASS |
| 新原生安装 | 创建有效插件目录；系统菜单打开原生 GUI；没有可用 Shell 时回退终端；安装不扫描、不打开应用、不应用分配 | PASS |
| 重复安装与升级 | 保留 1.1.3 配置格式、生效规则与恢复记录；不自动 adopt；拒绝覆盖手工修改的插件 | PASS |
| 原生 Git 安装后引导 | 不覆盖当前插件或 Git 元数据；后端版本不一致时阻止普通写操作，安装后解除 | PASS |
| 中断时补装后端 | 后端旧版/缺失可先修复程序；原样保留 pending.json 和配置现场，再执行 recover | PASS |
| 面板保存 | 只整理选中应用；其他应用手动位置保留；请求使用固定操作白名单，不接收任意 shell 指令 | PASS |
| 并发修改 | 旧 revision 被拒绝，不覆盖另一操作已经成功保存的分配；过期撤销受保护 | PASS |
| 配置状态 | 主 Hyprland 加载标记缺失时报告问题，不显示规则已启用 | PASS |
| 外部 desktop 更新 | 未漂移的系统入口继续采用系统新版本；明确接纳实际漂移；删除应用的 TOML 草稿可同时接纳并保留外部文件 | PASS |
| 原生菜单固定路径 | 插件和菜单使用 HOME/.config/omarchy；后端配置继续遵循 XDG | PASS |
| 旧菜单迁移 | 旧记录无 target 时识别 XDG 旧路径；保留两边用户菜单和权限；失败恢复两边及原记录 | PASS |
| reset / uninstall | reset 恢复规则但保留安装和分配；uninstall 删除受管命令及未修改插件，保留配置、后端副本、日志及外部修改 | PASS |
| 安装失败回滚 | 菜单登记失败后恢复原后端、插件和命令；同名非受管项、Git 管理目录、符号链接均受保护 | PASS |
| 大体积离线安装器 | 载荷从安装脚本自身读取，避免 Linux 单参数长度限制；含空格的路径可解压；载荷篡改时在写入目标前拒绝 | PASS |
| Lua 生成规则 | 真实 Lua 5.4 虚拟机加载语法及调用测试桩；并非真实 compositor API 执行 | PASS |

测试使用临时 HOME、XDG 目录和模拟的 hyprctl、gtk-launch、omarchy-shell 等进程。安装器、CLI 和 JSON bridge 本身以真实子进程运行；平台与实际应用被替代。

复现：

```bash
PYTHONPATH=src python3 -B -W error::ResourceWarning -m unittest discover -s tests -v
```

## 2. 原生插件声明及脚本

实际执行了本包 `reference/bin_omarchy-plugin-validate`，它为固定 Omarchy v4.0.4 的官方原文，来源和摘要见 `reference/SOURCES.md`：

```bash
bash reference/bin_omarchy-plugin-validate .
bash -n install.sh uninstall.sh install-omarchy-workspaces.sh
```

验证了 schemaVersion、ID、kind、entry point、文件存在性与符号链接限制。**官方验证器不编译 QML，也不证明插件实际成功显示。**

## 3. Qt Quick 界面

使用 Qt / PySide6 Essentials 6.9.3 的离屏运行时。适配脚本用明确的窗口及进程测试桩替代 Quickshell 宿主模块，其余界面由真实 Qt Quick 创建。

20 项断言覆盖：

- 状态载入与默认应用选择；搜索过滤。
- 真实 Qt Tab 事件的焦点移动，以及确认框 Tab 循环。
- 应用切换时未保存内容确认。
- 工作区数字输入尚未失焦时仍正确提交；保存后绑定继续有效。
- focus / move 的选择和恢复。
- revision 随修改请求提交，忙时不提交第二个命令、不关闭面板。
- 640 × 480 布局可垂直滚动，不要求大显示器才能访问控件。
- 确认框模态、Escape 先关闭确认框、再关闭面板。
- 未安装后端时阻止普通修改，保留安装入口。

结果：20 项通过，Qt 警告为 0。两个独立组件通过 qmllint；Panel.qml 原文通过 qmlformat 的完整语法解析。

可选开发验证（运行环境需另有 PySide6 Essentials；**日常安装不需要它**）：

```bash
python3 scripts/verify_ui.py --output /tmp/omarchy-workspaces-ui-check
```

可加 `--font /绝对路径/中文字体.otf` 为测试环境加载中文字体。该脚本无联网、无实际后端调用、不写桌面配置；不传输出目录时使用临时目录，拒绝向源码内生成截图以免触发插件热重载。输出 report.json 和三张检查图，不随发布包提供模拟截图作为真实桌面证据。

## 4. 分发包

发布包包含根 manifest、Panel.qml、组件、Python 源码、安装器、全部测试、可选 UI 检查脚本、文档及引用来源。

```bash
sha256sum -c SHA256SUMS
bash install-omarchy-workspaces.sh --extract /tmp/ows-source-review
```

提取目标须不存在。单文件安装器先校验内置 ZIP 载荷；不访问远端仓库下载安装本工具。最终 ZIP 展开后的所有清单项均已校验，并从其源码重新运行 Python 测试。

## 5. 仍需在用户桌面核实

1. Omarchy Shell 能实际加载原生 Quickshell 类型并显示面板；键盘焦点、Escape、多显示器和缩放正确。
2. 受管菜单及快捷键确实指向本工具；实际应用再次打开复用窗口，连续点击不重复拉起。
3. Chrome/PWA、ChatGPT、Grok Bot、微信及终端的真实 class/initialClass 与登记一致。
4. 插件热重载、显式禁用或删除时的宿主生命周期。keepLoaded 可保护普通隐藏，不会阻止宿主卸载；中断后依赖 recover。
5. 真实应用的托盘恢复、启动速度及自身多窗口策略。

按 README / docs/INSTALL.md 的本机验收步骤进行。未运行的项目不标记为 PASS。
