Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$AE = [System.Windows.Automation.AutomationElement]
$TS = [System.Windows.Automation.TreeScope]
$CT = [System.Windows.Automation.ControlType]

$root = $AE::RootElement
$trayCond = [System.Windows.Automation.PropertyCondition]::new($AE::ClassNameProperty, 'Shell_TrayWnd')
$tray = $root.FindFirst($TS::Children, $trayCond)
if (-not $tray) { Write-Output 'no taskbar'; exit 1 }

$btnCond = [System.Windows.Automation.PropertyCondition]::new($AE::AutomationIdProperty, '1360')
$overflowBtn = $tray.FindFirst($TS::Descendants, $btnCond)
if ($overflowBtn) {
    $invoke = $overflowBtn.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
    $invoke.Invoke()
    Start-Sleep -Milliseconds 900
    Write-Output 'overflow opened'
}

$ovCond = [System.Windows.Automation.PropertyCondition]::new($AE::ClassNameProperty, 'NotifyIconOverflowWindow')
$ov = $root.FindFirst($TS::Children, $ovCond)
if (-not $ov) { $ov = $root.FindFirst($TS::Descendants, $ovCond) }

if ($ov) {
    $btnType = [System.Windows.Automation.PropertyCondition]::new($AE::ControlTypeProperty, $CT::Button)
    $items = $ov.FindAll($TS::Descendants, $btnType)
    Write-Output ("overflow buttons: " + $items.Count)
    foreach ($i in $items) { Write-Output ("  - [" + $i.Current.Name + "]  " + $i.Current.ClassName) }
} else {
    Write-Output 'overflow window not found'
}

$trayBtns = $tray.FindAll($TS::Descendants, [System.Windows.Automation.PropertyCondition]::new($AE::ControlTypeProperty, $CT::Button))
Write-Output ("taskbar buttons: " + $trayBtns.Count)
foreach ($b in $trayBtns) {
    $n = $b.Current.Name
    if ($n) { Write-Output ("  - [" + $n + "]") }
}
