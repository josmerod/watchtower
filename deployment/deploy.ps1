# Deploy Watchtower to Unraid (Remote Build)
# Usage: ./deployment/deploy.ps1

$ServerIP = "REDACTED_LAN_IP"
$RemoteUser = "root"
$RemoteDir = "/tmp/watchtower_deploy"
$TarFileName = "watchtower_src.tar.gz"
$LocalTarPath = Join-Path $env:TEMP $TarFileName

Write-Host "1. Creating source archive at $LocalTarPath..." -ForegroundColor Cyan
# Explicitly list folders/files to include to avoid locking issues on venvs
tar -czf "$LocalTarPath" src deployment config utils Tests pyproject.toml uv.lock run_all_etl.sh run_watchtower_dashboard.py

if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create archive"; exit 1 }

Write-Host "2. Uploading archive to $ServerIP..." -ForegroundColor Cyan
Write-Host "   (You may be asked for password: REDACTED_PASSWORD)" -ForegroundColor Gray
scp "$LocalTarPath" "${RemoteUser}@${ServerIP}:/tmp/${TarFileName}"

if ($LASTEXITCODE -ne 0) { Write-Error "SCP failed"; exit 1 }

Write-Host "3. Building and Deploying on Remote Server..." -ForegroundColor Cyan
$RemoteScript = @"
set -e
echo '   -> Extracting...'
rm -rf $RemoteDir
mkdir -p $RemoteDir
tar -xzf /tmp/$TarFileName -C $RemoteDir

echo '   -> Building Docker Image...'
cd $RemoteDir
docker build -t watchtower -f deployment/Dockerfile .

echo '   -> Restarting Container...'
docker stop watchtower || true
docker rm watchtower || true

docker run -d \
  --name watchtower \
  --restart unless-stopped \
  -p 7777:7777 \
  -v /mnt/user/appdata/watchtower/data:/app/data \
  -v /mnt/user/appdata/watchtower/logs:/app/logs \
  -e TZ=Europe/Madrid \
  watchtower

echo '   -> Cleanup...'
rm -rf $RemoteDir /tmp/$TarFileName
echo '   -> Done!'
"@

ssh -t "${RemoteUser}@${ServerIP}" $RemoteScript

if ($LASTEXITCODE -eq 0) {
    Write-Host "Deployment Successful!" -ForegroundColor Green
    Write-Host "Dashboard available at http://${ServerIP}:7777" -ForegroundColor Green
    Remove-Item "$LocalTarPath"
} else {
    Write-Error "Remote deployment failed."
}
