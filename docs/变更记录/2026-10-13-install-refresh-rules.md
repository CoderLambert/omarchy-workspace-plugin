# 安装后自动刷新已启用的工作区规则

- 日期：2026-10-13
- 分支：main
- 交付：1.3.0-rc.2，插件自身独立更新后端与生效规则，不依赖个人 dotfiles。

## 问题与实现

旧安装器只更新程序，保留已生成规则，因此已安装环境可继续使用 silent 规则，导致新开应用分配到默认工作区但画面不跟随。新安装器在已有 install.lock 与 apply.lock 保护范围内，安装完成后自动重新生成并加载上一次已启用配置。

Manager 的事务执行抽成持锁内部方法，普通 apply 保持原接口。refresh-rules 使用已生效配置并不写配置草稿，保留未应用修改、注释和缺失草稿状态；安装器调用同一刷新逻辑。首次安装和已 reset 的配置不会被自动启用，不扫描、启动或移动任何应用。

规则更新沿用外部修改检测与 Hyprland 校验回滚。失败保留新后端用于诊断恢复，CLI 非零退出，GUI 返回失败并刷新组件状态，明确区分后端安装完成与规则刷新未完成。中断事务不自动恢复或覆盖。

## 实际修改

- src/omarchy_workspaces/installer.py、manager.py：自动刷新及配置/事务保护。
- src/omarchy_workspaces/cli.py、gui.py、qml/Strings.js：恢复命令、CLI/GUI 部分完成反馈与双语。
- __init__.py、manifest.json、scripts/verify_ui.py：RC2 版本与验证适配。
- tests/test_native_plugin.py：升级、重新安装、草稿、停用、外部修改、失败回滚回归。
- README 双语、INSTALL、PUBLISHING、RELEASE-CHECKLIST、IMPLEMENTATION、TEST-REPORT、CHANGELOG：更新流程与当前结果。
- 离线安装器与 SHA256SUMS：同步发行载荷。

## 实际验证

- Python 142 项通过（20.188 秒）。
- 新增 CLI refresh-rules 验证后，原生安装/桥接子集 24 项再次通过（15.801 秒）。
- QtTest 19 项通过；PySide6 / Qt 6.8.3 深浅主题各 42 项通过，无 Qt 错误；均为离屏适配器检查。
- 插件清单与 Shell 语法通过。完整 ZIP / 离线载荷与 SHA-256 校验通过（83 文件）。
- 新机器真实桌面安装未执行。

## 限制

新机器完整桌面安装、所有应用真实快捷键启动未执行。原生应用自行复用窗口但不发送激活请求时，仍需要插件受管入口保证聚焦；这一边界不由安装器修改。
