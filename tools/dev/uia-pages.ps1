Add-Type @"
using System;
using System.Runtime.InteropServices;
public class U3 {
  [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr c);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [StructLayout(LayoutKind.Sequential)] public struct R { public int Left, Top, Right, Bottom; }
}
"@
[void][U3]::SetProcessDpiAwarenessContext([IntPtr](-4))
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Drawing

$AE = [System.Windows.Automation.AutomationElement]
$TS = [System.Windows.Automation.TreeScope]
$CT = [System.Windows.Automation.ControlType]

$p = Get-Process demon -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $p) { Write-Output 'demon not running'; exit 1 }
$h = $p.MainWindowHandle
[void][U3]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 400

$win = $AE::FromHandle($h)
$items = $win.FindAll($TS::Descendants, [System.Windows.Automation.PropertyCondition]::new($AE::ControlTypeProperty, $CT::ListItem))
Write-Output ("list items: " + $items.Count)
foreach ($i in $items) { Write-Output ("  [" + $i.Current.Name + "]") }

$targets = @('语音', '角色', '日志')
foreach ($name in $targets) {
    $found = $null
    foreach ($i in $items) { if ($i.Current.Name -eq $name) { $found = $i; break } }
    if (-not $found) { Write-Output ("skip " + $name); continue }
    $sel = $found.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)
    $sel.Select()
    Start-Sleep -Milliseconds 800

    $rect = New-Object U3+R
    [void][U3]::GetWindowRect($h, [ref]$rect)
    $w = $rect.Right - $rect.Left
    $ht = $rect.Bottom - $rect.Top
    $bmp = New-Object System.Drawing.Bitmap $w, $ht
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $hdc = $g.GetHdc()
    [void][U3]::PrintWindow($h, $hdc, 2)
    $g.ReleaseHdc($hdc)
    $g.Dispose()
    $file = 'E:\dshwork\Demon\dist\page-' + $name + '.png'
    $bmp.Save($file, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Output ("saved " + $file)
}
