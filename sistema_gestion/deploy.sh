#!/bin/bash
# Deploy completo Sistema Gestión OS
# Garantiza build PWA + copia a api/public + validación + reinicio servicio
#
# Uso:  ./deploy.sh            (desde sistema_gestion/)
#       npm run deploy          (desde sistema_gestion/app/)

set -e  # cortar al primer error

SG_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$SG_DIR/app"
API_PUBLIC="$SG_DIR/api/public"
DIST_PWA="$APP_DIR/dist/pwa"

cd "$APP_DIR"

echo ">> [1/5] Build Quasar modo PWA (web + mobile + pwa)"
npx quasar build -m pwa

echo ""
echo ">> [2/5] Validando archivos críticos del build"
REQUIRED=("index.html" "sw.js" "manifest.json" "assets")
for f in "${REQUIRED[@]}"; do
  if [ ! -e "$DIST_PWA/$f" ]; then
    echo "ERROR: falta $DIST_PWA/$f — build incompleto"
    exit 1
  fi
done
WORKBOX=$(ls "$DIST_PWA"/workbox-*.js 2>/dev/null | head -1)
if [ -z "$WORKBOX" ]; then
  echo "ERROR: falta workbox-*.js — service worker no funcionará"
  exit 1
fi
echo "   OK - index.html, sw.js, manifest.json, workbox, assets/"

echo ""
echo ">> [3/5] Limpiando api/public y copiando build"
mkdir -p "$API_PUBLIC"
rm -rf "$API_PUBLIC"/assets "$API_PUBLIC"/icons "$API_PUBLIC"/index.html "$API_PUBLIC"/sw.js "$API_PUBLIC"/workbox-*.js "$API_PUBLIC"/manifest.json "$API_PUBLIC"/logo-os.png "$API_PUBLIC"/favicon.ico 2>/dev/null || true
cp -r "$DIST_PWA"/* "$API_PUBLIC"/

echo ""
echo ">> [4/5] Verificando deploy en api/public"
for f in "${REQUIRED[@]}"; do
  if [ ! -e "$API_PUBLIC/$f" ]; then
    echo "ERROR: $API_PUBLIC/$f no se copió"
    exit 1
  fi
done
INDEX_JS=$(grep -oE 'assets/index-[^"]+\.js' "$API_PUBLIC/index.html" | head -1)
echo "   OK - index.html referencia $INDEX_JS"

echo ""
echo ">> [5/5] Reiniciando os-gestion.service"
if sudo -n systemctl restart os-gestion.service 2>/dev/null; then
  sleep 1
  if systemctl is-active --quiet os-gestion.service; then
    echo "   OK - servicio activo"
  else
    echo "   WARNING - servicio no arrancó limpio, revisar con: sudo journalctl -u os-gestion -n 30"
    exit 1
  fi
else
  echo "   SKIP - sin permisos sudo sin password (los archivos ya están en su lugar, Express los toma al vuelo)"
fi

echo ""
echo "==========================================="
echo "  DEPLOY OK"
echo "  Build: $INDEX_JS"
echo "  Prod:  https://gestion.oscomunidad.com"
echo "==========================================="
