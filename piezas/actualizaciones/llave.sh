#!/bin/bash
# Pieza «actualizaciones»: crea el par de llaves Ed25519 para firmar las versiones de una app. Corre en tu computador.
#   bash llave.sh            → escribe llave-privada.pem (0600) aquí y muestra la llave pública para app.json
# La privada va SOLO al secreto ACTUALIZACIONES_LLAVE del entorno «publicar» del repo y a un respaldo tuyo (gestor de claves).
# Nunca la subas al repo. Para rotar: suma la nueva a app.json (hasta 2), publica, y después quita la vieja.
set -euo pipefail
umask 077
[ -e llave-privada.pem ] && { echo "Ya existe llave-privada.pem: no la piso."; exit 1; }
openssl genpkey -algorithm ed25519 -out llave-privada.pem
publica=$(openssl pkey -in llave-privada.pem -pubout -outform DER | tail -c 32 | base64)
echo
echo "Llave pública (va en app.json → \"actualizaciones\": {\"llaves\": [\"$publica\"]}):"
echo "  $publica"
echo
echo "Ahora:"
echo "  1. gh secret set ACTUALIZACIONES_LLAVE --env publicar < llave-privada.pem"
echo "  2. Guarda llave-privada.pem en tu gestor de claves y bórrala de aquí."
