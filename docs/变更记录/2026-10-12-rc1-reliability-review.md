# RC1 发版审核可靠性修复

- 日期：2026-10-12 至 2026-10-13
- 分支：main
- 产品仓库：CoderLambert/omarchy-workspace-plugin
- 版本：1.3.0-rc.1，公开 Beta 候选；未创建 Stable Release。

## 实际修改

| 文件或区域 | 改动 |
| --- | --- |
| manifest.json、src/omarchy_workspaces/__init__.py | 统一 RC 版本，声明 GPL-3.0-only |
| src/omarchy_workspaces/build.py、gui.py、installer.py | 真实 Python 文件的确定性构建指纹，版本 / 构建错配保护，一键同步后端；不依赖自报安装元数据 |
| src/omarchy_workspaces/discover.py、cli.py、hypr.py、core.py、manager.py | 预设默认不替换冲突键，展示原绑定及新命令，逐项确认、默认跳过；只授权确认过的键；预览后变化拒绝写入 |
| manager.py、gui.py、cli.py、Panel.qml、qml/Strings.js | 整理默认跳过 special:* / 负编号工作区；CLI --include-special 与面板勾选显式包含，布尔参数校验 |
| tests/test_rc1.py、test_discovery.py、test_native_plugin.py、test_release.py、tests/ui/tst_workspaces.qml | 对应回归检查、构建元数据伪造保护和 GPL / 构建文件载荷完整性 |
| scripts/verify_ui.py、verify_distribution.py | CI 可运行的深浅主题 / 语言 / 交互检查，ZIP / 离线载荷和许可证验证 |
| .github/workflows/ci.yml | PR / main 的 Python 3.11、3.13 独立测试；Qt 6.8.3 UI 检查，构建、校验、上传 artifacts；权限只读，不自动创建正式 Release |
| LICENSE、README.md、docs/INSTALL.md、USAGE.md、PUBLISHING.md、RELEASE-CHECKLIST.md、CHANGELOG.md、TEST-REPORT.md、本记录 | GPL-3.0-only，保留第三方许可，安装后端也附带 LICENSE；RC → Stable 验收与升级边界 |
| install-omarchy-workspaces.sh、SHA256SUMS | 同步 RC 的已有离线分发文件和校验清单 |

## 兼容与安全边界

旧 replace_shortcuts 字段仍兼容。自动预设新增的逐键授权字段 replace_shortcut_keys 存在时优先，明确确认 A 不授权 C；修改快捷键的显式 CLI / 高级菜单会重新处理授权。非交互运行跳过冲突键，应用仍可登记。

版本或构建不同，面板阻止修改，安装动作仍可用于同步程序。恢复事务现场、应用分配和语言配置保留，不自动 adopt、setup 或移动窗口。指纹读取真实代码内容，安装记录被修改不能伪装代码一致。

特殊工作区默认保护覆盖自动预设、单应用保存整理和全局整理。明确勾选 / --include-special 才能搬出；dry-run 不移动。临时工作区状态未同步成用户配置。

## 实际验证与交付检查

- Python -W error::ResourceWarning 单元及集成检查：129 项通过。
- Qt 6.11.2 QtTest：11 项通过。
- PySide6-Essentials 6.8.3：深浅主题各 29 项通过，Qt 无警告。最初脚本使用 setdefault 导致继承用户的 Wayland 环境，浅色窗口更新出现 DPR 警告而失败；已改为强制 offscreen / software，深浅主题重新运行通过，没有过滤或忽略警告。
- CI YAML 的触发器、只读权限、矩阵结构与 Python 语法检查通过。
- 官方 Omarchy 插件目录验证和 Bash 安装脚本语法通过。
- 最终 ZIP / 单文件离线载荷、LICENSE、构建文件及校验清单在提交前执行验证。
- 首轮 GitHub CI：Python 3.11 / 3.13 后端、安装、官方验证和校验清单通过；UI 在 Qt 导入阶段退出 77，未执行测试。后续为 Ubuntu 补充 EGL / OpenGL 系统库，并让导入失败显示具体错误；依赖修复后的远程 CI 三个任务全部通过，记录见 https://github.com/CoderLambert/omarchy-workspace-plugin/actions/runs/38275317089 。该轮为 127 项后端检查；最终提交另含授权保留和安装许可证回归，远程结果仍以对应 Actions 记录为准。
- RC1 的实际原生 Git 克隆 / 添加、两次 backend-only、源码安装 / 重复安装 / 卸载以及离线安装均在临时 HOME 完成；桌面 IPC 使用适配器，未触碰当前用户会话。

## 仍需完成

真实 Omarchy 4.0.4 的新机器安装、Grok Bot 连续点击、外部 desktop 更新、RC 升级 / 卸载、多显示器行为尚未全部验收。部分新增配置仍打开终端，此轮保持该边界，未扩展原生发现向导。产品 GPL-3.0-only 根据作者本轮明确选择；reference/ 的第三方代码及许可保留。

用户当前安装和应用任务未被替换或重启。个人 dotfiles 仓库与本轮产品修改分离；正式发布须通过 RELEASE-CHECKLIST.md。
