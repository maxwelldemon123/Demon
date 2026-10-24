Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$AE = [System.Windows.Automation.AutomationElement]
$root = $AE::RootElement
$kids = $root.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)
foreach ($k in $kids) {
  $n = $k.Current.Name
  if ($n -and $n -match 'SillyTavern|酒馆') { Write-Output ("[window] " + $n + "  class=" + $k.Current.ClassName) }
}
Write-Output "--- browsers ---"
Get-Process | Where-Object { $_.MainWindowTitle -match 'SillyTavern' } | ForEach-Object { Write-Output ($_.ProcessName + " : " + $_.MainWindowTitle) }