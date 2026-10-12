# 主题适配、中英双语和 scratchpad 的插件仓库交付

- 日期：2026-10-12
- 分支：main
- 产品仓库：CoderLambert/omarchy-workspace-plugin
- 范围：同步已在本机使用的插件改动与使用说明；个人配置继续由 dotfiles 管理。

## 目标和实际修改

| 文件或区域 | 实际修改 |
| --- | --- |
| Panel.qml、qml/ActionButton.qml、WindowChoice.qml、Theme.qml | 绑定 Omarchy 官方 Color / Style / BorderSurface，增强选中状态和窄屏布局 |
| qml/Strings.js、Panel.qml | 中文 / English 设置，保存至 ui.ini；翻译面板与常见结果，保留用户数据和原始诊断 |
| src/omarchy_workspaces/hypr.py、manager.py | scratchpad 内启动留在临时工作区，普通启动保持固定分配；等待窗口时隐藏 scratchpad 不强制展开 |
| src/omarchy_workspaces/plugin.py、installer.py | 识别经精确校验的 Chezmoi 启动器；安装保留该入口；离线载荷包含 JS 和 QML 测试 |
| .gitignore、scripts/ui_fixture.py、verify_qml.py、verify_ui.py、tests/ui/tst_workspaces.qml | 隔离 UI 适配器及主题 / 双语 / 保存 / 布局 / 键盘检查；验证入口禁用 Python 字节码，避免写入被监听的插件目录 |
| tests/test_workspaces.py、test_cli_integration.py、test_native_plugin.py、test_release.py | scratchpad、受管启动器、测试进程和离线文件完整性验证 |
| README.md、docs/INSTALL.md、USAGE.md、PUBLISHING.md | 痛点、功能、快速安装、日常使用、恢复、更新和英文上手；安装地址统一为本产品仓库 |
| CHANGELOG.md、TEST-REPORT.md、本记录 | 更新产品说明和真实验证结果，保留历史验证边界 |
| install-omarchy-workspaces.sh、SHA256SUMS | 重建本仓库已有的离线分发文件与校验清单 |

## 行为和边界

原生安装从 `omarchy plugin add https://github.com/CoderLambert/omarchy-workspace-plugin.git --enable` 开始，随后运行插件目录的 `install.sh --backend-only` 安装后端和菜单。全新用户无需取得作者的 dotfiles。Git 插件更新之后仍需同步后端。

默认安装保留分配，不执行 setup、自动识别或整理窗口。scratchpad 沿用原 Super+S。语言选择支持 zh / en，默认中文，操作和确认过程中暂时禁用切换；终端 CLI 和未知原始诊断不保证英文输出。Omarchy 官方主题和用户应用配置不进入本产品仓库。

同步仅选取插件源码和文档差异，保留产品仓库已经存在的官方安装地址、离线分发方式和引用来源；未复制个人 apps.toml、ui.ini、安装记录、插件 Git 元数据、缓存或日志。

## 实际验证

- 插件仓库源码的 Python 测试：115 项通过，11.532 秒。
- 插件仓库的 QtTest：10 项通过，1.887 秒；包括中文 / 英文切换、语言落盘和独立设置读取。
- Bash 安装 / 卸载脚本语法和 Omarchy 插件目录验证通过。
- README 相对文档链接检查通过。
- 离线分发文件在提交前重新构建；解压和校验结果见 TEST-REPORT.md 的当前交付补充。

本机之前已实际检查面板显示，使用自建探测窗口验证普通分配、scratchpad 显示 / 隐藏、受管复用和回到默认工作区，并只清理自建窗口。上述是本机实现阶段的真实验证，本轮没有重新操作用户应用。

## 未验证的范围

其他实体机器、全部第三方应用、全部主题和多显示器组合未完整验收。离屏测试使用显式适配器，不代表真实 Quickshell / Hyprland 全部交互。未上传独立 GitHub Release 附件或创建市场条目，未执行真实模型调用。个人 dotfiles 已有提交保留，不改写历史。
