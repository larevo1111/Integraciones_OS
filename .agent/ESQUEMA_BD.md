# Esquema BD — effi_data (MariaDB)

> **Generado**: 2026-03-09 | **Tablas**: 39 | **Prefijo**: `zeffi_`
>
> Este archivo es el índice de referencia rápida para agentes.
> Se regenera automáticamente después de cada pipeline.
> **No consultar la BD para obtener estructura — leer este archivo.**

---

## Conexión rápida

```bash
mysql -u osadmin -pEpist2487. effi_data -e "TU_QUERY;" 2>/dev/null
```
Host: `127.0.0.1:3306` (host) · `172.18.0.1:3306` (Docker)
Todas las columnas son **TEXT** + `_pk` BIGINT AUTO_INCREMENT PK.

---

## Mapa de tablas por módulo

| Módulo | Tablas |
|---|---|
| **Clientes / Terceros** | `zeffi_clientes`, `zeffi_proveedores` |
| **Inventario** | `zeffi_inventario`, `zeffi_bodegas`, `zeffi_categorias_articulos`, `zeffi_ajustes_inventario`, `zeffi_traslados_inventario`, `zeffi_trazabilidad` |
| **Ventas** | `zeffi_facturas_venta_encabezados`, `zeffi_facturas_venta_detalle`, `zeffi_remisiones_venta_encabezados`, `zeffi_remisiones_venta_detalle`, `zeffi_ordenes_venta_encabezados`, `zeffi_ordenes_venta_detalle`, `zeffi_cotizaciones_ventas_encabezados`, `zeffi_cotizaciones_ventas_detalle`, `zeffi_notas_credito_venta_encabezados`, `zeffi_notas_credito_venta_detalle`, `zeffi_devoluciones_venta_encabezados`, `zeffi_devoluciones_venta_detalle` |
| **Compras** | `zeffi_facturas_compra_encabezados`, `zeffi_facturas_compra_detalle`, `zeffi_remisiones_compra_encabezados`, `zeffi_remisiones_compra_detalle`, `zeffi_ordenes_compra_encabezados`, `zeffi_ordenes_compra_detalle` |
| **Tesorería** | `zeffi_cuentas_por_cobrar`, `zeffi_cuentas_por_pagar`, `zeffi_comprobantes_ingreso_encabezados`, `zeffi_comprobantes_ingreso_detalle` |
| **Producción** | `zeffi_produccion_encabezados`, `zeffi_materiales`, `zeffi_articulos_producidos`, `zeffi_otros_costos`, `zeffi_costos_produccion`, `zeffi_cambios_estado` |
| **Logística** | `zeffi_guias_transporte` |
| **Config** | `zeffi_tipos_egresos`, `zeffi_tipos_marketing` |

---

## Relaciones clave

| Relación | Campo izquierdo | Campo derecho |
|---|---|---|
| Clientes ↔ Ventas | `zeffi_clientes.numero_de_identificacion` | `zeffi_facturas_venta_encabezados.id_cliente` |
| Clientes ↔ Remisiones | `zeffi_clientes.numero_de_identificacion` | `zeffi_remisiones_venta_encabezados.id_cliente` |
| Clientes ↔ Ordenes | `zeffi_clientes.numero_de_identificacion` | `zeffi_ordenes_venta_encabezados.id_cliente` |
| Encabezado ↔ Detalle | `*_encabezados.id_interno` o `id_orden` o `id_remision` | `*_detalle.id_interno` o `id_orden` o `id_remision` |
| Proveedores ↔ Compras | `zeffi_proveedores.numero_de_identificacion` | `zeffi_facturas_compra_encabezados.id_proveedor` |

---

## Detalle por tabla

### zeffi_clientes — ~462 filas
Maestro de clientes.
```
_pk | id_effi_tipo_de_identificacion | tipo_de_identificacion | numero_de_identificacion | nombre
telefono_1 | telefono_2 | celular | whatsapp | email | web | direcciones
pais | departamento | ciudad | id_effi_ciudad | direccion
fecha_de_nacimiento | genero | tipo_de_persona | regimen_tributario | tipo_de_cliente
tipo_de_marketing | tarifa_de_precios | actividad_economica_ciiu | forma_de_pago
descuento | cupo_de_credito_cxc | moneda_principal | sucursal | ruta_logistica
vendedor | responsable_asignado | fecha_ultima_venta | observacia_n | vigencia
fecha_de_creacion | responsable_de_creacion | fecha_de_modificacion | responsable_de_modificacion
fecha_de_anulacion | responsable_de_anulacion
```

