# -*- coding: utf-8 -*-
"""记录托盘问题结论，更新使用说明。"""

import io

ROOT = r"E:\dshwork\Demon"

# 使用说明：把“关窗口不退出”改成“关窗口退出”
p = f"{ROOT}\\dist\\Demon\\使用说明.txt"
txt = io.open(p, encoding="utf-8-sig").read()
txt = txt.replace(
"""3. 关掉这个窗口不会退出程序，它会缩到托盘继续跑。
   双击托盘里的 D 图标可以重新打开控制窗口。
4. Windows 11 默认把新图标收进折叠区：
   点任务栏右下角的 ^ 就能看到 D；想固定的话，
   设置 → 个性化 → 任务栏 → 其他系统托盘图标 → Demon → 打开。
5. 停止：控制窗口点「退出 Demon」，或双击「停止Demon.bat」。""",
"""3. 关掉这个窗口 = 退出程序（不会留在后台）。
   停止也可以点「退出 Demon」按钮，或双击「停止Demon.bat」。
4. 关于托盘图标：这台 Win11 不注册第三方新托盘图标（实测连最小示例程序也
   没有位置、不进系统设置列表），所以托盘图标可能看不到。这不影响使用，
   所有操作都在控制窗口里。
5. 想快速启动：把 demon.exe 发送到桌面快捷方式，或把窗口固定到任务栏。""")
io.open(p, "w", encoding="utf-8", newline="").write(txt)
print("[OK] 使用说明")

devlog = """
## 2026-10-24 · 托盘图标问题定论

### 现象
- 用户看不到 Demon 托盘图标；Win11「其他系统托盘图标」列表里也没有 Demon。
- 程序侧日志：`isSystemTrayAvailable=是`、`isVisible=1`、`iconNull=0`，
  但 `geometry=0x0`。

### 对照实验
1. 写了一个 20 行最小 Qt 托盘程序（红色圆点）：
   `available=true visible=true geometry=0x0`，注册表 `NotifyIconSettings` 同样无记录。
2. 重启 Explorer 后重试：仍然无位置、无登记。

### 结论
**不是 Demon 的代码问题，是这台 Win11 不注册新的第三方托盘图标。**
（`HKCU\\Control Panel\\NotifyIconSettings` 里只有 Quark/WeGame/OneDrive 等既有条目，
新程序不会生成条目，因此也不会出现在设置页。）

### 应对
- 控制窗口作为主界面，启动即显示。
- 关闭窗口 = 退出程序（避免“看不见也关不掉”）。
- 托盘仍保留（万一以后系统恢复了能用），但不再作为唯一入口。
- 文档里说明：想快速启动就建桌面快捷方式或固定到任务栏。
"""

log = io.open(f"{ROOT}\\docs\\DEVLOG.md", encoding="utf-8").read()
if "托盘图标问题定论" not in log:
    io.open(f"{ROOT}\\docs\\DEVLOG.md", "a", encoding="utf-8", newline="").write(devlog)
    print("[OK] DEVLOG")

# 最终自检
print("done")
