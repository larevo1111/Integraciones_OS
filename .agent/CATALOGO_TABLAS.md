# Catálogo de Tablas — Origen Silvestre

Descripción de negocio de cada tabla disponible para el análisis de IA.
**Fuente de datos**: Hostinger `u768061575_os_integracion` (sincronizado diariamente desde Effi).

---

## VENTAS

### zeffi_facturas_venta_encabezados
Cada fila es una factura de venta emitida. Tiene los totales completos: valor bruto, descuentos, IVA, total neto que pagó el cliente, estado de cobro, márgenes y utilidad.
**Usar para**: ventas del día/semana/mes, ingresos totales, comparar períodos, ventas por canal, ventas por cliente, cartera pendiente de cobro, márgenes globales.

### zeffi_facturas_venta_detalle
Cada fila es un artículo dentro de una factura. Contiene cantidad, precio unitario, descuento, costo y utilidad por producto en cada venta.
**Usar para**: top productos más vendidos, análisis por referencia/categoría/marca, unidades vendidas, margen por producto, ventas de un artículo específico.

### zeffi_remisiones_venta_encabezados
Cada fila es una remisión (entrega de mercancía que aún no se ha facturado). Incluye totales, estado (pendiente de facturar o anulada) y datos del cliente/vendedor.
**Usar para**: mercancía entregada pendiente de cobro, comparar volumen facturado vs remisionado, cartera de remisiones, análisis por canal o vendedor.

### zeffi_remisiones_venta_detalle
Cada fila es un artículo dentro de una remisión. Misma estructura que detalle de facturas.
**Usar para**: qué productos se están remisionando, cantidades entregadas por referencia, análisis de remisiones por producto.

### zeffi_ordenes_venta_encabezados
Cada fila es una Orden de Venta (OV) — usada principalmente para consignación (mercancía en calle en poder del cliente).
**Usar para**: consignación activa (filtrar `vigencia = 'Vigente'`), valor total en consignación, órdenes por cliente o vendedor.
**Regla crítica**: `vigencia='Vigente'` = consignación activa. `vigencia='Anulada'` = ya procesada (convertida a remisión, facturada o cancelada).

### zeffi_ordenes_venta_detalle
Artículos dentro de cada orden de venta/consignación.
**Usar para**: detalle de qué productos están en consignación activa.

### zeffi_notas_credito_venta_encabezados
Cada fila es una nota crédito (devolución de dinero o crédito a favor del cliente sobre una factura). Indica qué factura origina la devolución y el valor devuelto.
**Usar para**: devoluciones en valor ($), impacto en ingresos netos, notas crédito por período o cliente.

### zeffi_notas_credito_venta_detalle
Artículos devueltos dentro de cada nota crédito.
**Usar para**: qué productos se devuelven más, devoluciones por referencia.

### zeffi_devoluciones_venta_encabezados
Devoluciones físicas de mercancía (la mercancía vuelve al inventario). Complementa las notas crédito.
**Usar para**: devoluciones físicas por período, clientes que más devuelven, productos más devueltos.

### zeffi_devoluciones_venta_detalle
Artículos incluidos en cada devolución física.

### zeffi_cotizaciones_ventas_encabezados
Cotizaciones enviadas a clientes (no son ventas aún — son propuestas de precio).
**Usar para**: pipeline de ventas, cotizaciones por período o cliente, tasa de conversión (cuántas cotizaciones terminaron en venta).

### zeffi_cotizaciones_ventas_detalle
Artículos dentro de cada cotización.

---

## CLIENTES Y PRODUCTOS

### zeffi_clientes
Maestro de todos los clientes registrados en Effi. Incluye datos de contacto, tipo de cliente, canal de marketing, tarifa asignada, forma de pago, vendedor, fecha última compra.
**Usar para**: buscar información de un cliente específico, segmentar por canal o tipo, clientes activos vs inactivos, clientes con crédito.
**Nota**: puede haber NITs duplicados — al hacer JOIN con facturas, deduplicar con GROUP BY.

### zeffi_inventario
Inventario actual de todos los artículos: stock disponible, costos (manual y promedio), precio de venta, márgenes, niveles mínimos y óptimos.
**Usar para**: stock disponible de un producto, valoración del inventario, artículos bajo stock mínimo, precios y márgenes actuales.

### catalogo_articulos
Catálogo de artículos con su clasificación en grupos de producto (Aceites, Cremas, Jabones, etc.). Enriquece los datos de ventas con la categoría de negocio.
**Usar para**: cruzar ventas con grupo de producto cuando facturas/remisiones no tienen el grupo directamente.

