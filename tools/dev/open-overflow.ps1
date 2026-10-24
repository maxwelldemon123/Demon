Add-Type @"
using System;
using System.Runtime.InteropServices;
public class U {
  [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr c);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, IntPtr e);
}
"@
[void][U]::SetProcessDpiAwarenessContext([IntPtr](-4))
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

$AE = [System.Windows.Automation.AutomationElement]
$TS = [System.Windows.Automation.TreeScope]

$root = $AE::RootElement
$tray = $root.FindFirst($TS::Children, [System.Windows.Automation.PropertyCondition]::new($AE::ClassNameProperty, 'Shell_TrayWnd'))
$btn = $tray.FindFirst($TS::Descendants, [System.Windows.Automation.PropertyCondition]::new($AE::AutomationIdProperty, '1360'))
if (-not $btn) { Write-Output 'no overflow button'; exit 1 }
$r = $btn.Current.BoundingRectangle
$cx = [int]($r.X + $r.Width / 2)
$cy = [int]($r.Y + $r.Height / 2)
Write-Output ("click at " + $cx + "," + $cy)
[void][U]::SetCursorPos($cx, $cy)
[U]::mouse_event(0x0002, 0, 0, 0, [IntPtr]::Zero)
Start-Sleep -Milliseconds 150
[U]::mouse_event(0x0004, 0, 0, 0, [IntPtr]::Zero)
Start-Sleep -Milliseconds 1500

$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
$out = 'E:\dshwork\Demon\dist\overflow.png'
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Output ("saved " + $out)

$ov = $root.FindFirst($TS::Children, [System.Windows.Automation.PropertyCondition]::new($AE::ClassNameProperty, 'NotifyIconOverflowWindow'))
if ($ov) {
  $btnType = [System.Windows.Automation.PropertyCondition]::new($AE::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)
  $items = $ov.FindAll($TS::Descendants, $btnType)
  Write-Output ("overflow items: " + $items.Count)
  foreach ($i in $items) { Write-Output ("  [" + $i.Current.Name + "]") }
} else {
  Write-Output 'overflow window not found'
}