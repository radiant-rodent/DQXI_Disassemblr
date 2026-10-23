# Install an ARMv6K-capable bare-metal toolchain for source replacement.
#
# This downloads the xPack ARM GNU toolchain into
#   %LOCALAPPDATA%\Programs\dqxi-tools
# and prints the compiler path. It does not modify the retail ROM.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File tools\setup_arm_toolchain.ps1

$ErrorActionPreference = "Stop"
$Version = "15.2.1-1.1"
$Dest = Join-Path $env:LOCALAPPDATA "Programs\dqxi-tools"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
$Zip = Join-Path $Dest "xpack-arm-none-eabi-gcc-$Version-win32-x64.zip"
$Url = "https://github.com/xpack-dev-tools/arm-none-eabi-gcc-xpack/releases/download/v$Version/xpack-arm-none-eabi-gcc-$Version-win32-x64.zip"

if (-not (Test-Path $Zip)) {
    Write-Host "Downloading $Url"
    Invoke-WebRequest -Uri $Url -OutFile $Zip
}
$Extract = Join-Path $Dest "xpack-arm-none-eabi-gcc-$Version"
if (-not (Test-Path $Extract)) {
    Write-Host "Extracting to $Extract"
    Expand-Archive -Path $Zip -DestinationPath $Dest -Force
}
$Exe = Join-Path $Extract "bin\arm-none-eabi-gcc.exe"
if (-not (Test-Path $Exe)) {
    throw "arm-none-eabi-gcc.exe not found under $Extract"
}
Write-Host "ARM toolchain ready: $Exe"
Write-Host "Add to PATH for this shell:"
Write-Host "  `$env:PATH = '$Extract\bin;' + `$env:PATH"
& $Exe --version | Select-Object -First 1
