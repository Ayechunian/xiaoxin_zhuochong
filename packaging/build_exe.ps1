$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$pythonPath = (Resolve-Path -LiteralPath (Join-Path $projectRoot "runtime\python.exe")).Path
$toolRoot = Join-Path $projectRoot ".build-tools"
$pyInstallerPackage = Join-Path $toolRoot "PyInstaller"

if (-not (Test-Path -LiteralPath $pyInstallerPackage)) {
    New-Item -ItemType Directory -Path $toolRoot -Force | Out-Null
    & $pythonPath -m pip install --target $toolRoot -r (Join-Path $projectRoot "requirements-build.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller 安装失败"
    }
}

& $pythonPath (Join-Path $PSScriptRoot "run_pyinstaller.py") $toolRoot
if ($LASTEXITCODE -ne 0) {
    throw "EXE 构建失败"
}

$result = Join-Path $projectRoot "release\小新桌宠.exe"
if (-not (Test-Path -LiteralPath $result)) {
    throw "构建完成但没有找到输出文件"
}
Get-Item -LiteralPath $result | Select-Object FullName, Length, LastWriteTime