---

### zeffi_proveedores — ~304 filas
Maestro de proveedores.
```
_pk | tipo_de_identificacion | numero_de_identificacion | nombre
telefono_1 | telefono_2 | celular | whatsapp | email | web | direcciones
pais | departamento | ciudad | codigo_dane_ciudad | direccion
fecha_de_nacimiento | tipo_de_persona | regimen_tributario | actividad_economica_ciiu
forma_de_pago | moneda_principal | sucursal | observacion | vigencia
fecha_de_creacion | responsable_de_creacion | fecha_de_modificacion | responsable_de_modificacion
fecha_de_anulacion | responsable_de_anulacion
```

---

### zeffi_inventario — ~488 filas
Snapshot de artículos con stock actual por bodega.
```
_pk | id | cod_barras | nombre | referencia | sucursal_principal | tipo_de_articulo
categoria | marca | valor_auxiliar | porcentaje_auxiliar | descripcion | url_imagen | url_video
vigencia | fecha_de_creacion | responsable_de_creacion | fecha_de_modificacion
costo_manual | costo_promedio | ultimo_costo | precio_minimo_de_venta | impuestos
precio_precio_publico_sugerido | precio_impuesto_precio_publico_sugerido
precio_precio_familiares_y_red_de_amigos | precio_impuesto_precio_familiares_y_red_de_amigos
precio_de_200_000_en_compras_y_miembros | precio_de_400_000_en_compras
precio_de_800_000_en_compras | precio_de_1_600_000_en_compras
gestion_de_stock | stock_minimo | stock_optimo | stock_total_empresa | stock_posible_combo
stock_bodega_principal_sucursal_principal | stock_bodega_villa_de_aburra_sucursal_principal
stock_bodega_apica_sucursal_principal | stock_bodega_el_salvador_sucursal_principal
[...14 columnas de stock por bodega...]
```

---

### zeffi_bodegas — ~15 filas
```
_pk | id | nombre_de_bodega | sucursal | vigencia
fecha_de_creacion | responsable_de_creacion | fecha_de_modificacion
responsable_de_modificacion | fecha_de_anulacion | responsable_de_anulacion
```

---

### zeffi_categorias_articulos — ~54 filas
```
_pk | id | nombre | vigencia
fecha_de_creacion | responsable_de_creacion | fecha_de_modificacion
responsable_de_modificacion | fecha_de_anulacion | responsable_de_anulacion
```

---

### zeffi_ajustes_inventario — ~356 filas
```
_pk | codigo | sucursal | bodega | articulos | vigencia
fecha_de_creacion | responsable_de_creacion
fecha_de_anulacion | responsable_de_anulacion
```

---

### zeffi_traslados_inventario — ~517 filas
```
_pk | codigo | sucursal_de_origen | bodega_de_origen
sucursal_de_destino | bodega_de_destino | articulos | observacion | vigencia
fecha_de_creacion | responsable_de_creacion | fecha_de_anulacion | responsable_de_anulacion
```

---

### zeffi_trazabilidad — ~63449 filas
La tabla más grande. Historial completo de movimientos de inventario.
```
_pk | id | id_articulo | articulo | descripcion | transaccion | tipo_de_movimiento
vigencia_de_transaccion | referencia_1 | sucursal | bodega | cantidad | costo | precio
fecha | responsable
```

---

### zeffi_facturas_venta_encabezados — ~824 filas
⚠️ Solo facturas **vigentes** (no histórico completo).
```
_pk | sucursal | centro_de_costos | id_interno | id_numeracion | cufe | bodega
cliente | id_cliente | telefono | pais | departamento | ciudad | direccion
vendedor | id_vendedor | tercero_multiproposito | id_tercero_multiproposito
total_bruto | descuentos | subtotal | impuestos | retenciones | propina_voluntaria | total_neto
formas_de_pago | lista_medios_de_pago | total_medios_de_pago_efectivo | total_medios_de_pago_banco
devoluciones_vigentes | costo_manual | utilidad_costo_manual | margen_de_utilidad_costo_manual
pdte_de_cobro | estado_cxc | dias_mora | valor_mora
fecha_de_entrega | estado_contable | observacion | garantia
fecha_de_creacion | responsable_de_creacion | fecha_de_anulacion | responsable_de_anulacion
guia_interna_de_transporte | guia_inicial_de_transportadora | estado_global_guia_inicial
distribuidor_dropshipping | convenio_dropshipping | estado_transaccion_de_dropshipping
```

