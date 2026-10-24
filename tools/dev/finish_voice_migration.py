# -*- coding: utf-8 -*-
"""收尾：酒馆插件残留清理脚本 + 文档更新。"""

import io, os

DIST = r"E:\dshwork\Demon\dist\Demon"
ROOT = r"E:\dshwork\Demon"

ps1 = r'''$ErrorActionPreference = 'Stop'
$stPath = 'C:\mylove\SillyTavern\data\default-user\settings.json'
$backupDir = 'E:\dshwork\st-gptsovits5-voice\_st-backup'

$listening = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($listening) {
    Write-Host "SillyTavern is running (port 8000)." -ForegroundColor Yellow
    Write-Host "Close SillyTavern first, then run this again." -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path $stPath)) { Write-Host "settings.json not found"; exit 1 }

New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
Copy-Item $stPath (Join-Path $backupDir ("settings-" + $stamp + ".json")) -Force

$raw = Get-Content $stPath -Raw -Encoding UTF8
$cfg = $raw | ConvertFrom-Json
if ($cfg.extension_settings.PSObject.Properties.Name -contains 'gptsovits5_voice') {
    $cfg.extension_settings.PSObject.Properties.Remove('gptsovits5_voice')
    ($cfg | ConvertTo-Json -Depth 100 -Compress) | Set-Content $stPath -Encoding UTF8 -NoNewline
    Write-Host "Removed gptsovits5_voice from settings.json" -ForegroundColor Green
} else {
    Write-Host "gptsovits5_voice not present (already clean)" -ForegroundColor Green
}
'''

io.open(f"{DIST}\\clean-st-plugin.ps1", "w", encoding="utf-8-sig", newline="").write(ps1)

bat = "@echo off\r\n" \
      "chcp 936 >nul\r\n" \
      "powershell -NoProfile -ExecutionPolicy Bypass -File \"%~dp0clean-st-plugin.ps1\"\r\n" \
      "echo.\r\n" \
      "pause\r\n"
io.open(f"{DIST}\\清理酒馆插件残留.bat", "w", encoding="gbk", newline="").write(bat)

# ---- 使用说明：补声线说明 ----
p = f"{DIST}\\使用说明.txt"
txt = io.open(p, encoding="utf-8-sig").read()
add = """
八、声线（从旧酒馆插件迁移）
------------------------------
Demon 现在自带 4 条声线，配置在 config.json 的 voiceProfiles：

  小d-柔软        小d · 柔软          （GPT e15 + SoVITS s400）
  demon-小恶魔    demon · 小恶魔       （GPT e15 + SoVITS s368）
  小d-柔软-泛化    小d · 柔软(泛化)     （GPT e10 + SoVITS s400）
  demon-小恶魔-2  demon · 小恶魔(泛化) （GPT e10 + SoVITS s368）

每条含：gptWeights / sovitsWeights / refAudio / promptText / promptLang。
合成前 Demon 会检查当前加载的权重，不一致就先调 set_gpt_weights 和
set_sovits_weights 切换（约 0.3~0.5 秒）。

参考音频已复制到 voices\\ 目录，不再依赖 GPT-SoVITS 的 refs 目录。
"""
if "八、声线" not in txt:
    txt += add
io.open(p, "w", encoding="utf-8", newline="").write(txt)
print("[OK] 使用说明")

# ---- DEVLOG ----
devlog = """
## 2026-10-24 · 音色档案从酒馆插件迁入 Demon

### 背景
用户要求：`st-gptsovits5-voice` 插件只保留音色档案并留存在 Demon，酒馆端删掉插件。

### 档案来源
插件配置存在酒馆 `settings.json` 的 `extension_settings.gptsovits5_voice`，
共 4 条档案（id / gptWeights / sovitsWeights / refAudio / promptText / promptLang）。

### 迁移动作
1. `VoiceProfileConfig` 增加 `name` / `gptWeights` / `sovitsWeights`。
2. `TtsClient::ensureWeights()`：合成前比对当前权重，不同则依次 GET
   `/set_gpt_weights?weights_path=...`、`/set_sovits_weights?weights_path=...`，
   成功后才合成；`/voice/speak` 与自动朗读都走这条路径。
3. 参考音频复制到 `dist\\Demon\\voices\\`，配置里用绝对路径（api_v2 的相对路径按它自己的 cwd 解析）。
4. 4 条档案写入 `config.json`，默认声线 `小d-柔软`。

### 酒馆端清理
- 检查 `public/scripts/extensions/third-party`、`plugins/`：**插件代码本来就不在了**。
- 删除 `settings.json` 里的 `gptsovits5_voice` 配置（先备份到
  `E:\\dshwork\\st-gptsovits5-voice\\_st-backup\\`）。
- 注意：酒馆当时正在运行（pid 20104），它下次保存设置时可能用内存里的旧配置覆盖；
  重启一次酒馆即可固定，或运行 `dist\\Demon\\清理酒馆插件残留.bat`。

### 实测
```
小d-柔软       -> 200  157 KB  3.5s
demon-小恶魔   -> 200  178 KB  3.2s
小d-柔软-泛化  -> 200  175 KB  2.7s
demon-小恶魔-2 -> 200  181 KB  2.7s
日志：权重已切换：...（每条切换 0.3~0.5 秒）
自检：5/5 PASS（profiles 显示 4 条）
```
"""

log = io.open(f"{ROOT}\\docs\\DEVLOG.md", encoding="utf-8").read()
if "音色档案从酒馆插件迁入" not in log:
    io.open(f"{ROOT}\\docs\\DEVLOG.md", "a", encoding="utf-8", newline="").write(devlog)
    print("[OK] DEVLOG")

print("done")
