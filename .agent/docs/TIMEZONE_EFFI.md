# Zona Horaria en Tablas Effi — Referencia Definitiva

**Verificado**: 2026-04-20 (auditoría completa, cruce tabla por tabla)
**Conclusión**: TODAS las tablas en effi_data están en **hora Colombia (UTC-5)**

---

## Cómo se garantiza

1. Effi exporta los Excel con timestamps en hora Colombia
2. `import_all.js` inserta como TEXT sin modificación
3. **Excepción**: `zeffi_cambios_estado.f_cambio_de_estado` llega en UTC desde Effi → `import_all.js` la convierte a COT restando 5 horas al importar
4. Resultado: toda la BD queda uniformemente en UTC-5

## Auditoría — verificación cruzada por documento

Método: comparar el timestamp de un mismo documento en su tabla de encabezado vs `zeffi_trazabilidad` (referencia base COT).

| Tabla | Doc verificado | Hora en tabla | Hora en trazabilidad | Resultado |
|---|---|---|---|---|
| **zeffi_trazabilidad** | — | — | — | **COT** (referencia) |
| **zeffi_remisiones_venta_encabezados** | Rem 2333 | 14:11:18 | 14:11:18 | **COT** ✅ |
| **zeffi_produccion_encabezados** | OP 2176 | 13:56:14 | 13:56:14 | **COT** ✅ |
| **zeffi_cambios_estado** | OP 2176 | 13:56:27 | (creación 13:56:14) | **COT** ✅ (13s después, no 5h) |
| **zeffi_ajustes_inventario** | Ajuste 363 | 18:25:42 | 18:25:42 | **COT** ✅ |
| **zeffi_remisiones_compra_encabezados** | Rem compra 476 | 13:04:55 | 13:04:55 | **COT** ✅ |
| **zeffi_materiales** | OP 2176 | 13:56:14 | 13:56:14 | **COT** ✅ |
| **zeffi_articulos_producidos** | OP 2176 | 13:56:14 | 13:56:14 | **COT** ✅ |
| **zeffi_cuentas_por_cobrar** | CXC 89 | 14:11:18 | (rem 2333: 14:11:18) | **COT** ✅ |
| **zeffi_facturas_venta_encabezados** | — | (sin datos del 20 abr) | — | **COT** (consistente) |
| **zeffi_ordenes_venta_encabezados** | — | (sin datos del 20 abr) | — | **COT** (consistente) |
| Todas las demás (20+ tablas) | — | Formato datetime correcto, horario laboral | — | **COT** (consistente) |

## Tablas con formato serial de Excel

3 tablas tienen fechas en formato serial numérico (ej: `46132.591180556`) en vez de datetime string. Los datos son COT correctos pero no legibles directamente:

| Tabla | Columnas afectadas |
|---|---|
| zeffi_inventario | fecha_de_creacion, fecha_de_modificacion |
| zeffi_guias_transporte | fecha_de_creacion, fecha_de_modificacion |
| zeffi_remisiones_venta_detalle | fecha_creacion, fecha_entrega, fecha_anulacion |

No afectan inventario (no usamos esas columnas). Si se necesitan, convertir en el importador.

## Regla para queries

**NO hacer conversiones de timezone.** Todas las fechas ya están en hora Colombia.

```sql
-- CORRECTO: comparar directo
WHERE fecha <= '2026-04-20 14:30:00'

-- INCORRECTO: nunca sumar ni restar horas
WHERE fecha <= DATE_ADD('2026-04-20 14:30:00', INTERVAL 5 HOUR)
```