### zeffi_categorias_articulos
Categorías maestras de artículos tal como están definidas en Effi.
**Usar para**: listar las categorías disponibles, verificar clasificaciones.

---

## COMPRAS

### zeffi_facturas_compra_encabezados
Facturas de compra a proveedores. Cada fila es una compra registrada.
**Usar para**: compras del período, gasto en compras, compras por proveedor.

### zeffi_facturas_compra_detalle
Artículos dentro de cada factura de compra — qué se compró y en qué cantidad.
**Usar para**: artículos comprados, costo por unidad comprada, volumen de compras por referencia.

### zeffi_ordenes_compra_encabezados
Órdenes de compra emitidas a proveedores (antes de recibirlas).
**Usar para**: compras en tránsito, órdenes pendientes de recibir.

### zeffi_ordenes_compra_detalle
Artículos dentro de cada orden de compra.

### zeffi_remisiones_compra_encabezados
Recepción de mercancía de proveedores (mercancía recibida que puede o no tener factura aún).
**Usar para**: ingresos de mercancía al inventario, recepciones por período.

### zeffi_remisiones_compra_detalle
Artículos recibidos en cada remisión de compra.

### zeffi_proveedores
Maestro de proveedores registrados en Effi.
**Usar para**: datos de un proveedor, listar proveedores activos, cruzar con compras.

---

## PRODUCCIÓN

### zeffi_produccion_encabezados
Órdenes de producción — cada fila es una orden de fabricación con su estado y valores.

**Campos clave**: `id_orden` (numérico secuencial, ej: 1985), `estado` ("Generada" / "Procesada"), `vigencia` ("Vigente" / "Anulado"), `fecha_de_creacion`, `fecha_inicial`, `fecha_final`.

**Estados**:
- `Generada` + `Vigente` (85 actualmente): OP creada pero NO ejecutada físicamente. **Effi ya descontó materiales y sumó productos al inventario aunque la producción no haya ocurrido.**
- `Procesada` + `Vigente` (1,024): OP ejecutada y confirmada — efecto real.
- `Generada` + `Anulado` (890): anuladas, su efecto fue revertido en trazabilidad.
- `Procesada` + `Anulado` (95): procesadas luego anuladas.

**Importante**: Effi registra el impacto en inventario al *crear* la OP, no al procesarla. Por eso las OPs "Generada" generan una discrepancia entre el inventario Effi y la realidad física.

**Usar para**: producción del período, OPs pendientes de ejecutar, costo de producción.

### zeffi_cambios_estado
Historial de TODOS los cambios de estado de OPs con timestamp exacto. **Tabla crítica para determinar el estado de una OP en una fecha histórica.**

**Campos clave**: `id_orden`, `nuevo_estado` ("Generada" / "Procesada"), `f_cambio_de_estado` (timestamp del cambio), `vigencia`.

**Comportamiento crítico — leer antes de usar**:
- **NO registra el estado inicial**. Una OP recién creada empieza en "Generada" sin ningún registro en esta tabla. El primer registro aparece solo cuando alguien cambia el estado.
- Para saber el estado de una OP en una fecha: buscar el último registro con `f_cambio_de_estado <= fecha`. Si no hay registro → la OP estaba en estado inicial = "Generada".

```sql
-- ¿En qué estado estaba la OP X al corte del 31/03?
SELECT nuevo_estado
FROM zeffi_cambios_estado
WHERE id_orden = 'X'
  AND f_cambio_de_estado <= '2026-03-31 23:59:59'
ORDER BY f_cambio_de_estado DESC, _pk DESC
LIMIT 1;
-- Sin filas → 'Generada' (estado inicial)
```

**Usar para**: auditoría de producción, reconstruir el estado de OPs en fechas históricas, calcular inventario teórico a fecha de corte.

### zeffi_materiales
Materias primas consumidas por cada OP. Una fila por cada material en cada OP.

**Campos clave**: `id_orden`, `cod_material`, `descripcion_material`, `cantidad` (TEXT con coma decimal, ej: "10,500"), `costo_ud`, `bodega`, `vigencia`.

**Valores de vigencia** (diferente a "Vigente"/"Anulado"):
- `"Orden vigente"` → la OP está vigente (1,109 OPs, 4,509 filas)
- `"Orden anulada"` → la OP fue anulada (985 OPs, 4,211 filas)

**Para inventario teórico**: filtrar `vigencia = 'Orden vigente'` para OPs en estado "Generada". Estas materias primas fueron descontadas por Effi prematuramente — hay que sumarlas de vuelta al stock teórico.

**Usar para**: consumo de materiales por OP, relación materia prima → producto terminado, ajuste de inventario teórico.