---

### zeffi_facturas_venta_detalle — ~4940 filas
```
_pk | sucursal | centro_de_costos | bodega | id_interno | id_numeracion | cufe
cliente | id_cliente | telefono | email_cliente | marketing_cliente
categoria_articulo | marca_articulo | cod_articulo | descripcion_articulo
referencia | lote | serie | observacion_detalle | cantidad
costo_manual_unitario | costo_manual_total | costo_promedio_unitario | costo_promedio_total
precio_bruto_unitario | precio_bruto_total | descuento_unitario | descuento_total
impuesto_total | precio_neto_total | utilidad_total_costo_manual
total_bruto_factura | subtotal_factura | impuestos_factura | total_neto_factura
vendedor | id_vendedor | fecha_creacion_factura | vigencia_factura
```

---

### zeffi_remisiones_venta_encabezados — ~2176 filas
```
_pk | sucursal | centro_de_costos | id_remision | id_venta_ecommerce | bodega
cliente | id_cliente | telefono | pais | departamento | ciudad | direccion
vendedor | total_bruto | descuentos | subtotal | impuestos | retenciones | total_neto
devoluciones_vigentes | costo_manual | utilidad_costo_manual | margen_de_utilidad_costo_manual
pdte_de_cobro | estado_cxc | dias_mora | valor_mora
estado_remision | fecha_de_creacion | responsable_de_creacion
fecha_de_anulacion | responsable_de_anulacion
guia_interna_de_transporte | estado_global_guia_inicial
distribuidor_dropshipping | convenio_dropshipping
```

---

### zeffi_remisiones_venta_detalle — ~8313 filas
```
_pk | sucursal | centro_de_costos | bodega | id_remision
nombre_cliente | id_cliente | telefono_cliente | email_cliente | direccion_cliente
vendedor | id_vendedor | observacion | estado | vigencia | fecha_creacion
categoria_articulo | marca_articulo | cod_articulo | descripcion_articulo
referencia_articulo | lote | serie | cantidad
costo_manual_unitario | costo_manual_total | precio_bruto_unitario | precio_bruto_total
descuento_unitario | descuento_total | impuesto_total | precio_neto_total
id_interno_factura_de_venta_asociada | estado_cxc
guia_interna_de_transporte | estado_global_guia | valor_flete_guia
```

---

### zeffi_ordenes_venta_encabezados — ~698 filas
```
_pk | sucursal | centro_de_costos | id_orden | id_venta_ecommerce | ecommerce | bodega
nombre_cliente | id_cliente | telefono | pais | departamento | ciudad | direccion
vendedor | total_bruto | descuentos | subtotal | impuestos | retenciones | total_neto
observacion | vigencia | ultimo_estado | estado_facturacion
fecha_de_entrega | fecha_de_creacion | responsable_de_creacion
observacion_de_anulacion | fecha_de_anulacion | responsable_de_anulacion
```

**⚠️ SEMÁNTICA DE ESTADOS — TABLA DE CONSIGNACIÓN:**
| vigencia | estado_facturacion | Significado | n (2026-03-13) |
|---|---|---|---|
| `Vigente` | `Pendiente` | **Consignación activa** — mercancía en calle | 13 |
| `Anulada` | `Pendiente` | OV anulada sin venta — errores, devoluciones | 462 |
| `Anulada` | `Remisionada` | OV convertida a remisión — venta consolidada | 223 |

**Filtro correcto para consignación activa: `WHERE vigencia = 'Vigente'`**
NUNCA filtrar solo por `ultimo_estado + estado_facturacion` — devuelve filas cerradas.
Verificación 2026-03-13: 13 vigentes, total_bruto=$7.380.375, total_neto=$7.763.832 (diff=IVA $383.457)

---

### zeffi_ordenes_venta_detalle — ~6986 filas
```
_pk | sucursal | centro_de_costos | bodega | id_orden | ultimo_estado_orden_de_venta
estado_facturacion | cliente | id_cliente | telefono | email_cliente
categoria_articulo | marca_articulo | cod_articulo | descripcion_original | descripcion_en_factura
referencia | lote | serie | cantidad | precio_unitario | descuentos | impuestos | total_neto
vendedor | id_vendedor | observacion_orden | vigencia | fecha_orden
```

---

