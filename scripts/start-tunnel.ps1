# Start a free, zero-config Cloudflare HTTPS Tunnel pointing to localhost:8000
param(
    [int]$Port = 8000
)

$CloudflaredPath = Join-Path $PSScriptRoot "cloudflared.exe"

if (-not (Test-Path $CloudflaredPath)) {
    Write-Host "Downloading cloudflared.exe..." -ForegroundColor Cyan
    curl.exe -L -o $CloudflaredPath https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
}

Write-Host "Starting Cloudflare Quick Tunnel on port $Port..." -ForegroundColor Green
Write-Host "Look for the public HTTPS URL ending in .trycloudflare.com below:" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop the tunnel.`n" -ForegroundColor DarkGray

& $CloudflaredPath tunnel --protocol http2 --edge-ip-version 4 --url "http://localhost:$Port"
