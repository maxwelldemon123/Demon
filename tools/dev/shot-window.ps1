Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Dpi {
    [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr ctx);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
[void][Dpi]::SetProcessDpiAwarenessContext([IntPtr](-4))
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

$p = Get-Process demon -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $p) { Write-Output "demon not running"; exit 1 }
$h = $p.MainWindowHandle
$r = New-Object Dpi+RECT
[void][Dpi]::GetWindowRect($h, [ref]$r)
$w = $r.Right - $r.Left
$ht = $r.Bottom - $r.Top
Write-Output ("window physical: " + $w + "x" + $ht + " at " + $r.Left + "," + $r.Top)

$bmp = New-Object System.Drawing.Bitmap $w, $ht
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
[void][Dpi]::PrintWindow($h, $hdc, 2)
$g.ReleaseHdc($hdc)
$g.Dispose()
$out = 'E:\dshwork\Demon\dist\window-final.png'
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()

$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
Write-Output ("screen: " + $screen.Width + "x" + $screen.Height)
Write-Output ("saved: " + $out)
