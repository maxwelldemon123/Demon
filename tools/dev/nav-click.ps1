Add-Type @"
using System;
using System.Runtime.InteropServices;
public class U4 {
  [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr c);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, IntPtr e);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [StructLayout(LayoutKind.Sequential)] public struct R { public int Left, Top, Right, Bottom; }
}
"@
[void][U4]::SetProcessDpiAwarenessContext([IntPtr](-4))
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Drawing

$AE = [System.Windows.Automation.AutomationElement]
$TS = [System.Windows.Automation.TreeScope]
$CT = [System.Windows.Automation.ControlType]

$p = Get-Process demon -ErrorAction SilentlyContinue | Select-Object -First 1
$h = $p.MainWindowHandle
[void][U4]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 400

$win = $AE::FromHandle($h)
$items = $win.FindAll($TS::Descendants, [System.Windows.Automation.PropertyCondition]::new($AE::ControlTypeProperty, $CT::ListItem))

function Capture($path) {
    $rect = New-Object U4+R
    [void][U4]::GetWindowRect($h, [ref]$rect)
    $w = $rect.Right - $rect.Left
    $ht = $rect.Bottom - $rect.Top
    $bmp = New-Object System.Drawing.Bitmap $w, $ht
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $hdc = $g.GetHdc()
    [void][U4]::PrintWindow($h, $hdc, 2)
    $g.ReleaseHdc($hdc)
    $g.Dispose()
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
}

foreach ($name in @('语音', '角色', '日志', '接口')) {
    $found = $null
    foreach ($i in $items) { if ($i.Current.Name -eq $name) { $found = $i; break } }
    if (-not $found) { Write-Output ("skip " + $name); continue }
    $r = $found.Current.BoundingRectangle
    $cx = [int]($r.X + $r.Width / 2)
    $cy = [int]($r.Y + $r.Height / 2)
    [void][U4]::SetCursorPos($cx, $cy)
    [U4]::mouse_event(0x0002, 0, 0, 0, [IntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [U4]::mouse_event(0x0004, 0, 0, 0, [IntPtr]::Zero)
    Start-Sleep -Milliseconds 900
    $file = 'E:\dshwork\Demon\dist\nav-' + $name + '.png'
    Capture $file
    Write-Output ("clicked " + $name + " at " + $cx + "," + $cy + " -> " + $file)
}
