---
name: effi-negocio
description: >
  Modelo de negocio Effi y lógica comercial de Origen Silvestre. Triggers: negocio, vigencia, consignación, canal, tarifa, producción, devolución, cartera, cliente.
---

# Skill: Modelo de Negocio Effi — Origen Silvestre

Guía del modelo de datos de Effi en el contexto del negocio de Origen Silvestre.
Documenta cómo se relacionan los módulos, qué significa cada estado, y la lógica de negocio detrás de los datos.

---

## 1. Qué es "vigente" en Effi

> **CRÍTICO para no cometer errores de análisis.**

**`vigencia = 'Vigente'` NO significa "abierto" o "pendiente de pago".**
Significa **"no anulado"** (no cancelado/eliminado).

Una factura cobrada al 100% sigue siendo `vigencia = 'Vigente'` porque no fue anulada.
Una factura anulada es `vigencia = 'Anulada'`.

**Consecuencia:** `?vigente=1` en los exports de Effi trae todos los documentos no anulados,
incluyendo los ya pagados/cerrados. No es un filtro de "activos" en sentido financiero.

**¿Cómo saber si una factura está pagada?**
→ `pdte_de_cobro = '0'` o `'0.00'` (es campo TEXT, castear a DECIMAL para comparar)
→ `estado_cxc = 'Cobrada'` o similar

---

## 2. Campos financieros en documentos de venta

Presente en `facturas_venta_encabezados`, `remisiones_venta_encabezados`, `ordenes_venta_encabezados`:

| Campo | Significado |
|---|---|
| `total_bruto` | Suma de precios antes de descuentos |
| `descuentos` | Total de descuentos aplicados |
| `subtotal` | total_bruto - descuentos (SIN IVA — valor comercial neto de la venta) |
| `impuestos` | IVA — se recauda y pasa íntegro a la DIAN, nunca es plata de la empresa |
| `retenciones` | Retenciones en la fuente — anticipo del impuesto de renta del vendedor, pagado por el comprador directamente a la DIAN. Es un **activo** para la empresa (reduce CxC, no reduce ingresos en el P&L). En OS son ocasionales (solo 2 meses en todo el histórico). |
| `total_neto` | subtotal + impuestos - retenciones (**incluye IVA**) |
| `pdte_de_cobro` | Saldo pendiente de cobro (0 = cobrado completamente) |
| `devoluciones_vigentes` | Snapshot dinámico de NCs vigentes asociadas a ese documento — **NO usar para análisis mensuales de calendario** |
| `costo_manual` | Costo de los productos vendidos (costo del inventario) |
| `utilidad_costo_manual` | total_neto - costo_manual |
| `margen_de_utilidad_costo_manual` | utilidad / total_neto × 100 |

> **Nota:** todos estos campos vienen como TEXT en MariaDB. Siempre castear:
> `CAST(REPLACE(total_neto, ',', '.') AS DECIMAL(15,2))`

### Métrica clave — ingresos netos (lo que realmente se queda en la empresa)

```
subtotal (= total_bruto - descuentos, sin IVA)
  - NCs del mes (subtotal de notas_credito_venta, sin IVA)
= ingresos_netos
```

IVA → nunca se queda (pasa a DIAN). Retenciones → son activo fiscal, no se restan de ingresos.
En `resumen_ventas_facturas_mes`: campo `fin_ingresos_netos`.

### Notas crédito vs devoluciones de venta — distinción CRÍTICA

| Documento | Tabla | Afecta |
|---|---|---|
| Nota crédito | `zeffi_notas_credito_venta_encabezados` | **Facturas** |
| Devolución de venta | `zeffi_devoluciones_venta_encabezados` | **Remisiones** |

**Para análisis de ventas facturadas → usar NCs, nunca `devoluciones_venta`.**
En NCs: usar campo `subtotal` (sin IVA), agrupado por `fecha_de_creacion` de la NC.
El campo `devoluciones_vigentes` en encabezados de facturas es un snapshot dinámico agrupado por fecha de factura (no por fecha de NC) — no sirve para resumen mensual calendario.

---

## 3. Sistema de consignación

Origen Silvestre usa **órdenes de venta (OV)** para gestionar mercancía en consignación.
Es el mecanismo más importante y enredado del sistema.

### Flujo completo