### zeffi_articulos_producidos
Artículos terminados que resultan de una OP. Una fila por cada producto en cada OP.

**Campos clave**: `id_orden`, `cod_articulo`, `descripcion_articulo_producido`, `cantidad` (TEXT con coma decimal), `bodega`, `vigencia`.

**Valores de vigencia**: igual que `zeffi_materiales` — "Orden vigente" / "Orden anulada".

**Para inventario teórico**: filtrar `vigencia = 'Orden vigente'` para OPs en estado "Generada". Estos productos fueron sumados por Effi prematuramente — hay que restarlos del stock teórico.

**Usar para**: qué se fabricó, cantidades producidas por referencia, ajuste de inventario teórico.

### zeffi_costos_produccion
Costos asociados a cada orden de producción (mano de obra, insumos indirectos, etc.).
**Usar para**: costo real de fabricación, análisis de costos de producción.

### zeffi_otros_costos
Otros costos cargados a órdenes de producción (costos indirectos, fletes, etc.).

---

## FINANCIERO

### zeffi_cuentas_por_cobrar
Cartera de clientes — facturas y remisiones con saldo pendiente de cobro, días de mora, estado.
**Usar para**: cartera total, clientes en mora, antigüedad de cartera, facturas vencidas.

### zeffi_cuentas_por_pagar
Deudas con proveedores — facturas de compra con saldo pendiente de pago.
**Usar para**: saldo por pagar a proveedores, deudas vencidas, flujo de caja de pagos.

### zeffi_comprobantes_ingreso_encabezados
Comprobantes de recaudo / pagos recibidos de clientes.
**Usar para**: pagos recibidos del período, ingresos de caja, abonos a cartera.

### zeffi_comprobantes_ingreso_detalle
Detalle de cada comprobante de ingreso — a qué facturas se aplicó el pago.

### zeffi_tipos_egresos
Tipos de egresos/gastos definidos en Effi (catálogo de conceptos de gasto).

---

## OPERACIONES Y LOGÍSTICA

### zeffi_bodegas
Maestro de bodegas/almacenes disponibles en la empresa.
**Usar para**: listar bodegas, cruzar con inventario por bodega.

### zeffi_traslados_inventario
Movimientos de mercancía entre bodegas.
**Usar para**: traslados del período, stock transferido entre sucursales.

### zeffi_ajustes_inventario
Ajustes manuales al inventario (entradas y salidas sin documento comercial).
**Usar para**: ajustes del período, diferencias de inventario.

### zeffi_guias_transporte
Catálogo completo de artículos con stock desagregado por bodega/punto de consignación y precios por cada tarifa. A pesar del nombre, es una vista de inventario detallada (similar a zeffi_inventario pero con granularidad de bodega).
**Usar para**: stock de un artículo en una bodega específica (Villa de Aburrá, Apicá, El Salvador, etc.), precios por tarifa de cada artículo, valoración por punto de entrega/consignación.

### zeffi_trazabilidad
Historial completo de todos los movimientos de inventario: ventas, compras, producción, ajustes, traslados. La tabla más completa para trazabilidad de artículos.

**Campos clave**: `id_articulo`, `articulo`, `transaccion` (ej: "ORDEN DE PRODUCCIÓN: 1985"), `tipo_de_movimiento`, `vigencia_de_transaccion`, `cantidad` (TEXT con coma decimal), `bodega`, `fecha`.

**Dos tipos de movimiento** (solo estos dos):
- `"Creación de transacción"` → movimiento original
- `"Anulación de transacción"` → reversa de un movimiento anulado, con signo ya invertido

**Signos de cantidad**: positivo = ingreso a bodega, negativo = egreso.

**Para reconstruir stock a fecha histórica**:
```sql
stock_en_corte = stock_actual - SUM(CAST(REPLACE(cantidad,',','.') AS DECIMAL(12,2)))
                  WHERE fecha > 'fecha_corte 23:59:59'
```
Usar TODOS los registros (no filtrar por tipo ni vigencia) — las anulaciones tienen signo ya invertido y se auto-cancelan matemáticamente.

**Tipos de transacción más frecuentes**: ORDEN DE PRODUCCIÓN (6,357), FACTURA DE VENTA (5,400), TRASLADO DE INVENTARIO (4,488), REMISIÓN DE VENTA (2,017), AJUSTE DE INVENTARIO (1,107).

**Usar para**: historial de movimientos de un artículo, cuándo entró/salió stock, trazabilidad completa por período, reconstrucción de stock en fecha histórica.

---

## MAESTROS / CATÁLOGOS

### zeffi_empleados
Maestro de empleados y vendedores registrados en Effi.
**Usar para**: datos de vendedores, listar el equipo de ventas, cruzar ventas por vendedor.

