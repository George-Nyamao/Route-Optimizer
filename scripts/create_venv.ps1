<#
creates a reproducible venv for the Route-Optimizer project.
Usage:
  # Use the default system py launcher to find Python 3.11
  .\scripts\create_venv.ps1

  # Or provide an explicit Python executable path
  .\scripts\create_venv.ps1 -PythonExe "C:\\Path\\To\\Python311\\python.exe"
#>
param(
    [string]$PythonExe = "py -3.11"
)

Write-Host "Using Python executable: $PythonExe"

# Resolve the python command to an executable path
try {
    $pythonPath = & $PythonExe -c "import sys; print(sys.executable)" 2>$null
} catch {
    Write-Error "Failed to run the provided Python executable. Ensure Python 3.11 is installed and $PythonExe is valid."
    exit 1
}

Write-Host "Resolved python path: $pythonPath"

$venvDir = Join-Path -Path (Get-Location) -ChildPath "map_env"

if (Test-Path $venvDir) {
    Write-Host "Removing existing venv at $venvDir"
    Remove-Item -Recurse -Force $venvDir
}

Write-Host "Creating virtual environment at $venvDir"
& $pythonPath -m venv $venvDir

Write-Host "Activating venv and upgrading installer tooling"
$activateScript = Join-Path $venvDir "Scripts/Activate.ps1"
if (-Not (Test-Path $activateScript)) {
    Write-Error "Activation script not found at $activateScript"
    exit 1
}

# Use the venv python to upgrade pip/setuptools/wheel and install requirements
$venvPython = Join-Path $venvDir "Scripts/python.exe"
& $venvPython -m pip install -U pip setuptools wheel
& $venvPython -m pip install -r .\requirements.txt

Write-Host "Virtual environment created and dependencies installed. To activate run:"
Write-Host "  .\map_env\Scripts\Activate.ps1"

exit 0
