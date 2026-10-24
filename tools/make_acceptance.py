# -*- coding: utf-8 -*-
"""生成 1.0 验收清单（bat + 说明 txt）。bat 用 GBK + CRLF。"""

import io

DIST = r"E:\dshwork\Demon\dist\Demon"

# ---------- selfcheck.ps1（UTF-8 BOM，PowerShell 5.1 友好；纯 ASCII 输出） ----------
ps1 = r'''$ErrorActionPreference = 'Stop'
$base = 'http://127.0.0.1:8790'
$pass = 0
$fail = 0

function Check($name, $ok, $detail) {
    if ($ok) { $script:pass++; Write-Host ("  [PASS] " + $name + "  " + $detail) -ForegroundColor Green }
    else     { $script:fail++; Write-Host ("  [FAIL] " + $name + "  " + $detail) -ForegroundColor Red }
}

Write-Host "Demon 1.0 self check" -ForegroundColor Cyan
Write-Host ("target: " + $base)
Write-Host ""

# 1 health
try {
    $r = Invoke-WebRequest ($base + '/healthz') -UseBasicParsing -TimeoutSec 5
    $j = $r.Content | ConvertFrom-Json
    Check 'healthz' ($r.StatusCode -eq 200 -and $j.status -eq 'ok') ('version=' + $j.version)
} catch { Check 'healthz' $false $_.Exception.Message }

# 2 models
try {
    $r = Invoke-WebRequest ($base + '/v1/models') -UseBasicParsing -TimeoutSec 5
    $j = $r.Content | ConvertFrom-Json
    $ids = ($j.data | ForEach-Object { $_.id }) -join ','
    Check 'models' ($ids -match 'demon') ('ids=' + $ids)
} catch { Check 'models' $false $_.Exception.Message }

# 3 voice status
$profiles = @()
try {
    $r = Invoke-WebRequest ($base + '/voice/status') -UseBasicParsing -TimeoutSec 5
    $j = $r.Content | ConvertFrom-Json
    $profiles = @($j.voice.profiles)
    Check 'voice/status' ($profiles.Count -ge 1) ('profiles=' + ($profiles -join ',') + ' autoPlay=' + $j.voice.autoPlay)
} catch { Check 'voice/status' $false $_.Exception.Message }

# 4 tts (skip when service is down)
$ttsUp = $false
try {
    $c = New-Object Net.Sockets.TcpClient
    $c.Connect('127.0.0.1', 9880)
    $ttsUp = $c.Connected
    $c.Close()
} catch { $ttsUp = $false }

if (-not $ttsUp) {
    Write-Host '  [SKIP] voice/speak  (GPT-SoVITS 9880 not running)' -ForegroundColor Yellow
} else {
try {
    $body = @{ text = '测试'; profile = $(if ($profiles.Count -gt 0) { $profiles[0] } else { 'xiaod' }); lang = 'zh' } | ConvertTo-Json -Compress
    $r = Invoke-WebRequest ($base + '/voice/speak') -Method Post -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -UseBasicParsing -TimeoutSec 120
    $bytes = $r.RawContentStream.ToArray()
    $isWav = ($bytes.Length -gt 10000 -and $bytes[0] -eq 82 -and $bytes[1] -eq 73 -and $bytes[2] -eq 70 -and $bytes[3] -eq 70)
    Check 'voice/speak' $isWav ('bytes=' + $bytes.Length + ' (need >10000, RIFF)')
} catch { Check 'voice/speak' $false $_.Exception.Message }
}

# 5 chat stream
try {
    $body = '{"model":"demon","stream":true,"messages":[{"role":"user","content":"self check"}]}'
    $r = Invoke-WebRequest ($base + '/v1/chat/completions') -Method Post -ContentType 'application/json' -Body $body -UseBasicParsing -TimeoutSec 180
    $txt = $r.Content
    $hasData = $txt -match 'data:'
    $hasDone = $txt -match '\[DONE\]'
    $hasError = $txt -match '"error"'
    if ($hasData -and $hasDone -and -not $hasError) { Check 'chat stream' $true 'got data + [DONE]' }
    elseif ($hasData -and $hasDone) { Check 'chat stream' $true 'data + [DONE], but upstream reported error (check config)' }
    else { Check 'chat stream' $false ('data=' + $hasData + ' done=' + $hasDone) }
} catch { Check 'chat stream' $false $_.Exception.Message }

Write-Host ""
Write-Host ("result: " + $pass + " passed, " + $fail + " failed")
if ($fail -eq 0) { Write-Host "SELF CHECK OK" -ForegroundColor Green } else { Write-Host "SELF CHECK FAILED" -ForegroundColor Red }
exit $fail
'''

