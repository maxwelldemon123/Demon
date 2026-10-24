Add-Type @"
using System;
using System.Runtime.InteropServices;
public class U2 {
  [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr c);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, IntPtr e);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [StructLayout(LayoutKind.Sequential)] public struct R { public int Left, Top, Right, Bottom; }
}
"@
[void][U2]::SetProcessDpiAwarenessContext([IntPtr](-4))
Add-Type -AssemblyName System.Drawing

$p = Get-Process demon -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $p) { Write-Output 'demon not running'; exit 1 }
$h = $p.MainWindowHandle
[void][U2]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 500

$rect = New-Object U2+R
[void][U2]::GetWindowRect($h, [ref]$rect)
Write-Output ("window: " + $rect.Left + "," + $rect.Top + " size " + ($rect.Right-$rect.Left) + "x" + ($rect.Bottom-$rect.Top))

$items = @(
    @{ name = 'status';  y = 162 },
    @{ name = 'api';     y = 228 },
    @{ name = 'launcher';y = 294 },
    @{ name = 'voice';   y = 360 },
    @{ name = 'chars';   y = 426 },
    @{ name = 'log';     y = 492 }
)

foreach ($it in $items) {
    $x = $rect.Left + 100
    $y = $rect.Top + [int]$it.y
    [void][U2]::SetCursorPos($x, $y)
    [U2]::mouse_event(0x0002, 0, 0, 0, [IntPtr]::Zero)
    Start-Sleep -Milliseconds 60
    [U2]::mouse_event(0x0004, 0, 0, 0, [IntPtr]::Zero)
    Start-Sleep -Milliseconds 700

    $w = $rect.Right - $rect.Left
    $ht = $rect.Bottom - $rect.Top
    $bmp = New-Object System.Drawing.Bitmap $w, $ht
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $hdc = $g.GetHdc()
    [void][U2]::PrintWindow($h, $hdc, 2)
    $g.ReleaseHdc($hdc)
    $g.Dispose()
    $out = 'E:\dshwork\Demon\dist\page-' + $it.name + '.png'
    $bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Output ("saved " + $out)
}
