$deadline = (Get-Date).AddMinutes(3)
while ((Get-Date) -lt $deadline) {
    $p = Start-Process -FilePath "docker" -ArgumentList "version" -NoNewWindow -PassThru
    if ($p.WaitForExit(10000) -and $p.ExitCode -eq 0) {
        Write-Output "DOCKER_READY"
        exit 0
    }
    try { $p.Kill() } catch {}
    Write-Output "waiting..."
    Start-Sleep -Seconds 5
}
Write-Output "DOCKER_TIMEOUT"
exit 1
