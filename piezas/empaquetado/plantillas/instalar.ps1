# Instala (o actualiza) {{nombre}} en Windows con un solo comando (PowerShell):
#   irm https://raw.githubusercontent.com/{{repo}}/main/instalar.ps1 | iex
# Baja la última versión publicada en GitHub, verifica su huella SHA-256 y la instala solo para tu usuario
# (sin permisos de administrador). Tus datos quedan en tu computador y nunca se tocan.
# Generado por la pieza «empaquetado» de Pieza (MPL-2.0, https://mozilla.org/MPL/2.0/) desde app.json.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$repo = '{{repo}}'
function Falla($m) { Write-Host "x $m" -ForegroundColor Red; exit 1 }

if (-not [Environment]::Is64BitOperatingSystem) { Falla '{{nombre}} necesita Windows de 64 bits.' }
Write-Host 'Buscando la última versión de {{nombre}}…'
try { $rel = Invoke-RestMethod -Headers @{ Accept = 'application/vnd.github+json' } "https://api.github.com/repos/$repo/releases/latest" } catch { Falla 'No pude consultar GitHub.' }
$tag = $rel.tag_name
if (-not ($tag -match '^v\d+\.\d+\.\d+$')) { Falla 'No encontré una versión publicada.' }
$base = "https://github.com/$repo/releases/download/$tag"
$tmp = Join-Path $env:TEMP '{{id}}-instalar'
New-Item -ItemType Directory -Force $tmp | Out-Null
$exe = Join-Path $tmp '{{nombre_ascii}}-Windows.exe'
Write-Host "Descargando {{nombre}} $tag…"
try {
  Invoke-WebRequest "$base/{{nombre_ascii}}-Windows.exe" -OutFile $exe -UseBasicParsing
  Invoke-WebRequest "$base/{{nombre_ascii}}-Windows.exe.sha256" -OutFile "$exe.sha256" -UseBasicParsing
} catch { Falla 'Esta versión aún no tiene descarga para Windows.' }
$esperado = ((Get-Content "$exe.sha256" -Raw).Trim() -split '\s+')[0].ToLower()
$real = (Get-FileHash $exe -Algorithm SHA256).Hash.ToLower()
if ($real -ne $esperado) { Remove-Item $exe -Force; Falla 'La descarga no coincide con su huella. No instalé nada.' }
Write-Host 'v Descarga verificada' -ForegroundColor Green

# Instalador silencioso (por usuario); al terminar abre {{nombre}}.
Start-Process -FilePath $exe -ArgumentList '/S', '--force-run' -Wait
Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "v {{nombre}} $tag instalada. Se abrió: lo primero es elegir tu idioma." -ForegroundColor Green
