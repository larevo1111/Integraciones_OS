#!/bin/bash
# Mantiene SSH jump tunnel desde el local → VPS Contabo → Hostinger MySQL.
# Expone MySQL Hostinger como 127.0.0.1:3313 localmente.
set -u
while true; do
  echo "[tunnel_hostinger] Abriendo 3313 → 109.106.250.195:3306 vía VPS"
  ssh -N \
    -o ExitOnForwardFailure=yes \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3 \
    -i /home/osserver/.ssh/sos_erp \
    -p 65002 \
    -J root@94.72.115.156 \
    -L 3313:127.0.0.1:3306 \
    u768061575@109.106.250.195
  echo "[tunnel_hostinger] Caído — reintento en 10s"
  sleep 10
done
