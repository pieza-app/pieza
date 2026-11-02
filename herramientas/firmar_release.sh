#!/usr/bin/env bash
# Firma y publica el Release BORRADOR de una app con actualizaciones firmadas (pieza «actualizaciones»). Corre en el Mac de quien
# mantiene la app, el único lugar donde está la llave privada (en el Llavero; ver herramientas/firmar/firmar.swift).
#   bash herramientas/firmar_release.sh <dueño/repo> <vX.Y.Z> <id>
# 1. Busca el borrador vX.Y.Z del repo (lo crea publicar.yml cuando app.json → actualizaciones.llaves tiene llaves).
# 2. Baja sus archivos a una carpeta temporal y revisa cada uno con su .sha256 (si falta o no calza, para).
# 3. Firma cada archivo (`<id>-actualizacion|X.Y.Z|<sha256>`), comprueba la firma y sube los .sig.
# 4. Te muestra lo que queda y, con tu sí, lo publica como la última versión (deja de ser borrador).
# Necesita gh (con sesión: gh auth login) y swift (Xcode o sus herramientas de línea de comandos).
set -euo pipefail
[ $# -eq 3 ] || { echo "Uso: bash herramientas/firmar_release.sh <dueño/repo> <vX.Y.Z> <id>" >&2; exit 2; }
REPO="$1"; TAG="$2"; APP="$3"
[[ "$REPO" =~ ^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$ ]] || { echo "«$REPO» no es dueño/repo." >&2; exit 2; }
[[ "$TAG" =~ ^v[0-9]{1,6}(\.[0-9]{1,6}){1,3}$ ]] || { echo "«$TAG» no es una versión vX.Y.Z." >&2; exit 2; }
[[ "$APP" =~ ^[a-z0-9][a-z0-9._-]{0,60}$ ]] || { echo "«$APP» no es el id de la app (el «id» de app.json)." >&2; exit 2; }
for c in gh swift shasum; do command -v "$c" >/dev/null || { echo "Falta $c." >&2; exit 1; }; done
VERSION="${TAG#v}"
FIRMAR="$(cd "$(dirname "$0")" && pwd)/firmar/firmar.swift"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# La llave tiene que estar (mejor saberlo antes de bajar nada).
PUBLICA="$(swift "$FIRMAR" publica "$APP")"
echo "Llave de $APP: $PUBLICA"

ID="$(gh api --paginate "repos/$REPO/releases?per_page=100" --jq ".[] | select(.draft and .tag_name == \"$TAG\") | .id")"
[[ "$ID" =~ ^[0-9]+$ ]] || { echo "No encontré un borrador $TAG en $REPO (¿ya está publicado, o publicar.yml no terminó?)." >&2; exit 1; }

# Los archivos del borrador (un borrador no se baja por su URL pública: va por la API, con tu sesión).
ARCHIVOS=()
while read -r AID NOMBRE; do
  [[ "$AID" =~ ^[0-9]+$ && "$NOMBRE" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "Archivo con un nombre raro en el Release: $NOMBRE" >&2; exit 1; }
  case "$NOMBRE" in *.sig) continue ;; esac
  gh api -H "Accept: application/octet-stream" "repos/$REPO/releases/assets/$AID" > "$TMP/$NOMBRE"
  case "$NOMBRE" in *.sha256) ;; *) ARCHIVOS+=("$NOMBRE") ;; esac
done < <(gh api --paginate "repos/$REPO/releases/$ID/assets?per_page=100" --jq '.[] | "\(.id) \(.name)"')
[ ${#ARCHIVOS[@]} -gt 0 ] || { echo "El borrador no tiene archivos." >&2; exit 1; }

cd "$TMP"
for f in "${ARCHIVOS[@]}"; do
  [ -f "$f.sha256" ] || { echo "Falta $f.sha256: no firmo algo que GitHub no dice qué es." >&2; exit 1; }
  ESPERADA="$(cut -d' ' -f1 "$f.sha256" | tr 'A-F' 'a-f')"
  [ ${#ESPERADA} -eq 64 ] && [ "$(shasum -a 256 "$f" | cut -d' ' -f1)" = "$ESPERADA" ] || { echo "$f no calza con su .sha256." >&2; exit 1; }
  swift "$FIRMAR" firmar "$APP" "$VERSION" "$f"
  swift "$FIRMAR" verificar "$APP" "$VERSION" "$f" "$PUBLICA" >/dev/null
done
for f in "${ARCHIVOS[@]}"; do gh release upload "$TAG" "$f.sig" --repo "$REPO" --clobber; done

echo
echo "Firmados en $REPO $TAG:"; printf '  %s (+ .sha256 y .sig)\n' "${ARCHIVOS[@]}"
printf '¿Publicarlo ahora como la última versión? Las apps instaladas lo verán en unas horas. Escribe «sí»: '
read -r RESPUESTA
[ "$RESPUESTA" = "sí" ] || [ "$RESPUESTA" = "si" ] || { echo "Queda como borrador (firmado). Vuelve a correr esto para publicarlo."; exit 0; }
gh api -X PATCH "repos/$REPO/releases/$ID" -F draft=false -f make_latest=true --jq .html_url
