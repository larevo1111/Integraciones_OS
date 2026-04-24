#!/bin/bash
# Snapshot de inventario Effi: corre pipeline + guarda copia de zeffi_inventario
# Ejecución: bash scripts/inventario/snapshot_inventario.sh
#
# NOTA: este script es PARTE del pipeline (invoca orquestador.py). Por eso lee
# de effi_data local como excepción válida a la regla de MANIFESTO §8
# ("effi_data = intermediaria, solo el orquestador puede usarla").
# Otros scripts que NO son del pipeline deben consultar os_integracion en VPS.

set -e
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS

FECHA=$(date +%Y-%m-%d)
HORA=$(date +%H%M)
LOG="logs/pipeline.log"
SNAP_DIR="inventario/snapshots"
mkdir -p "$SNAP_DIR"

echo "[$(date)] === SNAPSHOT INVENTARIO — Inicio ===" >> "$LOG"

# 1. Correr pipeline completo
echo "[$(date)] Ejecutando pipeline..." >> "$LOG"
python3 scripts/orquestador.py --forzar >> "$LOG" 2>&1

# 2. Exportar zeffi_inventario completo a CSV
ARCHIVO="$SNAP_DIR/inventario_${FECHA}_${HORA}.csv"
# shellcheck disable=SC1091
set -a; . /home/osserver/Proyectos_Antigravity/Integraciones_OS/integracion_conexionesbd.env; set +a
mysql -u "$DB_LOCAL_USER" -p"$DB_LOCAL_PASS" -h "$DB_LOCAL_HOST" -P "$DB_LOCAL_PORT" effi_data -e "
  SELECT id, nombre, categoria, vigencia,
         REPLACE(stock_total_empresa, ',', '.') AS stock_total,
         REPLACE(costo_manual, ',', '.') AS costo_manual,
         REPLACE(stock_bodega_principal_sucursal_principal, ',', '.') AS stock_principal,
         REPLACE(stock_bodega_jenifer_sucursal_principal, ',', '.') AS stock_jenifer,
         REPLACE(stock_bodega_santiago_sucursal_principal, ',', '.') AS stock_santiago,
         REPLACE(stock_bodega_ricardo_sucursal_principal, ',', '.') AS stock_ricardo,
         REPLACE(stock_bodega_mercado_libre_sucursal_principal, ',', '.') AS stock_mercado_libre,
         REPLACE(stock_bodega_villa_de_aburra_sucursal_principal, ',', '.') AS stock_villa_aburra,
         REPLACE(stock_bodega_apica_sucursal_principal, ',', '.') AS stock_apica,
         REPLACE(stock_bodega_el_salvador_sucursal_principal, ',', '.') AS stock_el_salvador,
         REPLACE(stock_bodega_desarrollo_de_producto_sucursal_principal, ',', '.') AS stock_desarrollo,
         REPLACE(stock_bodega_productos_no_conformes_bod_ppal_sucursal_principal, ',', '.') AS stock_no_conformes
  FROM zeffi_inventario
  WHERE vigencia = 'Vigente'
  ORDER BY id
" 2>/dev/null > "$ARCHIVO"

LINEAS=$(wc -l < "$ARCHIVO")
echo "[$(date)] Snapshot guardado: $ARCHIVO ($LINEAS líneas)" >> "$LOG"
echo "[$(date)] === SNAPSHOT INVENTARIO — Completo ===" >> "$LOG"