### zeffi_cotizaciones_ventas_encabezados — ~1006 filas
```
_pk | sucursal | centro_de_costos | id_cotizacion | bodega | cliente | id_cliente
telefono | pais | departamento | ciudad | direccion | vendedor
total_bruto | descuentos | subtotal | impuestos | retenciones | total_neto
estado_cotizacion | observacion | estado | fecha_de_entrega
fecha_de_creacion | responsable_de_creacion | fecha_de_anulacion | responsable_de_anulacion
```

---

### zeffi_cotizaciones_ventas_detalle — ~6565 filas
```
_pk | sucursal | centro_de_costos | bodega | id_cotizacion | cliente | id_cliente
cantidad | cod_articulo | descripcion_articulo | referencia | lote | serie
precio_unitario | precio_unitario_impuesto | vendedor | id_vendedor
fecha_de_entrega | vigencia | fecha_factura
[6 columnas de tarifas de precio...]
```

---

### zeffi_notas_credito_venta_encabezados — ~89 filas
```
_pk | sucursal | centro_de_costos | bodega | id_interno | id_numeracion
tipo_de_documento_de_venta | id_documento_de_venta | cude | vendedor_documento_de_venta
cliente | id_cliente | telefono | pais | departamento | ciudad | direccion
total_bruto | descuentos | subtotal | impuestos | retenciones | total_neto
pdte_de_pago | estado_cxp | dias_vencido | valor_vencido
fecha_de_devolucion | fecha_de_creacion | fecha_de_anulacion
```

---

### zeffi_notas_credito_venta_detalle — ~275 filas
```
_pk | sucursal | centro_de_costos | bodega | id_nota_credito
tipo_de_documento_de_venta | id_documento_de_venta | cliente | id_cliente
categoria_articulo | marca_articulo | cod_articulo | descripcion_original
referencia | lote | serie | cantidad
precio_bruto_unitario | precio_bruto_total | descuento_unitario | descuento_total
impuesto_total | precio_neto_total | vigencia | fecha_factura
```

---

### zeffi_devoluciones_venta_encabezados — ~27 filas
```
_pk | sucursal | centro_de_costos | id_devolucion | bodega | cliente | id_cliente
telefono | pais | departamento | ciudad | direccion | remision_de_venta_asociada
total_bruto | descuentos | subtotal | impuestos | retenciones | total_neto
pdte_de_pago | estado_cxp | dias_vencido | valor_vencido
fecha_de_devolucion | fecha_de_creacion | fecha_de_anulacion
```

---

### zeffi_devoluciones_venta_detalle — ~53 filas
```
_pk | sucursal | centro_de_costos | bodega | id_devolucion | cliente | id_cliente
categoria_articulo | marca_articulo | cod_articulo | descripcion_original
referencia | lote | serie | cantidad
costo_manual_unitario | costo_manual_total | precio_bruto_unitario | precio_bruto_total
descuento_unitario | descuento_total | impuesto_total | precio_neto_total
vigencia | fecha_remision
```

---

### zeffi_facturas_compra_encabezados — ~110 filas
```
_pk | sucursal | centro_de_costos | id_interno | id_numeracion | bodega
proveedor | id_proveedor | telefono | pais | departamento | ciudad | direccion
factura_del_proveedor | autorizacion
total_bruto | descuentos | subtotal | impuestos | retenciones | total_neto
fecha_de_compra | formas_de_pago | pdte_de_pago | estado_cxp | dias_vencido | valor_vencido
estado_contable | observacion | fecha_de_creacion | fecha_de_anulacion
```

---

### zeffi_facturas_compra_detalle — ~262 filas
```
_pk | sucursal | centro_de_costos | bodega | id_factura | proveedor | factura_proveedor
cod_articulo | id_tipo_de_egreso | descripcion_articulo | referencia | lote | serie
cantidad | precio_bruto_unitario | precio_bruto_total | descuento_unitario | descuento_total
impuesto_total | precio_neto_total | vigencia | fecha_compra | fecha_factura
```

---

### zeffi_remisiones_compra_encabezados — ~220 filas
```
_pk | sucursal | centro_de_costos | id_remision | bodega | proveedor | id_proveedor
telefono | pais | departamento | ciudad | direccion | remision_del_proveedor
total_bruto | descuentos | subtotal | impuestos | retenciones | total_neto
fecha_de_compra | pdte_de_pago | estado_cxp | dias_vencido | valor_vencido
estado_remision | fecha_de_creacion | fecha_de_anulacion
```

---