### zeffi_tarifas_precios
Tarifas de precios definidas en Effi (lista pública, distribuidor, mayorista, etc.).
**Usar para**: listar tarifas disponibles, cruzar con clientes que tienen cada tarifa.

### zeffi_tipos_marketing
Canales de marketing definidos en Effi (Instagram, WhatsApp, Referido, etc.).
**Usar para**: listar canales disponibles, cruzar con clientes o ventas por canal.

---

## RESÚMENES PRECALCULADOS *(más rápido para análisis mensuales)*

### resumen_ventas_facturas_mes
KPIs mensuales completos de ventas facturadas: ventas netas, devoluciones, ingresos, costos, margen, unidades, clientes activos, ticket promedio, cartera, top cliente/producto/canal. Incluye comparativos con mes anterior y mismo mes año anterior.
**Usar para**: resumen del mes, comparar meses, tendencias anuales, proyección del mes en curso. **Siempre preferir esta tabla para consultas mensuales globales** — es mucho más rápida.

### resumen_ventas_facturas_producto_mes
Ventas facturadas desglosadas por producto y mes. Cada fila = un artículo en un mes específico.
**Usar para**: ranking de productos por mes, evolución de ventas de un producto, top referencias del período.

### resumen_ventas_facturas_cliente_mes
Ventas facturadas desglosadas por cliente y mes. Cada fila = un cliente en un mes específico.
**Usar para**: ranking de clientes por mes, historial de compras de un cliente, clientes nuevos vs recurrentes.

### resumen_ventas_facturas_canal_mes
Ventas facturadas desglosadas por canal de marketing y mes.
**Usar para**: participación de cada canal, evolución de canales, comparar Instagram vs WhatsApp vs otros.

### resumen_ventas_remisiones_mes
Igual que facturas_mes pero para remisiones de venta. Incluye métricas de remisiones pendientes de facturar.
**Usar para**: resumen mensual de remisiones, remisiones pendientes, comparar facturado vs remisionado.

### resumen_ventas_remisiones_producto_mes
Remisiones desglosadas por producto y mes.

### resumen_ventas_remisiones_cliente_mes
Remisiones desglosadas por cliente y mes.

### resumen_ventas_remisiones_canal_mes
Remisiones desglosadas por canal y mes.

---

## OTROS

### crm_contactos
Contactos del CRM EspoCRM sincronizados a Hostinger. Incluye tipo de cliente, canal de marketing, clasificación comercial, datos de contacto.
**Usar para**: información enriquecida de clientes (clasificación CRM, tipo de negocio), análisis combinado CRM + Effi.

### codigos_ciudades_dane
Catálogo de municipios de Colombia con código DANE, nombre y departamento.
**Usar para**: normalizar nombres de ciudades, cruzar con clientes por municipio.

---

## Guía rápida — qué tabla usar

| Necesito saber... | Tabla recomendada |
|---|---|
| Ventas del día/semana (globales) | `zeffi_facturas_venta_encabezados` |
| Ventas del mes (globales) | `resumen_ventas_facturas_mes` |
| Qué productos se venden más | `zeffi_facturas_venta_detalle` o `resumen_ventas_facturas_producto_mes` |
| Ventas por canal de marketing | `resumen_ventas_facturas_canal_mes` |
| Mejores clientes del mes | `resumen_ventas_facturas_cliente_mes` |
| Remisiones pendientes de facturar | `zeffi_remisiones_venta_encabezados` |
| Consignación activa | `zeffi_ordenes_venta_encabezados` (vigencia='Vigente') |
| Stock disponible de un producto | `zeffi_inventario` |
| Grupo de producto de un artículo | `catalogo_articulos` |
| Devoluciones del mes | `zeffi_notas_credito_venta_encabezados` |
| Cartera pendiente de cobro | `zeffi_cuentas_por_cobrar` |
| Compras a proveedores | `zeffi_facturas_compra_encabezados` |
| Producción del período | `zeffi_produccion_encabezados` |
| OPs pendientes de ejecutar | `zeffi_produccion_encabezados` WHERE estado='Generada' AND vigencia='Vigente' |
| Estado de una OP en fecha histórica | `zeffi_cambios_estado` (último registro antes de la fecha) |
| Materiales consumidos por una OP | `zeffi_materiales` |
| Productos generados por una OP | `zeffi_articulos_producidos` |
| Inventario teórico a fecha de corte | Ver lógica en `.agent/contextos/inventario_fisico.md §Inventario Teórico` |
| Datos de un cliente | `zeffi_clientes` |
| Datos de un vendedor | `zeffi_empleados` |
