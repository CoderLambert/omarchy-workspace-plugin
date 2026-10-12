# 发布为 Omarchy 原生插件仓库

本项目源码现已托管于 [`CoderLambert/omarchy-workspace-plugin`](https://github.com/CoderLambert/omarchy-workspace-plugin)，默认分支根目录符合 Omarchy 原生插件结构，可直接通过 GitHub 安装。仓库目前没有单独的 GitHub Release 附件或插件市场条目。本文说明仓库结构、安装和后续发布维护方式。

## 1. 仓库结构

Git 仓库根目录必须直接包含：

| 文件/目录 | 作用 |
| --- | --- |
| `manifest.json` | 插件 ID `lambert.workspaces`、版本、`panel` 类型和入口 |
| `Panel.qml` | 原生面板入口 |
| `install.sh` | 用户级后端与插件安装器 |
| `src/omarchy_workspaces/` | Python 标准库后端 |
| `docs/`、`README.md` | 安装、使用、排错及发布文档 |
| `tests/` | 自动化验证 |
| `reference/` | 引用的 Omarchy 参考源码与许可证 |

解压 ZIP 后的 `omarchy-workspaces/` 就是仓库根目录。不要再把这个目录整体放到远端仓库的一层子目录里，否则 `omarchy plugin add` 无法在仓库根目录找到 manifest。

`lambert.workspaces` 是稳定插件 ID；发布名称或仓库名可以不同，升级时保持 ID 不变。若开发另一个独立插件，应使用不同 ID，而不是覆盖它。

## 2. 发布前验证

在源码根目录运行：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/verify_qml.py
bash -n install.sh
```

在 Omarchy 4.0.4 桌面还要执行官方验证器，并实际验证面板：

```bash
omarchy-plugin-validate .
```

验证器检查 manifest 和文件结构，不证明 QML 能正常加载，也不证明真实应用身份正确。按 [INSTALL.md](INSTALL.md#10-安装后验收) 完成本机使用验收，再更新 [TEST-REPORT.md](../TEST-REPORT.md)；只记录实际运行结果。

检查源码中没有个人 `apps.toml`、日志、状态备份、令牌或私有路径。本项目原创源码使用 GPL-3.0-only；保留 `reference/` 中引用代码的来源和许可证；不要把第三方源码视为无来源自有代码。

## 3. 安装当前 GitHub 仓库

当前仓库地址为 `https://github.com/CoderLambert/omarchy-workspace-plugin.git`。Omarchy 原生命令直接克隆整个仓库，因此 manifest 所在层必须是仓库根；本仓库已按此结构组织。安装面板与后端：

```bash
omarchy plugin add https://github.com/CoderLambert/omarchy-workspace-plugin.git --enable
bash ~/.config/omarchy/plugins/lambert.workspaces/install.sh --backend-only
```

官方 `add` 会验证、克隆、登记并按参数启用；不会执行后端安装脚本。也可以在 GitHub 仓库选择 **Code → Download ZIP**，解压后在仓库根目录运行 `bash install.sh`，或下载仓库中的离线安装器。

`--backend-only` 补装命令和菜单，不触碰已克隆的插件目录或 Git 元数据。

## 4. 更新策略

当前版本为 `1.3.0-rc.2`，面板同时校验版本号和 Python 后端源码指纹。禁止用仅改版本字段的方式伪装同步。CI 运行于 PR / main，构建产物保存在 Actions artifacts；创建 RC / Stable Release 仍由维护者在检查验收清单后明确执行，工作流不会自动发布稳定版。


发布者同步更新 Python `__version__`、manifest、文档和更新记录，重新验证后发布相应提交或标签。

从 Git 安装的用户使用 Omarchy 原生更新，核对差异后执行。由于官方更新同步仓库文件，不负责复制 Python 后端到运行目录，更新后仍需在插件目录运行：

```bash
bash ~/.config/omarchy/plugins/lambert.workspaces/install.sh --backend-only
```

再执行 `omarchy-workspaces --version`，重新打开面板。界面与后端版本不一致时，优先完成此步骤。

本地 ZIP 安装用户则重新运行新包的 `bash install.sh --no-setup`，保留应用分配，自动刷新已启用规则，保留尚未应用的草稿。不要混用不同来源的旧包去覆盖新版本。

## 5. 构建离线分发包

在源码根目录：

```bash
python3 build_release.py /tmp/install-omarchy-workspaces.sh
python3 build_source.py /tmp/omarchy-workspaces-plugin-1.3.0-rc.2.zip
```

构建结果包括完整源码与文档的 ZIP，及嵌入载荷校验的单文件安装器。ZIP 内 `SHA256SUMS` 用于校验展开后的文件；验证后一起提供给使用者。

不要手工修改已打包载荷而不重新构建。版本升级时替换示例文件名中的版本，并更新记录。

## 6. 生命周期限制

官方 `plugin disable` / `plugin remove` 没有调用本工具的规则恢复钩子。发布页面应明确：

- 暂停工作区接管用 `omarchy-workspaces reset`。
- 撤销接管并卸载入口用 `omarchy-workspaces uninstall`；Git 插件目录会保留，再按输出执行原生 `plugin remove`。
- 仅禁用界面用 `omarchy plugin disable lambert.workspaces`，现有规则仍生效。

不要把“插件已移除”写成“原快捷键、应用入口和工作区规则都已恢复”。

`uninstall` 保留应用配置、后端副本和日志。安装器自己复制的未修改插件可直接移除；手工或有本地修改的目录保留供用户核对。

## 7. 官方协议依据

核对版本：Omarchy v4.0.4，日期：2026-10-12（Asia/Shanghai）。

- [Shell 插件说明](https://github.com/omacom/omarchy/blob/v4.0.4/docs/omarchy-shell.md)
- [Shell API 与 manifest](https://github.com/omacom/omarchy/blob/v4.0.4/shell/README.md)
- [插件添加命令](https://github.com/omacom/omarchy/blob/v4.0.4/bin/omarchy-plugin-add)
- [插件禁用命令](https://github.com/omacom/omarchy/blob/v4.0.4/bin/omarchy-plugin-disable)
- [插件移除命令](https://github.com/omacom/omarchy/blob/v4.0.4/bin/omarchy-plugin-remove)
