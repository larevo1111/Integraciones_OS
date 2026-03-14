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
**Usar para**: producción del período, órdenes en proceso, costo de producción.

### zeffi_articulos_producidos
Artículos terminados que resultaron de una orden de producción.
**Usar para**: qué se fabricó, cantidades producidas por referencia.

### zeffi_costos_produccion
Costos asociados a cada orden de producción (mano de obra, insumos indirectos, etc.).
**Usar para**: costo real de fabricación, análisis de costos de producción.

### zeffi_materiales
Materias primas/materiales consumidos en cada orden de producción.
**Usar para**: consumo de materiales, relación materia prima → producto terminado.

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
Guías de transporte generadas para despachos.
**Usar para**: seguimiento de envíos, guías por período o cliente.

### zeffi_trazabilidad
Trazabilidad de movimientos de inventario — registro del ciclo de vida de los productos.
**Usar para**: historial de movimientos de un artículo específico.

### zeffi_cambios_estado
Historial de cambios de estado en documentos (facturas, remisiones, órdenes).
**Usar para**: auditoría, saber cuándo pasó un documento de un estado a otro.

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
| Datos de un cliente | `zeffi_clientes` |
| Datos de un vendedor | `zeffi_empleados` |