```
1. Se entrega mercancía al cliente consignatario
   → Se crea una OV por las unidades entregadas
   → Effi descarga el inventario con la OV

2. El cliente vende parte de la mercancía
   → Esas unidades se convierten en remisión de venta
   → Luego en factura de venta (cuando se cobra)

3. Se liquida la consignación (periódicamente)
   → Se anulan las OVs de unidades NO vendidas
     (observacion_de_anulacion: "LIQUIDACION" o "convertida a remisión")
   → Se crea nueva OV con lo que queda en consignación (si aplica)
```

### Tablas involucradas

| Tabla | Rol en consignación |
|---|---|
| `zeffi_ordenes_venta_encabezados` | Registro de mercancía entregada en consignación |
| `zeffi_ordenes_venta_detalle` | Detalle de artículos consignados |
| `zeffi_remisiones_venta_encabezados` | Liquidación parcial — lo que se vendió |
| `zeffi_facturas_venta_encabezados` | Cobro de lo que se vendió |

### Estados de OV

| `vigencia` | `ultimo_estado` | Significado |
|---|---|---|
| `Vigente` | `Generada` | Mercancía actualmente en consignación |
| `Anulada` | `Generada` | OV liquidada o anulada por error |

### Cómo distinguir anulación por liquidación vs error operativo

**Heurística (no 100% exacta):**

```python
def clasificar_ov_anulada(obs, fecha_creacion, fecha_anulacion):
    # Keywords que confirman liquidación (override de heurística de días)
    keywords_liquidacion = [
        'liquidacion', 'liquidación', 'remision', 'remisión',
        'convertida', 'retiro', 'devolucion', 'devolución',
        'no vendio', 'no vendió', 'no se entrego', 'no se entregó'
    ]
    obs_lower = (obs or '').lower()
    dias = (fecha_anulacion - fecha_creacion).days

    if any(k in obs_lower for k in keywords_liquidacion):
        return 'liquidacion'
    elif dias <= 1:
        return 'error_probable'
    else:
        return 'liquidacion'
```

**Distribución histórica en los datos:**
- 151 error_probable (≤1 día sin keywords) → ~$81M
- 533 liquidación_probable (>1 día o con keywords) → ~$143.5M

**Heurística verificada manualmente** (2026-01): OV pk672 con `observacion_de_anulacion='mal'`, anulada el mismo día de creación → excluida correctamente como error operativo (~$210k fuera del cálculo). ✅

### Campos para el resumen mensual

| Campo | Cálculo |
|---|---|
| `consignacion_pp` | SUM `total_neto` de OVs creadas ese mes, excluyendo `error_probable` |
| `consignacion_30pct` | `consignacion_pp × 0.70` (precio con 30% de descuento) |
| `consignacion_efectiva` | SUM de remisiones/facturas generadas a clientes consignatarios ese mes |

---

## 4. Canales de venta (marketing_cliente)

Campo `marketing_cliente` en `zeffi_facturas_venta_detalle` y `zeffi_remisiones_venta_detalle`.

| Código | Canal |
|---|---|
| `1.x` | Tiendas (artesanales, medicinales, fitness, restaurantes, etc.) |
| `2.x` | Distribuidores (nacional, internacional) |
| `3.x` | Marketplaces (Mercado Libre, otros) |
| `4.x` | Redes sociales (WhatsApp, Facebook) |
| `6.x` | Redes de amigos |
| `7.x` | Familiares y amigos |
| `10.x` | Referidos / Voz a voz |
| `11.x` | Miembros OS |
| `12.x` | Sin clasificar |

---

## 5. Flujo completo de una venta normal

```
Cotización (opcional)
    ↓
Orden de Venta (reserva inventario)
    ↓
Remisión de Venta (entrega física, descarga inventario)
    ↓
Factura de Venta (documento fiscal, genera CxC)
    ↓
Comprobante de Ingreso (pago recibido, cierra CxC)
```

**Notas:**
- No toda venta pasa por todos los pasos. Puede ir directo de OV a factura.
- `estado_facturacion` en OV: `Pendiente` = no facturada aún, `Remisionada` = ya tiene remisión

---

## 6. Fechas — cuál usar para cada análisis

