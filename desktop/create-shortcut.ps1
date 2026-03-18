$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("$env:USERPROFILE\Desktop\AutomatizaPyme.lnk")
$s.TargetPath = "$env:USERPROFILE\Desktop\atomatizacion de empresas\desktop\dist\win-unpacked\AutomatizaPyme.exe"
$s.WorkingDirectory = "$env:USERPROFILE\Desktop\atomatizacion de empresas\desktop\dist\win-unpacked"
$s.Description = "AutomatizaPyme - ERP para PYMEs"
$s.Save()
Write-Host "Shortcut created on Desktop pointing to win-unpacked"
