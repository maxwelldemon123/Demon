# -*- coding: utf-8 -*-
"""更新使用说明与 DEVLOG（控制窗口）。"""

import io

ROOT = r"E:\dshwork\Demon"

# 使用说明：替换“二、启动”整段
path = f"{ROOT}\\dist\\Demon\\使用说明.txt"
txt = io.open(path, encoding="utf-8-sig").read()
old_start = txt.index("二、启动")
old_end = txt.index("三、让酒馆连上")
new_block = """二、启动
--------
1. 双击「启动Demon.bat」（或直接运行 demon.exe）
2. 会弹出一个「Demon」控制窗口，上面能看到：
   - 监听地址（http://127.0.0.1:8790）
   - 当前上游（哪个模型服务）
   - 对外模型名
   - 语音队列状态
   - 声线下拉框、自动朗读开关
   - 复制接口地址 / 打开日志 / 配置目录 / 重载配置 / 退出
3. 关掉这个窗口不会退出程序，它会缩到托盘继续跑。
   双击托盘里的 D 图标可以重新打开控制窗口。
4. Windows 11 默认把新图标收进折叠区：
   点任务栏右下角的 ^ 就能看到 D；想固定的话，
   设置 → 个性化 → 任务栏 → 其他系统托盘图标 → Demon → 打开。
5. 停止：控制窗口点「退出 Demon」，或双击「停止Demon.bat」。

"""
txt = txt[:old_start] + new_block + txt[old_end:]
io.open(path, "w", encoding="utf-8", newline="").write(txt)
print("[OK] 使用说明")

devlog = """
## 2026-10-24 · 控制窗口（解决“找不到托盘图标”）

### 背景
用户反馈看不到托盘内容。排查结论：进程与 explorer 同会话（Session 2），
托盘创建成功（日志 `系统托盘可用=是`），但 **Windows 11 把新图标默认放进折叠区**，
注册表 `NotifyIconSettings` 里也没有登记项。

### 改动
1. 新增 `ControlWindow`（Qt Widgets）：运行状态 / 声线切换 / 自动朗读开关 /
   复制接口地址 / 打开日志 / 配置目录 / 重载配置 / 退出。
2. 启动即显示控制窗口，托盘图标保留为快捷方式（双击重新打开窗口）。
3. 启动气泡提示：“右键托盘 D 图标…如果没看到，点任务栏 ^”。
4. 单实例检测（QSharedMemory）：重复双击不再弹“端口被占用”，
   而是提示“已经在运行”。
5. 端口占用文案补充“最常见原因是已经有一个 Demon 在运行”。

### 踩坑
- 无 DPI 感知的 PowerShell 里 `GetWindowRect` 返回的是**虚拟化坐标**（1.75 倍缩放），
  截出来的窗口总像被裁掉。用 `SetProcessDpiAwarenessContext(-4)` 后拿到真实尺寸
  （1214x624，屏幕 2560x1440），确认窗口完整。
- 窗口尺寸不能写死：固定 560 宽会裁掉按钮；最终用
  `layout()->setSizeConstraint(QLayout::SetMinimumSize)` 让布局决定最小尺寸。
"""

log = io.open(f"{ROOT}\\docs\\DEVLOG.md", encoding="utf-8").read()
if "控制窗口" not in log:
    io.open(f"{ROOT}\\docs\\DEVLOG.md", "a", encoding="utf-8", newline="").write(devlog)
    print("[OK] DEVLOG")