| Análisis | Fecha a usar | Tabla | Campo |
|---|---|---|---|
| Ventas del mes | Fecha de creación de la factura | `facturas_venta_encabezados` | `fecha_de_creacion` |
| Entregas del mes | Fecha de creación de remisión | `remisiones_venta_encabezados` | `fecha_de_creacion` |
| Consignación creada | Fecha de creación OV | `ordenes_venta_encabezados` | `fecha_de_creacion` |
| Liquidación de consignación | Fecha de anulación OV | `ordenes_venta_encabezados` | `fecha_de_anulacion` |

> Para agrupar por mes: `DATE_FORMAT(fecha_de_creacion, '%Y-%m')`

---

## 7. Tarifas de precio

Origen Silvestre maneja múltiples listas de precio. En detalle de facturas/cotizaciones aparecen como columnas separadas:

| Tarifa | Campo (prefijo `precio_`) |
|---|---|
| Precio público sugerido (PP) | `precio_precio_publico_sugerido` |
| Familiares y red de amigos | `precio_precio_familiares_y_red_de_amigos` |
| Miembros (compras +200k) | `precio_de_200_000_en_compras_y_miembros` |
| Miembros (compras +400k) | `precio_de_400_000_en_compras` |
| Miembros (compras +800k) | `precio_de_800_000_en_compras` |
| Miembros (compras +1.6M) | `precio_de_1_600_000_en_compras` |

Estas columnas de tarifas existen en `facturas_venta_detalle`, `cotizaciones_ventas_detalle` y similares.
**No están en `ordenes_venta_detalle`** — ahí solo hay `precio_unitario`.

---

## 8. Dropshipping

Origen Silvestre también opera con distribuidores en modelo dropshipping.
Identificable en facturas por campos: `distribuidor_dropshipping`, `convenio_dropshipping`, `estado_transaccion_de_dropshipping`.
Estos registros representan ventas donde un distribuidor intermedia pero OS factura directamente.

---

## 9. Producción interna

OS produce sus propios productos. Flujo:

```
Orden de Producción (produccion_encabezados)
    ↓ consume materiales (materiales)
    ↓ genera artículos (articulos_producidos)
    ↓ incurre en costos (otros_costos)
    ↓ pasa por estados (cambios_estado)
```

El costo de producción (`costo_manual` en ventas) refleja el costo de fabricación propio.

---

## 10. Tabla analítica — resumen_ventas_facturas_mes

Tabla calculada por el pipeline (paso 3) a partir de `zeffi_facturas_venta_encabezados`, `zeffi_facturas_venta_detalle` y `zeffi_ordenes_venta_encabezados`.

PK: `mes` VARCHAR(7) `'YYYY-MM'`. Datos desde 2025-01.

| Prefijo | Campos | Fuente |
|---|---|---|
| `fin_` | ventas_brutas, descuentos, pct_descuento, **ventas_netas_sin_iva**, impuestos, ventas_netas, devoluciones, **ingresos_netos** | encabezados + NCs |
| `cto_` | costo_total, utilidad_bruta, margen_utilidad_pct | encabezados (`costo_manual`) |
| `vol_` | unidades_vendidas, num_facturas, ticket_promedio | detalle+encabezados |
| `cli_` | clientes_activos, clientes_nuevos, vtas_por_cliente | encabezados |
| `car_` | saldo (pendiente de cobro acumulado de facturas del mes) | encabezados (`pdte_de_cobro`) |
| `cat_` | num_referencias, vtas_por_referencia, num_canales | detalle (`cod_articulo`, `marketing_cliente`) |
| `con_` | consignacion_pp (OVs creadas, excl. errores operativos) | OVs |
| `top_` | canal (nombre), canal_ventas, cliente (nombre), cliente_ventas, producto_cod, producto_nombre, producto_ventas | detalle+encabezados |
| `pry_` | dia_del_mes, proyeccion_mes (lineal), ritmo_pct — **solo mes en curso**, NULL para meses cerrados | calculado |
| `ant_` | ventas_netas, var_ventas_pct, consignacion_pp, var_consignacion_pct | self-join -12 meses |

> **Campos porcentaje** (`fin_pct_descuento`, `cto_margen_utilidad_pct`, `ant_var_ventas_pct`, `ant_var_consignacion_pct`, `pry_ritmo_pct`): almacenados como **decimales (0–1)**, NO como porcentaje. Ej: 0.5079 = 50.79%. Multiplicar × 100 en la capa de presentación si se quiere mostrar como %.

**Script**: `scripts/calcular_resumen_ventas.py` — idempotente, UPSERT por mes.
