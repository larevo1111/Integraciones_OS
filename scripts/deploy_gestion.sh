#!/bin/bash
# Deploy idempotente + verificado de Sistema Gestión OS al VPS.
#
# Qué hace:
#   1. Build del frontend Quasar (npm run build).
#   2. Verifica que el dist local contenga los archivos críticos.
#   3. Rsync del dist al VPS (sistema_gestion/api/public/).
#   4. Verifica que los archivos críticos quedaron en el VPS.
#   5. Git pull en el VPS (para tomar cambios de server.js/helpers).
#   6. systemctl restart os-gestion en el VPS.
#   7. Verifica que https://gestion.oscomunidad.com/ responde 200.
#   8. Verifica que /sw.js responde 200 (service worker presente).
#
# Si cualquier paso falla → exit 1 (no deja deploy a medias).
#
# Uso: bash scripts/deploy_gestion.sh

set -euo pipefail

REPO="/home/osserver/Proyectos_Antigravity/Integraciones_OS"
APP_DIR="$REPO/sistema_gestion/app"
VPS_USER="osserver"
VPS_ROOT="root"
VPS_HOST="94.72.115.156"
VPS_REPO="/home/osserver/Proyectos_Antigravity/Integraciones_OS"
VPS_PUBLIC="$VPS_REPO/sistema_gestion/api/public"
URL_PROD="https://gestion.oscomunidad.com"

# Archivos mínimos que SIEMPRE deben quedar en public/ tras un build PWA
CRITICOS=(index.html sw.js manifest.json)

cd "$REPO"

echo "─── 1/7: Build frontend Quasar ───"
cd "$APP_DIR"
npm run build > /tmp/deploy_gestion_build.log 2>&1 || {
  echo "❌ Build falló. Ver /tmp/deploy_gestion_build.log"
  tail -20 /tmp/deploy_gestion_build.log
  exit 1
}

echo "─── 2/7: Verificar dist local ───"
DIST="$APP_DIR/dist/pwa"
for f in "${CRITICOS[@]}"; do
  if [ ! -f "$DIST/$f" ]; then
    echo "❌ Falta $DIST/$f tras el build"
    exit 1
  fi
done
# workbox-*.js es generado con hash, solo verificamos que exista al menos uno
ls "$DIST"/workbox-*.js > /dev/null 2>&1 || {
  echo "❌ Falta workbox-*.js en $DIST"
  exit 1
}
echo "   ✓ dist local OK"

echo "─── 3/7: Rsync al VPS ───"
rsync -az --delete "$DIST/" "$VPS_USER@$VPS_HOST:$VPS_PUBLIC/" > /tmp/deploy_gestion_rsync.log 2>&1 || {
  echo "❌ Rsync falló. Ver /tmp/deploy_gestion_rsync.log"
  tail -10 /tmp/deploy_gestion_rsync.log
  exit 1
}

echo "─── 4/7: Verificar archivos en VPS ───"
for f in "${CRITICOS[@]}"; do
  if ! ssh "$VPS_USER@$VPS_HOST" "test -f $VPS_PUBLIC/$f"; then
    echo "❌ $f NO quedó en VPS tras rsync"
    exit 1
  fi
done
ssh "$VPS_USER@$VPS_HOST" "ls $VPS_PUBLIC/workbox-*.js > /dev/null 2>&1" || {
  echo "❌ workbox-*.js NO quedó en VPS"
  exit 1
}
echo "   ✓ archivos críticos en VPS"

echo "─── 5/7: Git pull en VPS ───"
ssh "$VPS_USER@$VPS_HOST" "git -C $VPS_REPO pull --ff-only" || {
  echo "❌ git pull falló en VPS"
  exit 1
}

echo "─── 6/7: Restart os-gestion en VPS ───"
ssh "$VPS_ROOT@$VPS_HOST" "systemctl restart os-gestion && sleep 3" || {
  echo "❌ Restart os-gestion falló"
  exit 1
}
ssh "$VPS_ROOT@$VPS_HOST" "systemctl is-active os-gestion" | grep -q active || {
  echo "❌ os-gestion no está active tras restart"
  exit 1
}

echo "─── 7/7: Verificar URL pública ───"
HTTP_INDEX=$(curl -s -o /dev/null -w "%{http_code}" "$URL_PROD/" --max-time 15)
HTTP_SW=$(curl -s -o /dev/null -w "%{http_code}" "$URL_PROD/sw.js" --max-time 15)
if [ "$HTTP_INDEX" != "200" ] || [ "$HTTP_SW" != "200" ]; then
  echo "❌ URL pública no responde OK. index=$HTTP_INDEX sw.js=$HTTP_SW"
  exit 1
fi
echo "   ✓ $URL_PROD/      HTTP $HTTP_INDEX"
echo "   ✓ $URL_PROD/sw.js HTTP $HTTP_SW"

echo ""
echo "✅ Deploy completo y verificado."
