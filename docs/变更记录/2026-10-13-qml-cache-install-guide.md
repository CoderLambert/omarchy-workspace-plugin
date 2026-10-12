# 补全界面更新后的 Shell 重启步骤

- 日期：2026-10-13
- 分支：main
- 范围：安装与升级说明、故障排查、离线发行文档。

## 根因与改动

用户在新机器通过 Omarchy 插件管理器安装了正确提交与相同版本，但仍显示重构前的旧布局。直接从 GitHub 克隆确认 main@ff7af1e 的 Panel.qml、WorkspaceGroup.qml 与本机一致；远程离线载荷也包含相同界面。

Omarchy shell 的插件重扫尝试调用未暴露给 QML 的 Qt.clearComponentCache，旧 QML 类型仍可留在运行时缓存中。上游问题见 https://github.com/omacom/omarchy/issues/9251 。用户执行 omarchy restart shell 后确认新版布局已正常显示。

README 双语恢复 Shell 重启步骤，INSTALL/PUBLISHING 与故障排查同步；区分已安装源码、后端版本、生成规则与实际加载的界面。未新增自动重启或程序逻辑，版本仍为 RC2。

## 文件

README.md、README.zh-CN.md、docs/INSTALL.md、docs/PUBLISHING.md、docs/TROUBLESHOOTING.md、CHANGELOG.md；离线安装器和 SHA256SUMS 同步文档载荷。

## 验证

- 远程全新克隆的 QML 与本机逐字一致，远程离线安装器界面与源码一致。
- PySide6 / Qt 6.8.3 离屏机制复现：Qt.clearComponentCache 在 QML 不存在；同 URL 在原进程仍加载 old-layout；新进程加载 new-layout。禁用磁盘缓存以单独验证进程内缓存。
- 用户确认新机器 Shell 重启后界面正常，未替代为自动化桌面验证。
- ZIP / 离线载荷、SHA-256、Shell 语法和 Git diff --check 通过；本次不改变 Python/界面代码，不新增业务测试。
