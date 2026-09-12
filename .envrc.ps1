# Load environment variables from .env file into PowerShell environment
# Usage: .\.envrc.ps1

$envFile = Join-Path $PSScriptRoot ".env"

if (Test-Path $envFile) {
    $vars = @()
    Get-Content $envFile | ForEach-Object {
        # Skip empty lines and comments
        if ($_ -match '^\s*$' -or $_ -match '^\s*#') {
            return
        }
        
        # Parse KEY=VALUE format
        if ($_ -match '^([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            
            # Remove surrounding quotes if present
            if ($value -match "^`"(.*)`"`$" -or $value -match "^'(.*)'$") {
                $value = $matches[1]
            }
            
            # Set environment variable
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
            $vars += $key
        }
    }
    Write-Host "Loaded $($vars.Count) variables: $($vars -join ', ')"
}
else {
    Write-Warning ".env file not found at $envFile"
}
