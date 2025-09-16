<#
run_streamlit.ps1

Activates the project's virtual environment (PowerShell) and runs Streamlit.

Usage: In PowerShell, from the project root:
    .\run_streamlit.ps1

#>
param(
    [int]$Port = 8000,
    [string]$Address = '0.0.0.0'
)

Write-Host "Activating venv from .\.venv\Scripts\Activate.ps1 (if present)"
if (Test-Path -Path .\.venv\Scripts\Activate.ps1) {
    . .\.venv\Scripts\Activate.ps1
} else {
    Write-Warning "Virtual environment activation script not found at .\.venv\Scripts\Activate.ps1. Make sure your venv is created and activated manually.";
}

Write-Host "Running Streamlit on http://$Address`:$Port"
python -m streamlit run app/streamlit_app.py --server.port=$Port --server.address=$Address
