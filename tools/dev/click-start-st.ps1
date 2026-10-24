Add-Type @"
using System;
using System.Runtime.InteropServices;
public class U5 {
  [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr c);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
}
"@
[void][U5]::SetProcessDpiAwarenessContext([IntPtr](-4))
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$AE = [System.Windows.Automation.AutomationElement]
$TS = [System.Windows.Automation.TreeScope]
$CT = [System.Windows.Automation.ControlType]

$p = Get-Process demon -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $p) { Write-Output 'demon not running'; exit 1 }
$h = $p.MainWindowHandle
[void][U5]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 400

$win = $AE::FromHandle($h)
# 切到“启动”页
$items = $win.FindAll($TS::Descendants, [System.Windows.Automation.PropertyCondition]::new($AE::ControlTypeProperty, $CT::ListItem))
foreach ($i in $items) {
    if ($i.Current.Name -eq '启动') {
        $r = $i.Current.BoundingRectangle
        # 用 SelectionItem 不可靠，改用真实点击
        Add-Type @"
using System;
using System.Runtime.InteropServices;
public class U6 {
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, IntPtr e);
}
"@ -ErrorAction SilentlyContinue
        [void][U6]::SetCursorPos([int]($r.X + $r.Width/2), [int]($r.Y + $r.Height/2))
        [U6]::mouse_event(0x0002,0,0,0,[IntPtr]::Zero)
        Start-Sleep -Milliseconds 80
        [U6]::mouse_event(0x0004,0,0,0,[IntPtr]::Zero)
        break
    }
}
Start-Sleep -Milliseconds 800

$buttons = $win.FindAll($TS::Descendants, [System.Windows.Automation.PropertyCondition]::new($AE::ControlTypeProperty, $CT::Button))
foreach ($b in $buttons) {
    if ($b.Current.Name -eq '启动酒馆') {
        Write-Output 'clicking 启动酒馆'
        $inv = $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
        $inv.Invoke()
        break
    }
}