### zeffi_remisiones_compra_detalle — ~569 filas
```
_pk | sucursal | centro_de_costos | bodega | id_remision | proveedor | remision_proveedor
cantidad | cod_articulo | descripcion_articulo | referencia | lote | serie
precio_unitario | observacion_remision | vigencia | fecha_compra | fecha_remision
```

---

### zeffi_ordenes_compra_encabezados — ~85 filas
```
_pk | sucursal | centro_de_costos | id_orden | bodega | proveedor | id_proveedor
telefono | pais | departamento | ciudad | direccion
total_bruto | descuentos | subtotal | impuestos | retenciones | total_neto
observacion | estado | fecha_de_entrega | fecha_de_creacion | fecha_de_anulacion
```

---

### zeffi_ordenes_compra_detalle — ~230 filas
```
_pk | sucursal | centro_de_costos | bodega | id_orden | proveedor
cantidad | cod_articulo | descripcion_articulo | referencia | lote | serie
precio_unitario | observacion | vigencia_orden | fecha_de_creacion | fecha_de_anulacion
```

---

### zeffi_cuentas_por_cobrar — ~68 filas
```
_pk | tipo_de_cxc | id_cxc | id_resolucion_cxc | tercero | id_tercero
telefono_tercero | direccion_tercero | email_tercero | estado_cxc
valor_inicial | saldo_total | dias_mora | saldo_en_mora | primer_vencimiento | vencimientos
ultimo_seguimiento | vendedor | observacion | fecha_creacion | fecha_inicio_credito
centro_de_costos
```

---

### zeffi_cuentas_por_pagar — ~207 filas
```
_pk | tipo_de_cxp | id_cxp | tercero | id_tercero | estado_cxp
valor_inicial | saldo_total | dias_mora | saldo_en_mora | vencimientos
observacion | fecha_creacion | fecha_inicio_credito
```

---

### zeffi_comprobantes_ingreso_encabezados — ~1093 filas
```
_pk | sucursal | centro_de_costos | id_interno | id_numeracion
nombre_tercero | id_tercero | tipo_tercero | telefono | direccion
divisa | trm | subtotal | retencion | descuento | total
fecha_del_ingreso | concepto | estado_contable | respuesta_contable | observacion | estado
fecha_de_creacion | responsable_de_creacion | fecha_de_anulacion | responsable_de_anulacion
```

---

### zeffi_comprobantes_ingreso_detalle — ~1886 filas
```
_pk | sucursal_ingreso | centro_de_costos | id_ingreso
nombre_tercero | id_tercero | tipo_tercero | concepto | descripcion_concepto
tipo_referencia | sucursal_referencia | id_referencia | res_referencia
divisa | trm | subtotal | retencion | descuento | total_concepto | total_ingreso
medios_de_pago_ingreso | fecha_del_ingreso | observacion_ingreso | estado_ingreso
fecha_de_creacion | responsable_de_creacion | fecha_de_anulacion | responsable_de_anulacion
```

---

### zeffi_produccion_encabezados — ~1919 filas
```
_pk | sucursal | id_orden | bodega | nombre_encargado | id_encargado | tipo_encargado
nombre_tercero | id_tercero | tipo_tercero | activo_productivo
fecha_inicial | fecha_final | total_precios_de_venta
costo_de_materiales | otros_costos_de_produccion | beneficio_neto
observacion | estado | vigencia | fecha_de_creacion | responsable_de_creacion
fecha_de_anulacion | responsable_de_anulacion
```

---

### zeffi_materiales — ~8026 filas
```
_pk | sucursal | bodega | id_orden | nombre_encargado | id_encargado | tipo_encargado
nombre_tercero | id_tercero | tipo_tercero | activo_productivo
cod_material | descripcion_material | categoria | referencia | lote | serie
cantidad | costo_ud | observacion_de_orden | vigencia | responsable | fecha_creacion
```

---

### zeffi_articulos_producidos — ~3375 filas
```
_pk | sucursal | bodega | id_orden | nombre_encargado | id_encargado | tipo_encargado
nombre_tercero | id_tercero | tipo_tercero | activo_productivo
cod_articulo | descripcion_articulo_producido | categoria | referencia | lote | serie
cantidad | precio_minimo_ud | observacion_orden | vigencia | responsable | fecha_creacion
```

---

### zeffi_otros_costos — ~1065 filas
```
_pk | sucursal | bodega | id_orden | nombre_encargado | id_encargado | tipo_encargado
nombre_tercero | id_tercero | tipo_tercero | activo_productivo
costo_de_produccion | cantidad | costo_ud | observacion_orden | vigencia
responsable | fecha_inicio | fecha_fin | fecha_creacion
```

