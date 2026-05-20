#!/bin/bash
# Deploy del frontend ERP — compila y reinicia el servicio.
# Requiere sudoers: /etc/sudoers.d/osserver-restart (creado 2026-05-20).
# Ver .agent/contextos/erp_frontend.md §Deploy.
set -e

cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/frontend/app

echo "▶ Compilando..."
quasar build

echo "▶ Reiniciando servicio..."
if ! sudo -n systemctl restart os-erp-frontend.service; then
  echo "ERROR: no se pudo reiniciar os-erp-frontend.service sin password."
  echo "       Configurar /etc/sudoers.d/osserver-restart (ver .agent/contextos/erp_frontend.md)."
  exit 1
fi

sleep 3
if ! systemctl is-active --quiet os-erp-frontend.service; then
  echo "ERROR: servicio no arrancó limpio"
  echo "       Revisar: sudo journalctl -u os-erp-frontend -n 30"
  exit 1
fi
echo "✅ Deploy completo — servicio activo — http://menu.oscomunidad.com"
