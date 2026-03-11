#!/bin/bash
# Deploy del frontend ERP — compila y reinicia el servicio
set -e

cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/frontend/app

echo "▶ Compilando..."
quasar build

echo "▶ Reiniciando servicio..."
sudo systemctl restart os-erp-frontend

sleep 3
STATUS=$(systemctl is-active os-erp-frontend)
echo "✅ Deploy completo — servicio: $STATUS — http://menu.oscomunidad.com"