---

### zeffi_costos_produccion — ~15 filas
Catálogo de tipos de costos de producción.
```
_pk | id | nombre | vigencia
fecha_de_creacion | responsable_de_creacion | fecha_de_modificacion
responsable_de_modificacion | fecha_de_anulacion | responsable_de_anulacion
```

---

### zeffi_cambios_estado — ~1113 filas
Historial de cambios de estado de órdenes de producción.
```
_pk | sucursal | id_orden | nuevo_estado | observacion_estado | f_cambio_de_estado
responsable_cambio_de_estado | bodega | nombre_encargado | id_encargado | tipo_encargado
nombre_tercero | id_tercero | tipo_tercero | activo_productivo
fecha_inicial | fecha_final | total_precios_de_venta
costo_de_materiales | otros_costos_de_produccion | beneficio_neto
observacion | vigencia | fecha_de_creacion | responsable_de_creacion
fecha_de_anulacion | responsable_de_anulacion
```

---

### zeffi_guias_transporte — ~488 filas
```
_pk | id | cod_barras | nombre | referencia | sucursal_principal | tipo_de_articulo
categoria | marca | descripcion | vigencia | fecha_de_creacion | fecha_de_modificacion
costo_manual | costo_promedio | ultimo_costo | precio_minimo_de_venta | impuestos
[precios por tarifa...] | gestion_de_stock | stock_minimo | stock_optimo | stock_total_empresa
[stock por bodega...]
```

---

### zeffi_tipos_egresos — ~125 filas
```
_pk | id | tipo_de_egreso | vigencia
fecha_de_creacion | responsable_de_creacion | fecha_de_modificacion
responsable_de_modificacion | fecha_de_anulacion | responsable_de_anulacion
```

---

### zeffi_tipos_marketing — ~50 filas
```
_pk | id | tipo_de_marketing | vigencia
fecha_de_creacion | responsable_de_creacion | fecha_de_modificacion
responsable_de_modificacion | fecha_de_anulacion | responsable_de_anulacion
```

---

## Vistas SQL (sin prefijo)

### vbase_ventas_mes
Base de datos para cálculo de ventas por mes.

### vista_ventas_por_mes
Ventas agrupadas por mes — JOIN entre facturas_venta y clientes.

---

## Resumen de volumen

| Tabla | Filas aprox. |
|---|---|
| zeffi_trazabilidad | 63.449 |
| zeffi_remisiones_venta_detalle | 8.313 |
| zeffi_materiales | 8.026 |
| zeffi_ordenes_venta_detalle | 6.986 |
| zeffi_cotizaciones_ventas_detalle | 6.565 |
| zeffi_facturas_venta_detalle | 4.940 |
| zeffi_remisiones_venta_encabezados | 2.176 |
| zeffi_comprobantes_ingreso_detalle | 1.886 |
| zeffi_produccion_encabezados | 1.919 |
| zeffi_articulos_producidos | 3.375 |
| zeffi_otros_costos | 1.065 |
| zeffi_cambios_estado | 1.113 |
| zeffi_comprobantes_ingreso_encabezados | 1.093 |
| zeffi_cotizaciones_ventas_encabezados | 1.006 |
| zeffi_facturas_venta_encabezados | 824 |
| zeffi_ordenes_venta_encabezados | 694 |
| zeffi_remisiones_compra_detalle | 569 |
| zeffi_traslados_inventario | 517 |
| zeffi_inventario | 488 |
| zeffi_guias_transporte | 488 |
| zeffi_ajustes_inventario | 356 |
| zeffi_proveedores | 304 |
| zeffi_facturas_compra_detalle | 262 |
| zeffi_ordenes_compra_detalle | 230 |
| zeffi_remisiones_compra_encabezados | 220 |
| zeffi_cuentas_por_pagar | 207 |
| zeffi_notas_credito_venta_detalle | 275 |
| zeffi_clientes | 462 |
| zeffi_notas_credito_venta_encabezados | 89 |
| zeffi_facturas_compra_encabezados | 110 |
| zeffi_ordenes_compra_encabezados | 85 |
| zeffi_devoluciones_venta_detalle | 53 |
| zeffi_categorias_articulos | 54 |
| zeffi_tipos_marketing | 50 |
| zeffi_devoluciones_venta_encabezados | 27 |
| zeffi_cuentas_por_cobrar | 68 |
| zeffi_bodegas | 15 |
| zeffi_costos_produccion | 15 |
