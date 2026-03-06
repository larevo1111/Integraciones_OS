#!/bin/bash
# export_all.sh
# Ejecuta todos los scripts de exportación de Effi en secuencia.
# Uso: bash export_all.sh

set -e

SCRIPTS=(
  export_clientes
  export_bodegas
  export_inventario
  export_trazabilidad
  export_ajustes_inventario
  export_traslados_inventario
  export_ordenes_compra
  export_facturas_compra
  export_remisiones_compra
  export_cotizaciones_ventas
  export_ordenes_venta
  export_facturas_venta
  export_notas_credito_venta
  export_remisiones_venta
  export_devoluciones_venta
  export_cuentas_por_pagar
  export_cuentas_por_cobrar
  export_comprobantes_ingreso
  export_guias_transporte
  export_produccion_encabezados
  export_produccion_reportes
)

OK=0
ERR=0
FAILED=()

echo "======================================"
echo " EXPORTACIÓN EFFI - $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================"

echo "🔄 Reiniciando contenedor playwright..."
docker restart playwright
sleep 5
echo "✅ Contenedor listo"
echo ""

for script in "${SCRIPTS[@]}"; do
  echo ""
  echo "▶ $script"
  if docker exec playwright node /repo/scripts/${script}.js; then
    OK=$((OK + 1))
  else
    echo "⚠️  Falló, reintentando en 15s..."
    sleep 15
    docker restart playwright > /dev/null 2>&1
    sleep 5
    if docker exec playwright node /repo/scripts/${script}.js; then
      echo "✅ Reintento exitoso"
      OK=$((OK + 1))
    else
      echo "❌ Falló definitivamente: $script"
      ERR=$((ERR + 1))
      FAILED+=("$script")
    fi
  fi
  sleep 8
done

echo ""
echo "======================================"
echo " RESULTADO: ✅ $OK ok  ❌ $ERR errores"
if [ ${#FAILED[@]} -gt 0 ]; then
  echo " Fallidos: ${FAILED[*]}"
fi
echo "======================================"
