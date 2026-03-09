#!/bin/bash
# export_all.sh
# Ejecuta todos los scripts de exportación de Effi en secuencia.
# Diseñado para correr DENTRO del contenedor playwright.
# Uso: bash /repo/scripts/export_all.sh

SCRIPTS=(
  export_clientes
  export_proveedores
  export_bodegas
  export_inventario
  export_trazabilidad
  export_ajustes_inventario
  export_traslados_inventario
  export_categorias_articulos
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
  export_costos_produccion
  export_tipos_egresos
  export_tipos_marketing
)

OK=0
ERR=0
FAILED=()

echo "======================================"
echo " EXPORTACIÓN EFFI - $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================"

for script in "${SCRIPTS[@]}"; do
  echo ""
  echo "▶ $script"
  if node /repo/scripts/${script}.js; then
    OK=$((OK + 1))
  else
    echo "⚠️  Falló, reintentando en 15s..."
    sleep 15
    if node /repo/scripts/${script}.js; then
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
