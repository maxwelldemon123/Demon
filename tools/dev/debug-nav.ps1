Add-Type @"
using System;
using System.Runtime.InteropServices;
public class U7 {
  [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr c);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, IntPtr e);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
}
"@
[void][U7]::SetProcessDpiAwarenessContext([IntPtr](-4))
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$AE = [System.Windows.Automation.AutomationElement]
$TS = [System.Windows.Automation.TreeScope]
$CT = [System.Windows.Automation.ControlType]

$p = Get-Process demon -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $p) { Write-Output 'NO DEMON'; exit 1 }
Write-Output ("handle=" + $p.MainWindowHandle + " title=" + $p.MainWindowTitle)
$h = $p.MainWindowHandle
if ($h -eq 0) { Write-Output 'NO WINDOW HANDLE'; exit 1 }
[void][U7]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 500

$win = $AE::FromHandle($h)
$items = $win.FindAll($TS::Descendants, [System.Windows.Automation.PropertyCondition]::new($AE::ControlTypeProperty, $CT::ListItem))
Write-Output ("nav items=" + $items.Count)
foreach ($i in $items) {
    Write-Output ("  item [" + $i.Current.Name + "]")
    if ($i.Current.Name -eq '启动') {
        $r = $i.Current.BoundingRectangle
        [void][U7]::SetCursorPos([int]($r.X + $r.Width/2), [int]($r.Y + $r.Height/2))
        [U7]::mouse_event(0x0002,0,0,0,[IntPtr]::Zero)
        Start-Sleep -Milliseconds 90
        [U7]::mouse_event(0x0004,0,0,0,[IntPtr]::Zero)
        Write-Output '  clicked launcher nav'
    }
}
Start-Sleep -Milliseconds 900

$buttons = $win.FindAll($TS::Descendants, [System.Windows.Automation.PropertyCondition]::new($AE::ControlTypeProperty, $CT::Button))
Write-Output ("buttons=" + $buttons.Count)
foreach ($b in $buttons) {
    $n = $b.Current.Name
    Write-Output ("  button [" + $n + "]")
    if ($n -eq '打开页面') {
        $inv = $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
        $inv.Invoke()
        Write-Output '  invoked 打开页面'
    }
}
