# 快捷键唤出应用时跟随工作区

- 日期：2026-10-13
- 分支：main
- 范围：受管窗口的工作区规则、激活行为与说明。

## 问题与实现

原生 Omarchy 快捷键会直接运行系统启动器，绕过插件的 launch 路径。旧规则以 silent 将新窗口放到默认工作区，用户停在原处，容易误以为启动失败。

src/omarchy_workspaces/hypr.py 的 Lua / 新式 conf / 旧式 v2 三种规则都改为普通 workspace 分配，并允许受管普通窗口的激活请求获得焦点。所有已登记应用统一适用；普通系统快捷键无需新增或替换。已有窗口通过受管入口继续按 focus / move 策略复用。排除 special 工作区的匹配条件保留，整理操作的静默移动逻辑未改变。

窗口规则能跟随新窗口和应用发出的激活请求；直接调用原程序是否复用已有窗口由应用决定。希望保证复用时，应使用插件受管入口或主动配置受管快捷键。

## 文件

- src/omarchy_workspaces/hypr.py：规则生成。
- tests/test_workspaces.py、tests/test_cli_integration.py：三种后端、特殊工作区排除、原快捷键保留、Lua 效果及失败回滚适配。
- README.md、README.zh-CN.md、docs/USAGE.md、CHANGELOG.md：说明原生启动与复用边界。
- install-omarchy-workspaces.sh、SHA256SUMS：更新发行载荷。

## 实际验证

- Python 全量回归：137 项通过。
- 本机 Hyprland 0.56.2：生成规则加载后 configerrors 为空。
- 本机已有浏览器：从工作区 2 经受管入口直接聚焦工作区 3；窗口数量没有增加。
- 本机原生 Alacritty：从工作区 3 启动仅运行短暂 sleep 的测试终端，自动聚焦默认工作区 2；测试窗口自行退出，并恢复原焦点。
- 本机面板/后端源码指纹一致，状态无问题。
- 插件清单、Shell 语法、ZIP/离线载荷、SHA256、git diff --check：提交前通过。

## 限制

没有逐一启动所有实际应用，也没有调用真实模型。没有实际执行 XWayland 激活或启动期间隐藏 scratchpad 的桌面验收；相关保护有回归覆盖。UI 代码与本机现有新版面板相同，本次只改变窗口行为。