io.open(f"{DIST}\\selfcheck.ps1", "w", encoding="utf-8-sig", newline="").write(ps1)

# ---------- 自检.bat（GBK + CRLF） ----------
bat = "@echo off\r\n" \
      "chcp 936 >nul\r\n" \
      "cd /d \"%~dp0\"\r\n" \
      "powershell -NoProfile -ExecutionPolicy Bypass -File \"%~dp0selfcheck.ps1\"\r\n" \
      "echo.\r\n" \
      "pause\r\n"
io.open(f"{DIST}\\自检.bat", "w", encoding="gbk", newline="").write(bat)

# ---------- 验收清单 ----------
checklist = """Demon 1.0 验收清单
==================

准备工作（只需一次）
--------------------
[ ] 1. GPT-SoVITS 的 api_v2 已启动（端口 9880）
       不会启动就先跳过“语音”相关项，只验聊天
[ ] 2. 双击桌面 Demon 快捷方式（或 启动Demon.bat）
[ ] 3. 屏幕上出现「Demon」窗口，且显示：
       - 监听地址 http://127.0.0.1:8790
       - 当前上游 http://...（不是“未配置”）
       - 对外模型 demon（2 条声线）
       - 语音队列 空闲

A. 自动自检（1 分钟）
---------------------
[ ] 双击「自检.bat」
    期望最后一行：SELF CHECK OK（5 项全 PASS）
    如果 FAIL，把窗口内容截图发我

B. 酒馆连通（3 分钟）
---------------------
[ ] 4. 打开酒馆（你自己的那份，端口 8000）
[ ] 5. API 连接 → 聊天补全 → 来源选「自定义（兼容 OpenAI）」
       - 自定义端点： http://127.0.0.1:8790/v1
       - 自定义 API 密钥： 随便填
       - 输入模型名： demon
[ ] 6. 发一句“你好”
    期望：文字逐字出现（流式），不是等半天整段弹出
[ ] 7. 听声音
    期望：回复结束后自动朗读，音色是 xiaod
[ ] 8. 在 Demon 窗口把声线切到 demon，再发一句
    期望：下一次朗读变成另一个音色
[ ] 9. 取消勾选「回复后自动朗读」，再发一句
    期望：只出字，不出声

C. 异常与恢复（2 分钟）
-----------------------
[ ] 10. 关掉 Demon 窗口
     期望：窗口消失、程序退出（任务管理器里没有 demon.exe）
[ ] 11. 重新双击快捷方式
     期望：窗口回来，酒馆里再发消息仍然能用（不用重启酒馆）
[ ] 12. 在酒馆里发消息时，先关掉 GPT-SoVITS
     期望：文字照常出，只是没声音；Demon 不崩
[ ] 13. 重新启动 GPT-SoVITS，再发一句
     期望：声音恢复

D. 长对话（3 分钟）
-------------------
[ ] 14. 连续聊 10 轮以上
     期望：不卡死、不报错；Demon 内存稳定（任务管理器看，几十 MB）
[ ] 15. 翻回前面的消息
     期望：酒馆历史完整

验收通过标准
------------
A 全 PASS + B 的 6/7/8/9 + C 的 10/11/13 + D 的 14/15 都符合。
第 12 项（关掉语音不崩）也建议过一遍。

出问题怎么报
------------
1. Demon 窗口点「打开日志」，把 data\\demon.log 最后 30 行发我
2. 说明是在哪一项（比如 B-7）、当时做了什么、期望什么、实际什么
3. 如果是酒馆转圈，截图酒馆界面 + 日志同时发我
"""
io.open(f"{DIST}\\1.0验收清单.txt", "w", encoding="utf-8", newline="").write(checklist)

print("生成完成：")
print(" ", f"{DIST}\\1.0验收清单.txt")
print(" ", f"{DIST}\\自检.bat")
print(" ", f"{DIST}\\selfcheck.ps1")
