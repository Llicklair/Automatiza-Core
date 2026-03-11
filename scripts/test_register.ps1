$body = @{
    email = "demo@automatizapyme.com"
    password = "Demo1234!"
    full_name = "Demo Usuario"
    tenant = @{
        name = "Demo Empresa SL"
        nif = "B12345678"
    }
} | ConvertTo-Json

try {
    $r = Invoke-WebRequest -Uri "http://localhost:8080/api/v1/auth/register" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body `
        -UseBasicParsing
    Write-Host "STATUS: $($r.StatusCode)"
    Write-Host "BODY: $($r.Content)"
} catch {
    Write-Host "ERROR: $($_.Exception.Response.StatusCode)"
    $reader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
    Write-Host "DETAIL: $($reader.ReadToEnd())"
}
